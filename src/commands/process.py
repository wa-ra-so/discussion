import typer
from pathlib import Path
from typing import Optional
from datetime import datetime
from src.core.pipeline import get_pipeline
from src.storage.sqlite_manager import get_db_manager
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

app = typer.Typer(help="音声ファイル処理コマンド")


@app.command()
def process(
    audio_file: Path = typer.Argument(
        ...,
        help="商談音声ファイルのパス (MP3/WAV)",
        exists=True,
    ),
    company_name: str = typer.Option(
        ..., "--company", "-c", help="店舗名"
    ),
    corporate_name: Optional[str] = typer.Option(
        None, "--corporate", "-corp", help="法人名（任意。単一店舗経営の場合は不要）"
    ),
    contact_name: Optional[str] = typer.Option(
        None, "--contact", "-n", help="接触者氏名"
    ),
    meeting_date: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="商談日時 (ISO 8601 形式: 2024-01-31T14:00:00)",
    ),
    notes: Optional[str] = typer.Option(
        None, "--notes", help="手動補足メモ"
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="出力ディレクトリ（デフォルト: ./data/records）",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="詳細ログを出力"
    ),
) -> None:
    """
    商談音声ファイルを処理し、ディスカッション内容を自動抽出

    音声ファイルから以下の処理を実行します：
    1. 音声 → テキスト（Whisper）
    2. テキスト → ディスカッション項目（Claude API）
    3. 結果を JSON で保存

    Example:
        discussion process meeting.wav --company "レストランA" --contact "山田太郎"
        discussion process meeting.mp3 -c "レストランB" -d "2024-01-31T14:00:00"
    """

    # ロギングレベルの設定
    if verbose:
        logger.setLevel("DEBUG")

    # 検証
    if not audio_file.exists():
        typer.echo(
            typer.style(
                f"✗ エラー: ファイルが見つかりません: {audio_file}",
                fg=typer.colors.RED,
            )
        )
        raise typer.Exit(code=1)

    supported_formats = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
    if audio_file.suffix.lower() not in supported_formats:
        typer.echo(
            typer.style(
                f"✗ エラー: サポートされていないフォーマット: {audio_file.suffix}",
                fg=typer.colors.RED,
            )
        )
        raise typer.Exit(code=1)

    if meeting_date:
        try:
            datetime.fromisoformat(meeting_date)
        except ValueError:
            typer.echo(
                typer.style(
                    f"✗ エラー: 日時フォーマットが不正です: {meeting_date}",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

    # パイプラインを実行
    try:
        typer.echo()
        typer.echo(typer.style("🎤 商談音声解析を開始します", fg=typer.colors.BLUE))
        typer.echo(f"   ファイル: {audio_file.name}")
        typer.echo(f"   店舗名: {company_name}")
        if corporate_name:
            typer.echo(f"   法人名: {corporate_name}")
        if contact_name:
            typer.echo(f"   接触者: {contact_name}")
        if meeting_date:
            typer.echo(f"   日時: {meeting_date}")
        typer.echo()

        # パイプライン実行
        pipeline = get_pipeline()
        record, filepath = pipeline.process_and_save(
            audio_file=audio_file,
            company_name=company_name,
            corporate_name=corporate_name,
            contact_name=contact_name,
            meeting_date=meeting_date,
            notes=notes,
            output_dir=output_dir,
        )

        # DB に保存
        try:
            db = get_db_manager()
            record_id = db.save_record(record)
            logger.info(f"Record saved to database: record_id={record_id}")
        except Exception as e:
            logger.warning(f"Failed to save to database: {e}")

        # 成功メッセージ
        typer.echo(typer.style("✓ 処理が完了しました！", fg=typer.colors.GREEN))
        typer.echo()
        typer.echo(typer.style("【抽出結果】", bold=True))
        typer.echo(f"  Meeting ID: {record.meeting_id}")
        typer.echo(f"  保存先: {filepath}")
        typer.echo(f"  信頼度: {record.confidence_score:.1%}")
        typer.echo()

        # 抽出された優先課題を表示
        if record.priority_issues:
            typer.echo(typer.style("【優先課題】", bold=True))
            for i, issue in enumerate(record.priority_issues, 1):
                priority_str = "🔴" * issue.priority if issue.priority else "−"
                typer.echo(
                    f"  {i}. [{issue.category}] {issue.issue} {priority_str}"
                )
            typer.echo()

        # 提案ソリューションを表示
        if record.dx_solutions:
            typer.echo(typer.style("【DXソリューション提案】", bold=True))
            if record.dx_solutions.revenue_maximization:
                typer.echo(
                    f"  売上最大化: {', '.join(record.dx_solutions.revenue_maximization)}"
                )
            if record.dx_solutions.efficiency_cost_reduction:
                typer.echo(
                    f"  効率化: {', '.join(record.dx_solutions.efficiency_cost_reduction)}"
                )
            if record.dx_solutions.recruitment_market_development:
                typer.echo(
                    f"  採用・市場: {', '.join(record.dx_solutions.recruitment_market_development)}"
                )
            typer.echo()

        typer.echo(typer.style("💾 JSON ファイルが保存されました", fg=typer.colors.CYAN))
        typer.echo(f"   {filepath}")

    except FileNotFoundError as e:
        typer.echo(
            typer.style(f"✗ エラー: ファイルが見つかりません: {e}", fg=typer.colors.RED)
        )
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(
            typer.style(f"✗ エラーが発生しました: {e}", fg=typer.colors.RED)
        )
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(code=1)
