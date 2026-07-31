import json
import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from schema.models import DiscussionRecord
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SQLiteManager:
    """SQLite データベース管理"""

    def __init__(self, db_path: Path = settings.db_path):
        """初期化"""
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """データベースとテーブルを初期化"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # companies テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # meetings テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS meetings (
                    meeting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    meeting_uuid TEXT UNIQUE NOT NULL,
                    contact_name TEXT,
                    contact_email TEXT,
                    meeting_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(company_id)
                )
                """
            )

            # discussion_records テーブル（JSON ストア）
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS discussion_records (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER NOT NULL,
                    record_data JSON NOT NULL,
                    confidence_score REAL,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
                )
                """
            )

            # priority_issues テーブル（高速検索用）
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS priority_issues (
                    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER NOT NULL,
                    category TEXT,
                    issue TEXT,
                    priority INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (record_id) REFERENCES discussion_records(record_id)
                )
                """
            )

            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")

    def save_record(self, record: DiscussionRecord) -> int:
        """
        DiscussionRecord をデータベースに保存

        Args:
            record: DiscussionRecord

        Returns:
            int: record_id
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # company を取得/作成
            company_name = record.company_info.name
            cursor.execute("SELECT company_id FROM companies WHERE name = ?", (company_name,))
            result = cursor.fetchone()

            if result:
                company_id = result[0]
            else:
                cursor.execute(
                    "INSERT INTO companies (name) VALUES (?)",
                    (company_name,),
                )
                company_id = cursor.lastrowid

            # meeting を作成
            cursor.execute(
                """
                INSERT INTO meetings (company_id, meeting_uuid, contact_name, contact_email, meeting_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    record.meeting_id,
                    record.company_info.contact_name,
                    record.company_info.contact_email,
                    record.company_info.date.isoformat(),
                ),
            )
            meeting_id = cursor.lastrowid

            # discussion_record を保存
            record_json = record.model_dump_json()
            cursor.execute(
                """
                INSERT INTO discussion_records (meeting_id, record_data, confidence_score, summary)
                VALUES (?, ?, ?, ?)
                """,
                (
                    meeting_id,
                    record_json,
                    record.confidence_score,
                    record.summary,
                ),
            )
            record_id = cursor.lastrowid

            # priority_issues を保存
            for issue in record.priority_issues:
                cursor.execute(
                    """
                    INSERT INTO priority_issues (record_id, category, issue, priority)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        issue.category.value,
                        issue.issue,
                        issue.priority,
                    ),
                )

            conn.commit()
            logger.info(f"Record saved: {record.meeting_id} (record_id={record_id})")
            return record_id

    def get_meetings_by_company(
        self, company_name: str, limit: int = 100
    ) -> List[dict]:
        """
        企業の商談一覧を取得

        Args:
            company_name: 店舗名（企業名）
            limit: 取得件数

        Returns:
            商談リスト
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    c.name as company_name,
                    m.meeting_uuid,
                    m.contact_name,
                    m.meeting_date,
                    dr.confidence_score,
                    dr.summary
                FROM meetings m
                JOIN companies c ON m.company_id = c.company_id
                LEFT JOIN discussion_records dr ON m.meeting_id = dr.meeting_id
                WHERE c.name = ?
                ORDER BY m.meeting_date DESC
                LIMIT ?
                """,
                (company_name, limit),
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_companies(self, limit: int = 100) -> List[dict]:
        """
        すべての企業一覧を取得

        Args:
            limit: 取得件数

        Returns:
            企業リスト
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    c.company_id,
                    c.name,
                    COUNT(m.meeting_id) as meeting_count,
                    MAX(m.meeting_date) as last_meeting
                FROM companies c
                LEFT JOIN meetings m ON c.company_id = m.company_id
                GROUP BY c.company_id
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def search_issues(
        self, keyword: str, limit: int = 100
    ) -> List[dict]:
        """
        優先課題を検索

        Args:
            keyword: 検索キーワード
            limit: 取得件数

        Returns:
            マッチした課題リスト
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    c.name as company_name,
                    pi.category,
                    pi.issue,
                    pi.priority,
                    m.meeting_date
                FROM priority_issues pi
                JOIN discussion_records dr ON pi.record_id = dr.record_id
                JOIN meetings m ON dr.meeting_id = m.meeting_id
                JOIN companies c ON m.company_id = c.company_id
                WHERE pi.issue LIKE ? OR pi.category LIKE ?
                ORDER BY pi.priority DESC, m.meeting_date DESC
                LIMIT ?
                """,
                (f"%{keyword}%", f"%{keyword}%", limit),
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_record_json(self, meeting_uuid: str) -> Optional[dict]:
        """
        商談の JSON レコードを取得

        Args:
            meeting_uuid: Meeting UUID

        Returns:
            DiscussionRecord の JSON dict
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT dr.record_data
                FROM discussion_records dr
                JOIN meetings m ON dr.meeting_id = m.meeting_id
                WHERE m.meeting_uuid = ?
                """,
                (meeting_uuid,),
            )

            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None

    def get_all_records_for_company(self, company_name: str) -> List[dict]:
        """
        企業のすべての JSON レコードを取得（法人カルテ用）

        Args:
            company_name: 店舗名（企業名）

        Returns:
            DiscussionRecord の JSON dict リスト
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT dr.record_data
                FROM discussion_records dr
                JOIN meetings m ON dr.meeting_id = m.meeting_id
                JOIN companies c ON m.company_id = c.company_id
                WHERE c.name = ?
                ORDER BY m.meeting_date DESC
                """,
                (company_name,),
            )

            rows = cursor.fetchall()
            return [json.loads(row[0]) for row in rows]

    def get_stats_by_category(self, company_name: str) -> dict:
        """
        企業の課題カテゴリ別統計を取得

        Args:
            company_name: 店舗名（企業名）

        Returns:
            カテゴリ別の課題数
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    pi.category,
                    COUNT(*) as count,
                    AVG(pi.priority) as avg_priority
                FROM priority_issues pi
                JOIN discussion_records dr ON pi.record_id = dr.record_id
                JOIN meetings m ON dr.meeting_id = m.meeting_id
                JOIN companies c ON m.company_id = c.company_id
                WHERE c.name = ?
                GROUP BY pi.category
                """,
                (company_name,),
            )

            rows = cursor.fetchall()
            return {row[0]: {"count": row[1], "avg_priority": row[2]} for row in rows}


def get_db_manager() -> SQLiteManager:
    """グローバル DB マネージャを取得（シングルトン）"""
    if not hasattr(get_db_manager, "_instance"):
        get_db_manager._instance = SQLiteManager()
    return get_db_manager._instance
