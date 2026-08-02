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
    """文字起こし済みテキスト または 音声ファイル → JSON レコードへのエンドツーエンドパイプライン"""

    def __init__(self):
        """初期化（Whisperモデルは実際に音声処理が呼ばれるまで遅延ロード）"""
        self._audio_processor: Optional[AudioProcessor] = None
        self.text_analyzer = TextAnalyzer()

    @property
    def audio_processor(self) -> AudioProcessor:
        if self._audio_processor is None:
            self._audio_processor = AudioProcessor(model_size=settings.whisper_model)
        return self._audio_processor

    def process_transcript(
        self,
        transcript_text: str,
        company_name: str,
        corporate_name: Optional[str] = None,
        contact_name: Optional[str] = None,
        meeting_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DiscussionRecord:
        """
        文字起こし済みテキストを解析してディスカッション記録を生成
        """
        logger.info(f"Starting text pipeline for: {company_name}")

        try:
            record = self.text_analyzer.analyze(
                transcription=transcript_text,
                company_name=company_name,
                corporate_name=corporate_name,
                contact_name=contact_name,
                meeting_date=meeting_date,
            )

            if notes:
                record.notes = notes

            logger.info("Text pipeline complete")
            return record

        except Exception as e:
            logger.error(f"Text pipeline failed: {e}")
            raise

    def process_audio_file(
        self,
        audio_file: Path,
        company_name: str,
        corporate_name: Optional[str] = None,
        contact_name: Optional[str] = None,
        meeting_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DiscussionRecord:
        """
        音声ファイルを文字起こし（Whisper）してから解析し、ディスカッション記録を生成
        """
        logger.info(f"Starting audio pipeline: {audio_file}")

        try:
            logger.info("Step 1/2: Transcribing audio...")
            transcription_result = self.audio_processor.transcribe(audio_file, language="ja")
            transcription_text = transcription_result["text"]
            logger.info(f"Transcription complete: {len(transcription_text)} characters")

            logger.info("Step 2/2: Analyzing discussion content...")
            record = self.process_transcript(
                transcript_text=transcription_text,
                company_name=company_name,
                corporate_name=corporate_name,
                contact_name=contact_name,
                meeting_date=meeting_date,
                notes=notes,
            )

            logger.info("Audio pipeline complete")
            return record

        except Exception as e:
            logger.error(f"Audio pipeline failed: {e}")
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

        filename = f"{record.meeting_id}.json"
        filepath = output_dir / filename

        record_json = record.model_dump_json(indent=2)
        filepath.write_text(record_json, encoding="utf-8")

        logger.info(f"Record saved: {filepath}")
        return filepath

    def process_and_save(
        self,
        company_name: str,
        transcript_text: Optional[str] = None,
        audio_file: Optional[Path] = None,
        corporate_name: Optional[str] = None,
        contact_name: Optional[str] = None,
        meeting_date: Optional[str] = None,
        notes: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> tuple[DiscussionRecord, Path]:
        """
        テキストまたは音声ファイルを処理して記録を保存（一括処理）。
        transcript_text と audio_file はどちらか一方を指定する。

        Returns:
            (DiscussionRecord, 保存ファイルパス) のタプル
        """
        if transcript_text is not None and audio_file is not None:
            raise ValueError("transcript_text と audio_file は同時に指定できません")
        if transcript_text is None and audio_file is None:
            raise ValueError("transcript_text か audio_file のどちらかを指定してください")

        if audio_file is not None:
            record = self.process_audio_file(
                audio_file=audio_file,
                company_name=company_name,
                corporate_name=corporate_name,
                contact_name=contact_name,
                meeting_date=meeting_date,
                notes=notes,
            )
        else:
            record = self.process_transcript(
                transcript_text=transcript_text,
                company_name=company_name,
                corporate_name=corporate_name,
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
