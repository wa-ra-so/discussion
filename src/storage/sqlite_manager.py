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

            # corporations テーブル（法人）
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS corporations (
                    corporation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # companies テーブル（店舗）。法人への紐付けは任意（単一店舗経営もあるため）。
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    corporation_id INTEGER,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (corporation_id) REFERENCES corporations(corporation_id)
                )
                """
            )
            self._ensure_column(
                conn, "companies", "corporation_id", "INTEGER REFERENCES corporations(corporation_id)"
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

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        """既存テーブルに列が無ければ追加する（簡易マイグレーション）"""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column}")
            logger.info(f"Migrated: added column {column} to {table}")

    def _get_or_create_corporation(
        self, cursor: sqlite3.Cursor, corporate_name: Optional[str]
    ) -> Optional[int]:
        """法人を取得/作成。corporate_name が None の場合は None を返す"""
        if not corporate_name:
            return None

        cursor.execute(
            "SELECT corporation_id FROM corporations WHERE name = ?", (corporate_name,)
        )
        result = cursor.fetchone()
        if result:
            return result[0]

        cursor.execute("INSERT INTO corporations (name) VALUES (?)", (corporate_name,))
        return cursor.lastrowid

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

            corporation_id = self._get_or_create_corporation(
                cursor, record.company_info.corporate_name
            )

            # company（店舗）を取得/作成
            company_name = record.company_info.name
            cursor.execute("SELECT company_id, corporation_id FROM companies WHERE name = ?", (company_name,))
            result = cursor.fetchone()

            if result:
                company_id = result[0]
                # 法人名が新たに分かった場合は紐付けを更新する
                if corporation_id and not result[1]:
                    cursor.execute(
                        "UPDATE companies SET corporation_id = ? WHERE company_id = ?",
                        (corporation_id, company_id),
                    )
            else:
                cursor.execute(
                    "INSERT INTO companies (name, corporation_id) VALUES (?, ?)",
                    (company_name, corporation_id),
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
        店舗の商談一覧を取得

        Args:
            company_name: 店舗名
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
                    corp.name as corporate_name,
                    m.meeting_uuid,
                    m.contact_name,
                    m.meeting_date,
                    dr.confidence_score,
                    dr.summary
                FROM meetings m
                JOIN companies c ON m.company_id = c.company_id
                LEFT JOIN corporations corp ON c.corporation_id = corp.corporation_id
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
        すべての店舗一覧を取得

        Args:
            limit: 取得件数

        Returns:
            店舗リスト（法人名を含む）
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    c.company_id,
                    c.name,
                    corp.name as corporate_name,
                    COUNT(m.meeting_id) as meeting_count,
                    MAX(m.meeting_date) as last_meeting
                FROM companies c
                LEFT JOIN corporations corp ON c.corporation_id = corp.corporation_id
                LEFT JOIN meetings m ON c.company_id = m.company_id
                GROUP BY c.company_id
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_corporations(self, limit: int = 100) -> List[dict]:
        """
        すべての法人一覧を取得（傘下の店舗数・課題ありの店舗数つき）

        Args:
            limit: 取得件数

        Returns:
            法人リスト
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    corp.corporation_id,
                    corp.name,
                    COUNT(DISTINCT c.company_id) as store_count,
                    COUNT(DISTINCT m.meeting_id) as meeting_count,
                    MAX(m.meeting_date) as last_meeting
                FROM corporations corp
                LEFT JOIN companies c ON c.corporation_id = corp.corporation_id
                LEFT JOIN meetings m ON m.company_id = c.company_id
                GROUP BY corp.corporation_id
                ORDER BY corp.updated_at DESC
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
                    corp.name as corporate_name,
                    pi.category,
                    pi.issue,
                    pi.priority,
                    m.meeting_date
                FROM priority_issues pi
                JOIN discussion_records dr ON pi.record_id = dr.record_id
                JOIN meetings m ON dr.meeting_id = m.meeting_id
                JOIN companies c ON m.company_id = c.company_id
                LEFT JOIN corporations corp ON c.corporation_id = corp.corporation_id
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
        店舗のすべての JSON レコードを取得（店舗カルテ用）

        Args:
            company_name: 店舗名

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
        店舗の課題カテゴリ別統計を取得

        Args:
            company_name: 店舗名

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

    def get_corporate_card(self, corporate_name: str) -> Optional[dict]:
        """
        法人カルテ用データを取得。傘下の店舗ごとに課題の有無・件数をまとめる。

        Args:
            corporate_name: 法人名

        Returns:
            {
                "corporate_name": str,
                "stores": [
                    {
                        "company_name": str,
                        "meeting_count": int,
                        "last_meeting": str | None,
                        "issue_count": int,
                        "has_issues": bool,
                        "top_issue": str | None,
                    },
                    ...
                ]
            }
            法人が存在しない場合は None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT corporation_id FROM corporations WHERE name = ?", (corporate_name,)
            )
            corp_row = cursor.fetchone()
            if not corp_row:
                return None
            corporation_id = corp_row["corporation_id"]

            cursor.execute(
                """
                SELECT c.company_id, c.name
                FROM companies c
                WHERE c.corporation_id = ?
                ORDER BY c.name
                """,
                (corporation_id,),
            )
            stores = []
            for store_row in cursor.fetchall():
                company_id = store_row["company_id"]

                cursor.execute(
                    """
                    SELECT COUNT(*) as meeting_count, MAX(m.meeting_date) as last_meeting
                    FROM meetings m
                    WHERE m.company_id = ?
                    """,
                    (company_id,),
                )
                meeting_stats = cursor.fetchone()

                cursor.execute(
                    """
                    SELECT pi.issue, pi.priority
                    FROM priority_issues pi
                    JOIN discussion_records dr ON pi.record_id = dr.record_id
                    JOIN meetings m ON dr.meeting_id = m.meeting_id
                    WHERE m.company_id = ?
                    ORDER BY pi.priority DESC
                    """,
                    (company_id,),
                )
                issues = cursor.fetchall()

                stores.append(
                    {
                        "company_name": store_row["name"],
                        "meeting_count": meeting_stats["meeting_count"] or 0,
                        "last_meeting": meeting_stats["last_meeting"],
                        "issue_count": len(issues),
                        "has_issues": len(issues) > 0,
                        "top_issue": issues[0]["issue"] if issues else None,
                    }
                )

            return {"corporate_name": corporate_name, "stores": stores}

def get_db_manager() -> SQLiteManager:
    """グローバル DB マネージャを取得（シングルトン）"""
    if not hasattr(get_db_manager, "_instance"):
        get_db_manager._instance = SQLiteManager()
    return get_db_manager._instance
