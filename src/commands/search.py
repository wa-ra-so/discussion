import typer
from typing import Optional
from src.storage.sqlite_manager import get_db_manager
from src.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

app = typer.Typer(help="商談記録検索コマンド")


@app.command()
def search(
    query: str = typer.Argument(
        ..., help="検索キーワード"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="表示件数"),
) -> None:
    """
    商談記録内の優先課題を検索

    キーワードで課題内容やカテゴリを検索します。
    優先度の高い順、最新の商談順で表示されます。

    Example:
        discussion search "人手不足"
        discussion search "予約効率"
        discussion search "インバウンド" --limit 30
    """

    try:
        logger.info(f"Searching for keyword: {query}")
        db = get_db_manager()

        # 優先課題を検索
        issues = db.search_issues(query, limit=limit)

        if not issues:
            typer.echo()
            typer.echo(
                typer.style(
                    f"ℹ️ '{query}' に該当する課題は見つかりませんでした",
                    fg=typer.colors.YELLOW,
                )
            )
            raise typer.Exit()

        typer.echo()
        typer.echo(typer.style(f"【検索結果】'{query}' の検索結果", bold=True))
        typer.echo(f"件数: {len(issues)}")
        typer.echo()

        # カテゴリマッピング
        category_display = {
            "marketing": "📢 集客・マーケティング",
            "reservation_efficiency": "📅 予約・業務効率",
            "cost_reduction": "💰 コスト削減",
            "recruitment": "👥 採用・人財",
            "inbound": "🌍 インバウンド",
        }

        # テーブルヘッダ
        typer.echo(
            f"{'#':<3} {'企業名':<20} {'カテゴリ':<15} {'優先度':<5} {'課題内容':<50}"
        )
        typer.echo("-" * 95)

        for i, issue in enumerate(issues, 1):
            company_name = issue["company_name"][:19]
            category = issue["category"]
            category_label = category_display.get(category, category)

            # 優先度の表示
            priority_str = "🔴" * issue["priority"] if issue["priority"] else "−"

            # 課題内容を省略
            issue_text = (
                issue["issue"][:47] + "..."
                if issue["issue"] and len(issue["issue"]) > 47
                else issue["issue"]
            )

            typer.echo(
                f"{i:<3} {company_name:<20} {category_label:<15} {priority_str:<5} {issue_text:<50}"
            )

        typer.echo()

        # サマリー統計
        category_count = {}
        for issue in issues:
            cat = issue["category"]
            category_count[cat] = category_count.get(cat, 0) + 1

        typer.echo(typer.style("【カテゴリ別件数】", bold=True))
        for category, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
            label = category_display.get(category, category)
            typer.echo(f"  {label}: {count}件")

        typer.echo()

    except Exception as e:
        typer.echo(typer.style(f"✗ エラーが発生しました: {e}", fg=typer.colors.RED))
        logger.error(f"Error searching issues: {e}")
        raise typer.Exit(code=1)
