from pathlib import Path
from typing import Optional
from datetime import datetime
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AudioProcessor:
    """音声ファイルをテキストに変換"""

    def __init__(self, model_size: str = "base"):
        """
        初期化

        Args:
            model_size: Whisper モデルサイズ（tiny, base, small, medium, large）
        """
        import whisper  # 重い依存のため実際に使うときだけ読み込む

        logger.info(f"Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)
        self.model_size = model_size

    def transcribe(
        self, audio_file: Path, language: str = "ja"
    ) -> dict:
        """
        音声ファイルを文字起こし

        Args:
            audio_file: 音声ファイルパス (MP3/WAV)
            language: 言語コード (ja, en など)

        Returns:
            {
                "text": "全体の文字起こし",
                "language": "ja",
                "duration": 600.5,
                "segments": [
                    {"start": 0.0, "end": 10.5, "text": "..."},
                    ...
                ],
                "processing_time": 15.2
            }
        """
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        logger.info(f"Transcribing audio: {audio_file}")
        start_time = datetime.now()

        try:
            # Whisper で文字起こし
            result = self.model.transcribe(
                str(audio_file),
                language=language,
                verbose=False,
            )

            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Transcription complete. Duration: {result['duration']:.1f}s, "
                f"Processing time: {processing_time:.1f}s"
            )

            return {
                "text": result["text"],
                "language": result.get("language", language),
                "duration": result.get("duration", 0),
                "segments": result.get("segments", []),
                "processing_time": processing_time,
            }

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def transcribe_batch(
        self, audio_files: list[Path], language: str = "ja"
    ) -> list[dict]:
        """
        複数の音声ファイルを一括文字起こし

        Args:
            audio_files: 音声ファイルパスのリスト
            language: 言語コード

        Returns:
            文字起こし結果のリスト
        """
        results = []
        for audio_file in audio_files:
            try:
                result = self.transcribe(audio_file, language)
                result["file"] = str(audio_file)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {audio_file}: {e}")
                results.append(
                    {
                        "file": str(audio_file),
                        "error": str(e),
                        "text": None,
                    }
                )

        return results


def get_audio_processor() -> AudioProcessor:
    """グローバルオーディオプロセッサを取得（シングルトン）"""
    if not hasattr(get_audio_processor, "_instance"):
        get_audio_processor._instance = AudioProcessor(
            model_size=settings.whisper_model
        )
    return get_audio_processor._instance
