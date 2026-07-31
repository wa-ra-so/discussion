import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from schema.models import DiscussionRecord
from src.core.audio_processor import AudioProcessor
from src.core.text_analyzer import TextAnalyzer
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DiscussionPipeline:
    """音声ファイル → JSON レコードへのエンドツーエンドパイプライン"""

    def __init__(self):
        """初期化"""
        self.audio_processor = AudioProcessor(
            model_size=settings.whisper_model
        )
        self.text_analyzer = TextAnalyzer()

    def process_audio_file(
        self,
        audio_file: Path,
        company_name: str,
        contact_name: Optional[str] = None,
        meeting_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DiscussionRecord:
        """
        音声ファイルを処理してディスカッション記録を生成

        Args:
            audio_file: 音声ファイルパス
            company_name: 店舗名（企業名）
            contact_name: 接触者氏名
            meeting_date: 商談日時（ISO 8601 形式）
            notes: 手動補足メモ

        Returns:
            DiscussionRecord: 構造化されたディスカッション記録
        """
        logger.info(f"Starting pipeline: {audio_file}")

        try:
            # Step 1: 音声ファイルを文字起こし
            logger.info("Step 1/3: Transcribing audio...")
            transcription_result = self.audio_processor.transcribe(
                audio_file, language="ja"
            )
            transcription_text = transcription_result["text"]
            logger.info(
                f"Transcription complete: {len(transcription_text)} characters"
            )

            # Step 2: テキストを解析
            logger.info("Step 2/3: Analyzing discussion content...")
            record = self.text_analyzer.analyze(
                transcription=transcription_text,
                company_name=company_name,
                contact_name=contact_name,
                meeting_date=meeting_date,
            )

            # Step 3: メモを追加
            if notes:
                record.notes = notes

            logger.info("Step 3/3: Pipeline complete")
            return record

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise

    def save_record(
        self, record: DiscussionRecord, output_dir: Optional[Path] = None
    ) -> Path:
        """
        ディスカッション記録を JSON ファイルとして保存

        Args:
            record: DiscussionRecord
            output_dir: 出力ディレクトリ（Noneの場合は設定値を使用）

        Returns:
            Path: 保存したファイルのパス
        """
        if output_dir is None:
            output_dir = settings.records_dir

        output_dir.mkdir(parents=True, exist_ok=True)

        # ファイル名を生成（meeting_id を使用）
        filename = f"{record.meeting_id}.json"
        filepath = output_dir / filename

        # JSON に変換して保存
        record_json = record.model_dump_json(indent=2)
        filepath.write_text(record_json, encoding="utf-8")

        logger.info(f"Record saved: {filepath}")
        return filepath

    def process_and_save(
        self,
        audio_file: Path,
        company_name: str,
        contact_name: Optional[str] = None,
        meeting_date: Optional[str] = None,
        notes: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> tuple[DiscussionRecord, Path]:
        """
        音声ファイルを処理して記録を保存（一括処理）

        Returns:
            (DiscussionRecord, 保存ファイルパス) のタプル
        """
        record = self.process_audio_file(
            audio_file=audio_file,
            company_name=company_name,
            contact_name=contact_name,
            meeting_date=meeting_date,
            notes=notes,
        )

        filepath = self.save_record(record, output_dir)

        return record, filepath


def get_pipeline() -> DiscussionPipeline:
    """グローバルパイプラインを取得（シングルトン）"""
    if not hasattr(get_pipeline, "_instance"):
        get_pipeline._instance = DiscussionPipeline()
    return get_pipeline._instance
