from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from typing import Optional

from schema.models import DiscussionRecord

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.core.pipeline import get_pipeline
from src.storage.sqlite_manager import get_db_manager
from src.utils.logger import get_logger
from src.config import settings

logger = get_logger(__name__)

# レート制限（IPアドレス単位）
limiter = Limiter(key_func=get_remote_address)

# FastAPI アプリケーション
app = FastAPI(
    title="Discussion System API",
    description="食べログ営業向け商談解析API",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS設定
# 本番はフロントエンド（Next.js静的書き出し）をこのFastAPIから同一オリジンで配信するため
# 本来CORSは不要だが、`next dev`（localhost:3000）からこのAPI（localhost:8000）を
# 直接叩くローカル開発時のために残してある。環境変数 CORS_ORIGINS で上書き可能。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _record_to_dict(record: DiscussionRecord) -> dict:
    """DiscussionRecord をAPIレスポンス用の辞書に変換する（テキスト・音声共通）"""
    return {
        "success": True,
        "meeting_id": record.meeting_id,
        "company_name": record.company_info.name,
        "corporate_name": record.company_info.corporate_name,
        "contact_name": record.company_info.contact_name,
        "confidence_score": record.confidence_score,
        "summary": record.summary,
        "priority_issues": [
            {
                "category": issue.category,
                "issue": issue.issue,
                "priority": issue.priority,
            }
            for issue in record.priority_issues
        ],
        "dx_solutions": record.dx_solutions.model_dump(),
        "created_at": record.created_at.isoformat(),
    }


# ============================================================================
# PROCESS ENDPOINT - 文字起こし済みテキストの解析
# ============================================================================
@app.post("/api/process")
@limiter.limit("20/minute")
async def process_transcript(
    request: Request,
    transcript: str = Form(...),
    company_name: str = Form(...),
    corporate_name: Optional[str] = Form(None),
    contact_name: Optional[str] = Form(None),
    meeting_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
) -> dict:
    """
    文字起こし済みの商談テキストを解析し、法人/店舗別に蓄積する。

    音声認識（Whisper）は行わない前提。既に文字起こし済みのテキストを
    Claude API で構造化するだけなので、通常は数秒で完了する。

    Args:
        transcript: 商談の文字起こしテキスト
        company_name: 店舗名
        corporate_name: 法人名（任意。単一店舗経営の場合は不要）
        contact_name: 接触者氏名
        meeting_date: 商談日時
        notes: 補足メモ

    Returns:
        解析結果（優先課題・DX提案・要約など）
    """
    if not transcript or len(transcript.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="文字起こしテキストが短すぎます（10文字以上必要です）",
        )

    logger.info(f"Analyzing transcript for {company_name} ({len(transcript)} chars)")

    try:
        pipeline = get_pipeline()
        record, _ = pipeline.process_and_save(
            transcript_text=transcript,
            company_name=company_name,
            corporate_name=corporate_name,
            contact_name=contact_name,
            meeting_date=meeting_date,
            notes=notes,
        )

        db = get_db_manager()
        try:
            record_id = db.save_record(record)
            logger.info(f"Record saved to DB: {record_id}")
        except Exception as e:
            logger.warning(f"Failed to save to DB: {e}")

        return _record_to_dict(record)

    except Exception as e:
        logger.error(f"Transcript analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROCESS-AUDIO ENDPOINT - 録音ファイルの処理（非同期ジョブ方式）
# ============================================================================
# 音声処理の最大待ち時間。Whisperのffmpeg経由の音声デコードがまれに
# ハングしたまま返ってこないケースがあり、その場合ジョブが永久に
# 'pending' のままになってしまう。タイムアウトさせて必ず failed に落とす。
AUDIO_PROCESSING_TIMEOUT_SECONDS = 600


def _run_audio_processing_job(
    job_id: str,
    tmp_path: Path,
    company_name: str,
    corporate_name: Optional[str],
    contact_name: Optional[str],
    meeting_date: Optional[str],
    notes: Optional[str],
) -> None:
    """
    バックグラウンドスレッドで実行される音声処理本体。
    Whisper文字起こし + Claude解析は同期・ブロッキングだが、Starlette の
    BackgroundTasks は同期関数をスレッドプールで実行するため、
    イベントループ（＝他のリクエスト、特にステータス確認のポーリング）を
    ブロックしない。

    実処理はさらに別スレッドで実行し、AUDIO_PROCESSING_TIMEOUT_SECONDS を
    超えたらタイムアウト扱いにする（ffmpeg/Whisperがハングして戻ってこない
    場合に、ジョブが永久に pending のまま残るのを防ぐため）。
    """
    db = get_db_manager()

    def _process() -> DiscussionRecord:
        pipeline = get_pipeline()
        record, _ = pipeline.process_and_save(
            audio_file=tmp_path,
            company_name=company_name,
            corporate_name=corporate_name,
            contact_name=contact_name,
            meeting_date=meeting_date,
            notes=notes,
        )
        return record

    # 通常の with 文（shutdown(wait=True)）だとタイムアウト後も、ハングした
    # ワーカースレッドの終了を待ってブロックしてしまい意味がなくなるため、
    # shutdown(wait=False) で切り離す。ハングしたスレッド自体はプロセスの
    # 生存中はリークするが、ジョブのステータス更新をブロックしないことを優先する。
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(_process)
        try:
            record = future.result(timeout=AUDIO_PROCESSING_TIMEOUT_SECONDS)
        except FutureTimeoutError:
            executor.shutdown(wait=False)
            raise TimeoutError(
                f"音声処理が{AUDIO_PROCESSING_TIMEOUT_SECONDS}秒以内に完了しませんでした。"
                "ファイルが長すぎるか、音声デコードでの問題が発生している可能性があります。"
            )
        else:
            executor.shutdown(wait=False)

        try:
            record_id = db.save_record(record)
            logger.info(f"Record saved to DB: {record_id}")
        except Exception as e:
            logger.warning(f"Failed to save to DB: {e}")

        db.update_job(job_id, status="completed", result=_record_to_dict(record))
        logger.info(f"Job {job_id} completed")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        db.update_job(job_id, status="failed", error_message=str(e))

    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/api/process-audio")
@limiter.limit("5/minute")
async def process_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_name: str = Form(...),
    corporate_name: Optional[str] = Form(None),
    contact_name: Optional[str] = Form(None),
    meeting_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
) -> dict:
    """
    録音ファイルの処理を受け付け、バックグラウンドジョブとして開始する。

    Whisper文字起こし + Claude解析には数十秒〜数分かかるため、リクエストを
    ブロックせず即座に job_id を返す。進捗は GET /api/process-audio/status/{job_id}
    でポーリングして確認する。

    Args:
        file: 音声ファイル (MP3/WAV/M4A/FLAC/OGG)
        company_name: 店舗名
        corporate_name: 法人名（任意。単一店舗経営の場合は不要）
        contact_name: 接触者氏名
        meeting_date: 商談日時
        notes: 補足メモ

    Returns:
        {job_id, status: "pending"}
    """
    supported_formats = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in supported_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_ext}",
        )

    if file.size and file.size > 100 * 1024 * 1024:  # 100MB制限
        raise HTTPException(
            status_code=413,
            detail="File size exceeds 100MB limit",
        )

    logger.info(f"Accepting audio for processing: {file.filename} for {company_name}")

    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)

    job_id = str(uuid.uuid4())
    db = get_db_manager()
    db.create_job(job_id, company_name=company_name, corporate_name=corporate_name)

    background_tasks.add_task(
        _run_audio_processing_job,
        job_id,
        tmp_path,
        company_name,
        corporate_name,
        contact_name,
        meeting_date,
        notes,
    )

    return {"success": True, "job_id": job_id, "status": "pending"}


@app.get("/api/process-audio/status/{job_id}")
@limiter.limit("120/minute")
async def get_process_audio_status(request: Request, job_id: str) -> dict:
    """
    音声処理ジョブの状態をポーリングで確認する。

    Returns:
        status: pending | completed | failed
        result: 完了時のみ、処理結果（/api/process と同じ形）
        error: 失敗時のみ、エラーメッセージ
    """
    db = get_db_manager()
    job = db.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return {
        "success": True,
        "job_id": job_id,
        "status": job["status"],
        "result": job["result"],
        "error": job["error_message"],
    }


# ============================================================================
# LIST MEETINGS ENDPOINT - 商談一覧
# ============================================================================
@app.get("/api/list-meetings")
@limiter.limit("30/minute")
async def list_meetings(
    request: Request,
    company_name: Optional[str] = None,
    corporate_name: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    商談記録を一覧取得

    Args:
        company_name: フィルター対象店舗（指定時はその店舗の商談一覧）
        corporate_name: フィルター対象法人（指定時はその法人傘下の店舗一覧）
        limit: 取得件数

    Returns:
        法人一覧 / 店舗一覧 / 商談情報のリスト
    """
    try:
        logger.info(
            f"Listing meetings: company={company_name}, corporate={corporate_name}, limit={limit}"
        )
        db = get_db_manager()

        if company_name:
            # 特定店舗の商談一覧
            meetings = db.get_meetings_by_company(company_name, limit=limit)
            return {
                "success": True,
                "company_name": company_name,
                "meetings": meetings,
                "count": len(meetings),
            }
        elif corporate_name:
            # 法人傘下の店舗一覧
            card = db.get_corporate_card(corporate_name)
            if card is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No corporation found: {corporate_name}",
                )
            return {
                "success": True,
                "corporate_name": corporate_name,
                "stores": card["stores"],
                "count": len(card["stores"]),
            }
        else:
            # 全法人一覧 + 全店舗一覧
            corporations = db.get_all_corporations(limit=limit)
            companies = db.get_all_companies(limit=limit)
            return {
                "success": True,
                "corporations": corporations,
                "companies": companies,
                "count": len(companies),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing meetings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SEARCH ENDPOINT - 課題検索
# ============================================================================
@app.get("/api/search")
@limiter.limit("30/minute")
async def search_issues(
    request: Request,
    query: str,
    limit: int = 20,
) -> dict:
    """
    優先課題をキーワード検索

    Args:
        query: 検索キーワード
        limit: 取得件数

    Returns:
        マッチした課題リスト
    """
    try:
        if not query or len(query) < 2:
            raise HTTPException(
                status_code=400,
                detail="Query must be at least 2 characters",
            )

        logger.info(f"Searching: {query}")
        db = get_db_manager()
        issues = db.search_issues(query, limit=limit)

        return {
            "success": True,
            "query": query,
            "issues": issues,
            "count": len(issues),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CARD ENDPOINT - 法人カルテ
# ============================================================================
@app.get("/api/card/{company_name}")
@limiter.limit("30/minute")
async def get_company_card(
    request: Request,
    company_name: str,
) -> dict:
    """
    企業の法人カルテを取得

    Args:
        company_name: 企業名

    Returns:
        法人カルテデータ
    """
    try:
        logger.info(f"Generating card for: {company_name}")
        db = get_db_manager()
        records = db.get_all_records_for_company(company_name)

        if not records:
            raise HTTPException(
                status_code=404,
                detail=f"No records found for {company_name}",
            )

        # 統計情報を計算
        stats = db.get_stats_by_category(company_name)
        latest = records[0]

        return {
            "success": True,
            "company_name": company_name,
            "corporate_name": latest.get("company_info", {}).get("corporate_name"),
            "total_meetings": len(records),
            "latest_record": latest,
            "all_records": records,
            "stats": stats,
            "generated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CORPORATE CARD ENDPOINT - 法人カルテ（傘下の店舗ごとの課題有無を一覧化）
# ============================================================================
@app.get("/api/corporate-card/{corporate_name}")
@limiter.limit("30/minute")
async def get_corporate_card(
    request: Request,
    corporate_name: str,
) -> dict:
    """
    法人カルテを取得。傘下の店舗ごとに課題の有無・件数をまとめる。

    Args:
        corporate_name: 法人名

    Returns:
        法人カルテデータ（店舗別の課題サマリー）
    """
    try:
        logger.info(f"Generating corporate card for: {corporate_name}")
        db = get_db_manager()
        card = db.get_corporate_card(corporate_name)

        if card is None:
            raise HTTPException(
                status_code=404,
                detail=f"No corporation found: {corporate_name}",
            )

        return {
            "success": True,
            "corporate_name": card["corporate_name"],
            "store_count": len(card["stores"]),
            "stores_with_issues": sum(1 for s in card["stores"] if s["has_issues"]),
            "stores": card["stores"],
            "generated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating corporate card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================
@app.get("/api/health")
async def health_check() -> dict:
    """ヘルスチェック"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# フロントエンド静的ファイル配信（Next.js の書き出し済みビルドを同一オリジンで配信）
# 必ず /api/* などの他のルートより後に mount する（先着したルートが優先されるため）。
# ローカル開発時（web_dist が存在しない場合）はマウントせず、API単体として動作する。
# ============================================================================
_web_dist = Path(os.environ.get("WEB_DIST_DIR", "./web_dist"))
if _web_dist.is_dir():
    app.mount("/", StaticFiles(directory=_web_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
