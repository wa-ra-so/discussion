from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


# Enums
class ReservationMethod(str, Enum):
    PAPER_LEDGER = "paper_ledger"
    ONLINE_POS = "online_pos"
    GOOGLE_CALENDAR = "google_calendar"
    OTHER = "other"


class ReservationChannel(str, Enum):
    TABELOG = "tabelog"
    HOT_PEPPER = "hot_pepper"
    GURUNAVI = "gurunavi"
    IKYU = "ikyu"
    RETTY = "retty"
    SNS = "sns"
    GOOGLE = "google"
    HOMEPAGE = "homepage"
    OTHER = "other"


class PhoneFrequency(str, Enum):
    FREQUENT = "frequent"
    OCCASIONAL = "occasional"
    SOMETIMES_MISSED = "sometimes_missed"


class DoublebookingIssue(str, Enum):
    PAST_OCCURRENCE = "past_occurrence"
    NO_OCCURRENCE_BUT_WORRIED = "no_occurrence_but_worried"
    RULES_IN_PLACE = "rules_in_place"


class OrderingMethod(str, Enum):
    VERBAL = "verbal"
    MOBILE_ORDER = "mobile_order"
    TABLE_TABLET = "table_tablet"
    TICKET_MACHINE = "ticket_machine"
    PRE_PAYMENT = "pre_payment"
    OTHER = "other"


class OrderingChannel(str, Enum):
    FAX = "fax"
    PHONE = "phone"
    LINE_EMAIL = "line_email"
    VENDOR_WEB = "vendor_web"
    UNIFIED_SYSTEM = "unified_system"
    OTHER = "other"


class OrderingResponsible(str, Enum):
    OWNER_MANAGER = "owner_manager"
    CHEF = "chef"
    SPECIFIC_STAFF = "specific_staff"
    ANYONE = "anyone"


class MultilingualSupport(str, Enum):
    FULLY_SUPPORTED = "fully_supported"
    NO_MENU_TRANSLATION = "no_menu_translation"
    PAYMENT_ISSUES = "payment_issues"
    NO_MEASURES = "no_measures"


class PriorityCategory(str, Enum):
    MARKETING = "marketing"
    RESERVATION_EFFICIENCY = "reservation_efficiency"
    COST_REDUCTION = "cost_reduction"
    RECRUITMENT = "recruitment"
    INBOUND = "inbound"


# Company Info
class CompanyInfo(BaseModel):
    name: str = Field(..., description="店舗名")
    contact_name: str = Field(..., description="接触者氏名")
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    date: datetime = Field(..., description="商談日時")


# Recruitment Section
class StaffComposition(BaseModel):
    employees: Optional[int] = None
    part_time: Optional[int] = None


class PastRecruitment(BaseModel):
    methods: Optional[List[str]] = None
    cost_per_hire: Optional[float] = None


class RecruitmentSection(BaseModel):
    assumed_issues: Optional[str] = None
    current_staff: Optional[StaffComposition] = None
    ideal_staff: Optional[StaffComposition] = None
    operation_structure: Optional[dict] = None
    past_recruitment: Optional[PastRecruitment] = None
    recruitment_budget: Optional[float] = None
    desired_talent: Optional[str] = None
    hiring_timeline: Optional[str] = None
    current_initiatives: Optional[str] = None


# Sales Section
class AverageSpend(BaseModel):
    lunch: Optional[float] = None
    dinner: Optional[float] = None


class SeatUtilization(BaseModel):
    weekday: Optional[float] = None
    weekend: Optional[float] = None


class TurnoverRate(BaseModel):
    weekday: Optional[str] = None
    weekend: Optional[str] = None


class SalesSection(BaseModel):
    assumed_issues: Optional[str] = None
    average_customer_spend: Optional[AverageSpend] = None
    seat_utilization: Optional[SeatUtilization] = None
    turnover_rate: Optional[TurnoverRate] = None
    fl_ratio: Optional[float] = None
    customer_segment: Optional[str] = None
    usage_scenes: Optional[str] = None
    other_media_roi: Optional[str] = None
    current_initiatives: Optional[str] = None
    pos_system: Optional[str] = None


# Booking & Efficiency Section
class SiteController(BaseModel):
    in_use: bool
    details: Optional[str] = None


class PhoneResponse(BaseModel):
    frequency: Optional[PhoneFrequency] = None
    daily_calls: Optional[int] = None


class BookingEfficiencySection(BaseModel):
    assumed_issues: Optional[str] = None
    current_reservation_method: Optional[List[ReservationMethod]] = None
    net_reservation_status: Optional[bool] = None
    site_controller_usage: Optional[SiteController] = None
    reservation_channels: Optional[List[ReservationChannel]] = None
    phone_response: Optional[PhoneResponse] = None
    double_booking_issues: Optional[DoublebookingIssue] = None
    ordering_method: Optional[List[OrderingMethod]] = None
    pos_system: Optional[str] = None
    current_ordering_method: Optional[List[OrderingChannel]] = None
    daily_ordering_time: Optional[float] = None
    ordering_timing: Optional[List[str]] = None
    ordering_responsible: Optional[OrderingResponsible] = None


# Inbound Section
class InboundSection(BaseModel):
    assumed_issues: Optional[str] = None
    monthly_foreign_guests: Optional[int] = None
    multilingual_support: Optional[MultilingualSupport] = None


# Discussions (all sections combined)
class Discussions(BaseModel):
    recruitment: Optional[RecruitmentSection] = None
    sales: Optional[SalesSection] = None
    booking_efficiency: Optional[BookingEfficiencySection] = None
    inbound: Optional[InboundSection] = None


# Priority Issue
class PriorityIssue(BaseModel):
    category: PriorityCategory
    issue: str
    priority: Optional[int] = Field(None, ge=1, le=5)


# DX Solutions
class DXSolutions(BaseModel):
    revenue_maximization: Optional[List[str]] = None
    efficiency_cost_reduction: Optional[List[str]] = None
    recruitment_market_development: Optional[List[str]] = None


# Next Steps
class NextSteps(BaseModel):
    store_actions: Optional[List[str]] = None
    store_deadline: Optional[str] = None
    tabelog_actions: Optional[List[str]] = None
    tabelog_deadline: Optional[str] = None


# Main Discussion Record
class DiscussionRecord(BaseModel):
    meeting_id: str
    company_info: CompanyInfo
    discussions: Discussions
    priority_issues: List[PriorityIssue]
    dx_solutions: DXSolutions
    next_steps: NextSteps
    summary: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None

    class Config:
        use_enum_values = False
        json_schema_extra = {
            "example": {
                "meeting_id": "20240131_1400_example_restaurant",
                "company_info": {
                    "name": "Example Restaurant",
                    "contact_name": "山田太郎",
                    "contact_email": "yamada@example.com",
                    "date": "2024-01-31T14:00:00"
                },
                "discussions": {
                    "recruitment": {
                        "assumed_issues": "人手不足で営業時間短縮を余儀なくされている",
                        "current_staff": {"employees": 1, "part_time": 2},
                        "ideal_staff": {"employees": 2, "part_time": 3}
                    }
                },
                "priority_issues": [
                    {
                        "category": "recruitment",
                        "issue": "求人を出しても応募が全く来ない",
                        "priority": 5
                    }
                ],
                "dx_solutions": {},
                "next_steps": {},
                "confidence_score": 0.85
            }
        }
