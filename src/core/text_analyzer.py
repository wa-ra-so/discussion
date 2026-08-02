import json
import anthropic
from datetime import datetime
from typing import Optional
from schema.models import DiscussionRecord, CompanyInfo, Discussions
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TextAnalyzer:
    """Claude API を使ってテキストをディスカッション項目に解析"""

    def __init__(self):
        """初期化"""
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def analyze(
        self,
        transcription: str,
        company_name: str,
        corporate_name: Optional[str] = None,
        contact_name: Optional[str] = None,
        meeting_date: Optional[str] = None,
    ) -> DiscussionRecord:
        """
        音声書き起こしテキストをディスカッション項目に解析

        Args:
            transcription: 音声書き起こしテキスト
            company_name: 店舗名
            corporate_name: 法人名（任意）
            contact_name: 接触者氏名
            meeting_date: 商談日時（ISO 8601 形式）

        Returns:
            DiscussionRecord: 構造化されたディスカッション記録
        """
        logger.info(f"Analyzing transcription for: {company_name}")

        # プロンプト構築
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            transcription, company_name, corporate_name, contact_name, meeting_date
        )

        try:
            # Claude API を呼び出し
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # JSON を抽出
            response_text = message.content[0].text
            structured_data = self._extract_json(response_text)

            # DiscussionRecord を構築
            record = self._build_discussion_record(
                structured_data, company_name, corporate_name, contact_name, meeting_date
            )

            logger.info(
                f"Analysis complete. Confidence: {record.confidence_score:.2f}"
            )
            return record

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise

    def _build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        return """あなたは食べログの営業ヒアリング記録を分析するAIです。

商談音声の書き起こしテキストが与えられます。
以下の6つのディスカッション項目から情報を抽出し、JSONフォーマットで返してください：

1. 採用・人手（recruitment）：スタッフ構成、採用課題、求人施策
2. 集客・売上（sales）：客単価、席稼働率、客層、売上施策
3. 予約・業務効率（booking_efficiency）：予約システム、発注業務、オペレーション課題
4. インバウンド集客（inbound）：外国人客対応、多言語対応状況
5. 優先課題（priority_issues）：複数の課題を優先度付け
6. DXソリューション提案（dx_solutions）：食べログの提案ソリューション

【重要】
- 確実に抽出できた情報のみを記入してください
- 推測や補完は避けてください
- 不確実な情報や曖昧な箇所は記入しないでください
- 各項目の confidence フィールドで信頼度を記入（0.0-1.0）
- JSON フォーマットで返してください

【JSON スキーマ】
{
  "discussions": {
    "recruitment": {
      "assumed_issues": "string or null",
      "current_staff": {"employees": number or null, "part_time": number or null},
      "ideal_staff": {"employees": number or null, "part_time": number or null},
      "hiring_needs": "string or null",
      "current_initiatives": "string or null"
    },
    "sales": {
      "average_customer_spend": {"lunch": number or null, "dinner": number or null},
      "seat_utilization": {"weekday": number or null, "weekend": number or null},
      "customer_segment": "string or null",
      "current_initiatives": "string or null"
    },
    "booking_efficiency": {
      "current_reservation_method": ["string"],
      "phone_response": {"frequency": "string or null", "daily_calls": number or null},
      "daily_ordering_time": number or null,
      "ordering_responsible": "string or null"
    },
    "inbound": {
      "monthly_foreign_guests": number or null,
      "multilingual_support": "string or null"
    }
  },
  "priority_issues": [
    {
      "category": "string",
      "issue": "string",
      "priority": number (1-5)
    }
  ],
  "dx_solutions": {
    "revenue_maximization": ["string"],
    "efficiency_cost_reduction": ["string"],
    "recruitment_market_development": ["string"]
  },
  "summary": "string",
  "confidence_score": number (0.0-1.0)
}"""

    def _build_user_prompt(
        self,
        transcription: str,
        company_name: str,
        corporate_name: Optional[str],
        contact_name: Optional[str],
        meeting_date: Optional[str],
    ) -> str:
        """ユーザープロンプトを構築"""
        context = f"""
【商談情報】
店舗名：{company_name}
法人名：{corporate_name or "不明（単一店舗経営の可能性）"}
接触者：{contact_name or "不明"}
日時：{meeting_date or "不明"}

【音声書き起こし】
{transcription}

【指示】
上記の商談内容から、6つのディスカッション項目への情報抽出を行い、
JSON フォーマットで返してください。
"""
        return context

    def _extract_json(self, response_text: str) -> dict:
        """レスポンステキストから JSON を抽出"""
        # JSON ブロック（```json ... ```）を探す
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        else:
            json_str = response_text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            raise

    def _build_discussion_record(
        self,
        structured_data: dict,
        company_name: str,
        corporate_name: Optional[str],
        contact_name: Optional[str],
        meeting_date: Optional[str],
    ) -> DiscussionRecord:
        """構造化データから DiscussionRecord を構築"""
        from datetime import datetime as dt

        # meeting_id を生成
        now = dt.now()
        meeting_id = f"{now.strftime('%Y%m%d_%H%M')}_{company_name.replace(' ', '_')}"

        # company_info を構築
        company_info = CompanyInfo(
            name=company_name,
            corporate_name=corporate_name,
            contact_name=contact_name or "不明",
            date=dt.fromisoformat(meeting_date) if meeting_date else now,
        )

        # discussions を構築
        discussions_data = structured_data.get("discussions", {})
        discussions = Discussions(**discussions_data)

        # priority_issues を構築
        priority_issues_data = structured_data.get("priority_issues", [])
        from schema.models import PriorityIssue

        priority_issues = [
            PriorityIssue(**item) for item in priority_issues_data
        ]

        # dx_solutions を構築
        dx_solutions_data = structured_data.get("dx_solutions", {})
        from schema.models import DXSolutions

        dx_solutions = DXSolutions(**dx_solutions_data)

        # next_steps を構築（空でもOK）
        from schema.models import NextSteps

        next_steps = NextSteps()

        # DiscussionRecord を構築
        record = DiscussionRecord(
            meeting_id=meeting_id,
            company_info=company_info,
            discussions=discussions,
            priority_issues=priority_issues,
            dx_solutions=dx_solutions,
            next_steps=next_steps,
            summary=structured_data.get("summary", ""),
            confidence_score=structured_data.get("confidence_score", 0.0),
        )

        return record


def get_text_analyzer() -> TextAnalyzer:
    """グローバルテキストアナライザを取得（シングルトン）"""
    if not hasattr(get_text_analyzer, "_instance"):
        get_text_analyzer._instance = TextAnalyzer()
    return get_text_analyzer._instance
