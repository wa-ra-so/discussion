from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile
from datetime import datetime
from typing import Optional, List

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.core.pipeline import get_pipeline
from src.storage.sqlite_manager import get_db_manager
from src.utils.logger import get_logger
from src.config import settings
from schema.models import DiscussionRecord

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

# CORS設定（Next.jsからのリクエスト許可、環境変数 CORS_ORIGINS で上書き可能）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PROCESS ENDPOINT - 音声ファイル処理
# ============================================================================
@app.post("/api/process")
@limiter.limit("5/minute")
async def process_audio(
    request: Request,
    file: UploadFile = File(...),
    company_name: str = Form(...),
    corporate_name: Optional[str] = Form(None),
    contact_name: Optional[str] = Form(None),
    meeting_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
) -> dict:
    """
    音声ファイルを処理し、ディスカッション記録を生成

    Args:
        file: 音声ファイル (MP3/WAV)
        company_name: 店舗名
        corporate_name: 法人名（任意。単一店舗経営の場合は不要）
        contact_name: 接触者氏名
        meeting_date: 商談日時
        notes: 補足メモ

    Returns:
        DiscussionRecord の JSON
    """
    try:
        # ファイル検証
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

        logger.info(f"Processing audio: {file.filename} for {company_name}")

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(
            suffix=file_ext, delete=False
        ) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)

        try:
            # パイプラインで処理
            pipeline = get_pipeline()
            record, filepath = pipeline.process_and_save(
                audio_file=tmp_path,
                company_name=company_name,
                corporate_name=corporate_name,
                contact_name=contact_name,
                meeting_date=meeting_date,
                notes=notes,
            )

            # DB に保存
            try:
                db = get_db_manager()
                record_id = db.save_record(record)
                logger.info(f"Record saved to DB: {record_id}")
            except Exception as e:
                logger.warning(f"Failed to save to DB: {e}")

            # レスポンス構築
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
                        "category": issue.category.value,
                        "issue": issue.issue,
                        "priority": issue.priority,
                    }
                    for issue in record.priority_issues
                ],
                "dx_solutions": record.dx_solutions.model_dump(),
                "created_at": record.created_at.isoformat(),
            }

        finally:
            # 一時ファイルを削除
            tmp_path.unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
