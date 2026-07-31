import typer
import json
from typing import Optional
from pathlib import Path
from src.storage.sqlite_manager import get_db_manager
from src.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

app = typer.Typer(help="法人カルテ生成コマンド")


def generate_markdown_card(company_name: str, records: list[dict]) -> str:
    """Markdown 形式の法人カルテを生成"""
    if not records:
        return f"# {company_name}\n\n商談記録がありません。"

    # 最新の記録を取得（進捗状況用）
    latest = records[0]
    company_info = latest.get("company_info", {})
    discussions = latest.get("discussions", {})
    priority_issues = latest.get("priority_issues", [])
    dx_solutions = latest.get("dx_solutions", {})

    md = f"""# 法人カルテ: {company_name}

## 企業情報
- **店舗名**: {company_name}
- **接触者**: {company_info.get("contact_name", "不明")}
- **最終更新**: {datetime.now().strftime("%Y年%m月%d日")}
- **商談件数**: {len(records)}件

---

## 優先課題（最新商談）

### 主要な経営課題
"""

    if priority_issues:
        for issue in priority_issues[:5]:  # Top 5
            priority_str = "🔴" * issue.get("priority", 1)
            md += f"- [{issue.get('category', '不明')}] {issue.get('issue', '−')} {priority_str}\n"
    else:
        md += "- 記録なし\n"

    md += "\n---\n\n## ディスカッション内容（最新商談）\n\n"

    # 採用・人手
    recruitment = discussions.get("recruitment", {})
    if recruitment:
        md += f"""### 採用・人手
- **課題**: {recruitment.get("assumed_issues", "−")}
- **現在**: 社員{recruitment.get("current_staff", {}).get("employees", "−")}名, パート・アルバイト{recruitment.get("current_staff", {}).get("part_time", "−")}名
- **理想**: 社員{recruitment.get("ideal_staff", {}).get("employees", "−")}名, パート・アルバイト{recruitment.get("ideal_staff", {}).get("part_time", "−")}名
- **施策**: {recruitment.get("current_initiatives", "−")}

"""

    # 集客・売上
    sales = discussions.get("sales", {})
    if sales:
        avg_spend = sales.get("average_customer_spend", {})
        utilization = sales.get("seat_utilization", {})
        md += f"""### 集客・売上
- **客単価**: 昼{avg_spend.get("lunch", "−")}円 / 夜{avg_spend.get("dinner", "−")}円
- **席稼働率**: 平日{utilization.get("weekday", "−")}% / 週末{utilization.get("weekend", "−")}%
- **客層**: {sales.get("customer_segment", "−")}
- **施策**: {sales.get("current_initiatives", "−")}

"""

    # 予約・業務効率
    booking = discussions.get("booking_efficiency", {})
    if booking:
        md += f"""### 予約・業務効率
- **予約方法**: {", ".join(booking.get("current_reservation_method", [])) if booking.get("current_reservation_method") else "−"}
- **電話対応**: {booking.get("phone_response", {}).get("frequency", "−")}
- **発注時間**: 約{booking.get("daily_ordering_time", "−")}分/日
- **発注責当**: {booking.get("ordering_responsible", "−")}

"""

    # インバウンド
    inbound = discussions.get("inbound", {})
    if inbound:
        md += f"""### インバウンド集客
- **月間外国人客**: {inbound.get("monthly_foreign_guests", "−")}名
- **多言語対応**: {inbound.get("multilingual_support", "−")}

"""

    # DX ソリューション提案
    if dx_solutions:
        md += f"""---

## 推奨ソリューション

### 売上最大化
"""
        for sol in dx_solutions.get("revenue_maximization", []):
            md += f"- {sol}\n"

        md += f"""
### 業務効率・コスト削減
"""
        for sol in dx_solutions.get("efficiency_cost_reduction", []):
            md += f"- {sol}\n"

        md += f"""
### 採用・市場開拓
"""
        for sol in dx_solutions.get("recruitment_market_development", []):
            md += f"- {sol}\n"

    # 商談履歴
    md += f"""

---

## 商談履歴

"""
    for i, record in enumerate(records, 1):
        meeting_info = record.get("company_info", {})
        meeting_date = meeting_info.get("date", "不明")
        if isinstance(meeting_date, str):
            try:
                meeting_date = datetime.fromisoformat(meeting_date).strftime("%Y年%m月%d日")
            except:
                pass
        confidence = record.get("confidence_score", 0)

        md += f"**{i}. {meeting_date}** (信頼度: {confidence:.0%})\n"
        md += f"- 接触者: {meeting_info.get('contact_name', '−')}\n"
        md += f"- 要約: {record.get('summary', '−')}\n\n"

    return md


def generate_json_card(company_name: str, records: list[dict]) -> str:
    """JSON 形式の法人カルテを生成"""
    card = {
        "company_name": company_name,
        "generated_at": datetime.now().isoformat(),
        "total_meetings": len(records),
        "records": records,
    }
    return json.dumps(card, indent=2, ensure_ascii=False)


@app.command()
def card(
    company_name: str = typer.Argument(
        ..., help="店舗名（企業名）"
    ),
    output_format: str = typer.Option(
        "markdown", "--format", "-f", help="出力形式 (markdown/json)"
    ),
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="出力ファイルパス（Noneの場合は表示のみ）"
    ),
) -> None:
    """
    法人カルテを生成・表示

    店舗のすべての商談履歴を集約した法人カルテを生成します。
    Markdown 形式で表示・保存できます。

    Example:
        discussion card "レストランA"
        discussion card "レストランA" --format json --output card.json
    """

    try:
        logger.info(f"Generating card for: {company_name}")
        db = get_db_manager()

        # 企業のすべてのレコードを取得
        records = db.get_all_records_for_company(company_name)

        if not records:
            typer.echo()
            typer.echo(
                typer.style(
                    f"ℹ️ '{company_name}' の商談記録はありません",
                    fg=typer.colors.YELLOW,
                )
            )
            raise typer.Exit()

        # 出力形式に応じてカルテを生成
        if output_format == "json":
            card_content = generate_json_card(company_name, records)
        else:  # markdown
            card_content = generate_markdown_card(company_name, records)

        # ファイルに保存または表示
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(card_content, encoding="utf-8")
            typer.echo()
            typer.echo(
                typer.style("✓ 法人カルテが保存されました", fg=typer.colors.GREEN)
            )
            typer.echo(f"  {output_file}")
            typer.echo()
        else:
            typer.echo()
            typer.echo(card_content)
            typer.echo()

    except Exception as e:
        typer.echo(typer.style(f"✗ エラーが発生しました: {e}", fg=typer.colors.RED))
        logger.error(f"Error generating card: {e}")
        raise typer.Exit(code=1)
