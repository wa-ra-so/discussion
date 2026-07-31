import typer
from typing import Optional
from src.storage.sqlite_manager import get_db_manager
from src.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

app = typer.Typer(help="商談記録表示コマンド")


@app.command()
def list_meetings(
    company_name: Optional[str] = typer.Option(
        None, "--company", "-c", help="店舗名でフィルター"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="表示件数"),
) -> None:
    """
    商談記録の一覧を表示

    デフォルトではすべての企業の最新商談を表示します。
    --company オプションで特定の企業に絞り込めます。

    Example:
        discussion list-meetings
        discussion list-meetings --company "レストランA" --limit 20
    """

    try:
        db = get_db_manager()

        if company_name:
            # 特定企業の商談一覧
            logger.info(f"Listing meetings for company: {company_name}")
            meetings = db.get_meetings_by_company(company_name, limit=limit)

            if not meetings:
                typer.echo(
                    typer.style(
                        f"ℹ️ '{company_name}' の商談記録はありません",
                        fg=typer.colors.YELLOW,
                    )
                )
                raise typer.Exit()

            typer.echo()
            typer.echo(typer.style(f"【{company_name}】の商談記録", bold=True))
            typer.echo(f"件数: {len(meetings)}")
            typer.echo()

            # テーブルヘッダ
            typer.echo(
                f"{'#':<3} {'日時':<20} {'接触者':<15} {'信頼度':<8} {'概要':<40}"
            )
            typer.echo("-" * 90)

            for i, meeting in enumerate(meetings, 1):
                meeting_date = (
                    datetime.fromisoformat(meeting["meeting_date"]).strftime("%Y-%m-%d %H:%M")
                    if meeting["meeting_date"]
                    else "不明"
                )
                contact = meeting["contact_name"] or "不明"
                confidence = (
                    f"{meeting['confidence_score']:.0%}"
                    if meeting["confidence_score"]
                    else "−"
                )
                summary = (
                    meeting["summary"][:37] + "..."
                    if meeting["summary"] and len(meeting["summary"]) > 37
                    else meeting["summary"] or "−"
                )

                typer.echo(
                    f"{i:<3} {meeting_date:<20} {contact:<15} {confidence:<8} {summary:<40}"
                )

            typer.echo()

        else:
            # すべての企業一覧
            logger.info("Listing all companies")
            companies = db.get_all_companies(limit=limit)

            if not companies:
                typer.echo(
                    typer.style(
                        "ℹ️ 商談記録がまだありません",
                        fg=typer.colors.YELLOW,
                    )
                )
                raise typer.Exit()

            typer.echo()
            typer.echo(typer.style("【企業一覧】", bold=True))
            typer.echo(f"件数: {len(companies)}")
            typer.echo()

            # テーブルヘッダ
            typer.echo(
                f"{'#':<3} {'企業名':<30} {'商談数':<8} {'最終商談':<20}"
            )
            typer.echo("-" * 65)

            for i, company in enumerate(companies, 1):
                last_meeting = (
                    datetime.fromisoformat(company["last_meeting"]).strftime("%Y-%m-%d")
                    if company["last_meeting"]
                    else "−"
                )

                typer.echo(
                    f"{i:<3} {company['name']:<30} {company['meeting_count']:<8} {last_meeting:<20}"
                )

            typer.echo()
            typer.echo(
                typer.style("💡 特定企業の商談を見る: ", fg=typer.colors.CYAN, bold=True)
                + 'discussion list-meetings --company "企業名"'
            )
            typer.echo()

    except Exception as e:
        typer.echo(typer.style(f"✗ エラーが発生しました: {e}", fg=typer.colors.RED))
        logger.error(f"Error listing meetings: {e}")
        raise typer.Exit(code=1)
