import typer
from typing import Optional
from pathlib import Path
from src.utils.logger import setup_logger
from src.commands.process import process
from src.commands.list_meetings import list_meetings
from src.commands.search import search
from src.commands.card import card

app = typer.Typer(
    help="食べログ営業向け商談音声解析・法人カルテ自動生成システム"
)
logger = setup_logger(__name__)

# コマンドを統合
app.command()(process)
app.command(name="list-meetings")(list_meetings)
app.command()(search)
app.command()(card)


@app.command()
def list_meetings(
    company_name: Optional[str] = typer.Option(
        None, "--company", "-c", help="店舗名でフィルター"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="表示件数"),
) -> None:
    """
    商談記録の一覧を表示

    Example:
        discussion list-meetings --company "レストランA"
    """
    logger.info(f"Listing meetings (limit: {limit})")
    if company_name:
        logger.info(f"Filtering by company: {company_name}")
    typer.echo("✓ 商談記録を表示します...")
    # Phase 3 で実装


@app.command()
def search(
    query: str = typer.Argument(
        ..., help="検索キーワード"
    ),
    field: Optional[str] = typer.Option(
        None, "--field", "-f", help="検索対象フィールド (company, issue, solution など)"
    ),
) -> None:
    """
    商談記録を検索

    Example:
        discussion search "人手不足" --field "issue"
    """
    logger.info(f"Searching for: {query}")
    if field:
        logger.info(f"Search field: {field}")
    typer.echo(f"✓ '{query}' を検索します...")
    # Phase 3 で実装


@app.command()
def card(
    company_id: str = typer.Argument(
        ..., help="店舗ID または 店舗名"
    ),
    output_format: str = typer.Option(
        "json", "--format", "-f", help="出力形式 (json/markdown/pdf)"
    ),
) -> None:
    """
    法人カルテを生成

    Example:
        discussion card "レストランA" --format markdown
    """
    logger.info(f"Generating card for: {company_id}")
    logger.info(f"Output format: {output_format}")
    typer.echo(f"✓ '{company_id}' の法人カルテを生成します...")
    # Phase 3 で実装


@app.command()
def export(
    company_id: str = typer.Argument(
        ..., help="店舗ID または 店舗名"
    ),
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="出力ファイルパス"
    ),
    format: str = typer.Option(
        "json", "--format", "-f", help="出力形式 (json/markdown/pdf)"
    ),
) -> None:
    """
    商談記録をエクスポート

    Example:
        discussion export "レストランA" --format json --output output.json
    """
    logger.info(f"Exporting record for: {company_id}")
    logger.info(f"Output format: {format}")
    if output_file:
        logger.info(f"Output file: {output_file}")
    typer.echo(f"✓ '{company_id}' をエクスポートします...")
    # Phase 3 で実装


@app.command()
def init() -> None:
    """
    プロジェクトを初期化（ディレクトリ、DB作成）

    Example:
        discussion init
    """
    logger.info("Initializing project...")
    from src.config import settings

    typer.echo("✓ ディレクトリを作成しています...")
    typer.echo(f"  - Data directory: {settings.data_dir}")
    typer.echo(f"  - Audio directory: {settings.audio_dir}")
    typer.echo(f"  - Records directory: {settings.records_dir}")
    typer.echo(f"  - Database: {settings.db_path}")
    # Phase 1 で実装
    typer.echo("✓ 初期化が完了しました")


def main() -> None:
    """エントリーポイント"""
    app()


if __name__ == "__main__":
    main()
