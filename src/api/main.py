from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile
from datetime import datetime
from typing import Optional, List

from src.core.pipeline import get_pipeline
from src.storage.sqlite_manager import get_db_manager
from src.utils.logger import get_logger
from src.config import settings
from schema.models import DiscussionRecord

logger = get_logger(__name__)

# FastAPI アプリケーション
app = FastAPI(
    title="Discussion System API",
    description="食べログ営業向け商談解析API",
    version="1.0.0",
)

# CORS設定（Next.jsからのリクエスト許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PROCESS ENDPOINT - 音声ファイル処理
# ============================================================================
@app.post("/api/process")
async def process_audio(
    file: UploadFile = File(...),
    company_name: str = Form(...),
    contact_name: Optional[str] = Form(None),
    meeting_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
) -> dict:
    """
    音声ファイルを処理し、ディスカッション記録を生成

    Args:
        file: 音声ファイル (MP3/WAV)
        company_name: 店舗名
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
async def list_meetings(
    company_name: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    商談記録を一覧取得

    Args:
        company_name: フィルター対象企業（Noneの場合は全企業）
        limit: 取得件数

    Returns:
        企業・商談情報のリスト
    """
    try:
        logger.info(f"Listing meetings: company={company_name}, limit={limit}")
        db = get_db_manager()

        if company_name:
            # 特定企業の商談一覧
            meetings = db.get_meetings_by_company(company_name, limit=limit)
            return {
                "success": True,
                "company_name": company_name,
                "meetings": meetings,
                "count": len(meetings),
            }
        else:
            # 全企業一覧
            companies = db.get_all_companies(limit=limit)
            return {
                "success": True,
                "companies": companies,
                "count": len(companies),
            }

    except Exception as e:
        logger.error(f"Error listing meetings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SEARCH ENDPOINT - 課題検索
# ============================================================================
@app.get("/api/search")
async def search_issues(
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
async def get_company_card(
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
