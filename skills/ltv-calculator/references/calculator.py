"""
LTV (주택담보대출비율) 계산기
2025.10.15 대책 및 가격대별 절대한도 반영

CLI usage:
    python calculator.py calculate --property-value 70000 --region-type 투기과열 --borrower-type 무주택
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from typing import Optional, List

from langchain_core.tools import tool

# LTV 한도율 (규제지역)
LTV_REGULATED = {
    "무주택": 0.40,
    "서민실수요": 0.70,   # 부부합산 연소득 9천만원 이하 무주택 세대주
    "생애최초": 0.70,
    "1주택처분": 0.50,
    "다주택": 0.0,
}

# LTV 한도율 (비규제지역)
LTV_UNREGULATED = {
    "무주택": 0.70,
    "서민실수요": 0.70,   # 비규제에서도 동일 (기본 70%와 같음)
    "생애최초": 0.80,
    "1주택처분": 0.70,
    "다주택": 0.60,
}

# 서민실수요자 기준 (부부합산 연소득, 만원)
SEOMIN_INCOME_THRESHOLD = 9000

# 9억 초과 고가주택 차등 (투기과열지구)
HIGH_VALUE_THRESHOLD = 90000  # 9억 (만원)
HIGH_VALUE_LTV_BELOW = 0.40
HIGH_VALUE_LTV_ABOVE = 0.20

# 가격대별 절대한도 (규제지역, 만원)
ABSOLUTE_LIMITS = [
    (150000, 60000),   # 15억 이하 → 6억
    (250000, 40000),   # 15~25억 → 4억
    (float("inf"), 20000),  # 25억 초과 → 2억
]

# 소액임차보증금 (만원)
SMALL_DEPOSIT = {
    "서울": 5500,
    "수도권과밀": 4800,
    "광역시": 2800,
    "기타": 2000,
}

# 규제지역 목록 (2025.10.15)
REGULATED_AREAS = {
    "서울": ["전 25개 자치구"],
    "경기": ["과천", "광명", "성남(분당)", "성남(수정)", "성남(중원)",
            "수원(영통)", "수원(장안)", "수원(팔달)", "안양(동안)",
            "용인(수지)", "의왕", "하남"],
}


def _get_ltv_rate(region_type: str, borrower_type: str) -> float:
    """LTV 한도율 조회"""
    if region_type in ("투기과열", "조정대상"):
        return LTV_REGULATED.get(borrower_type, 0.0)
    else:
        return LTV_UNREGULATED.get(borrower_type, 0.70)


def _high_value_ltv(property_value: float, borrower_type: str) -> float:
    """9억 초과 고가주택 차등 LTV 계산 (투기과열지구, 일반 무주택)"""
    if borrower_type != "무주택":
        # 생애최초 등은 차등 미적용
        rate = LTV_REGULATED.get(borrower_type, 0.0)
        return property_value * rate

    if property_value <= HIGH_VALUE_THRESHOLD:
        return property_value * HIGH_VALUE_LTV_BELOW
    else:
        below = HIGH_VALUE_THRESHOLD * HIGH_VALUE_LTV_BELOW
        above = (property_value - HIGH_VALUE_THRESHOLD) * HIGH_VALUE_LTV_ABOVE
        return below + above


def _absolute_limit(property_value: float) -> float:
    """가격대별 절대한도 (규제지역)"""
    for threshold, limit in ABSOLUTE_LIMITS:
        if property_value <= threshold:
            return limit
    return ABSOLUTE_LIMITS[-1][1]


@dataclass
class LTVResult:
    ltv_rate_pct: float         # 적용 LTV율 (%)
    ltv_limit: float            # LTV 기준 대출한도 (만원)
    absolute_limit: float       # 가격대별 절대한도 (만원, 0이면 미적용)
    final_limit: float          # 최종 대출한도 (만원)
    has_absolute_cap: bool      # 절대한도 적용 여부
    high_value_applied: bool    # 9억 초과 차등 적용 여부
    property_value: float       # 주택 감정가
    senior_liens: float         # 선순위채권
    small_deposit: float        # 소액임차보증금 공제
    details: str                # 산출 근거


def calculate_ltv_limit(
    property_value: float,
    region_type: str = "투기과열",
    borrower_type: str = "무주택",
    senior_liens: float = 0,
    deposit_region: str = "서울",
    has_tenant: bool = False,
) -> LTVResult:
    """
    LTV 기준 대출한도 계산

    Args:
        property_value: 주택 감정가액 (만원)
        region_type: 지역유형 (투기과열/조정대상/비규제)
        borrower_type: 차주유형 (무주택/생애최초/1주택처분/다주택)
        senior_liens: 선순위채권 잔액 (만원)
        deposit_region: 소액임차보증금 지역 (서울/수도권과밀/광역시/기타)
        has_tenant: 임차인 유무

    Returns:
        LTVResult
    """
    is_regulated = region_type in ("투기과열", "조정대상")
    ltv_rate = _get_ltv_rate(region_type, borrower_type)

    # 대출 불가 체크
    if ltv_rate == 0:
        return LTVResult(
            ltv_rate_pct=0, ltv_limit=0, absolute_limit=0,
            final_limit=0, has_absolute_cap=False, high_value_applied=False,
            property_value=property_value, senior_liens=senior_liens,
            small_deposit=0,
            details=f"{borrower_type}는 {region_type} 지역에서 대출 불가",
        )

    # 9억 초과 차등 (투기과열 + 일반 무주택만, 서민실수요·생애최초는 제외)
    high_value_applied = False
    if region_type == "투기과열" and borrower_type == "무주택" and property_value > HIGH_VALUE_THRESHOLD:
        ltv_amount = _high_value_ltv(property_value, borrower_type)
        high_value_applied = True
        details = f"9억 × 40% + {(property_value - HIGH_VALUE_THRESHOLD):,.0f}만 × 20%"
    else:
        ltv_amount = property_value * ltv_rate
        details = f"{property_value:,.0f}만 × {ltv_rate*100:.0f}%"

    # 소액임차보증금 공제
    deposit = SMALL_DEPOSIT.get(deposit_region, 2000) if has_tenant else 0

    # LTV 한도
    ltv_limit = ltv_amount - senior_liens - deposit
    ltv_limit = max(ltv_limit, 0)

    # 절대한도 (규제지역만)
    abs_limit = 0.0
    has_absolute_cap = False
    if is_regulated:
        abs_limit = _absolute_limit(property_value)
        if ltv_limit > abs_limit:
            has_absolute_cap = True

    final = min(ltv_limit, abs_limit) if is_regulated else ltv_limit

    return LTVResult(
        ltv_rate_pct=round(ltv_rate * 100, 1),
        ltv_limit=round(ltv_limit, 0),
        absolute_limit=round(abs_limit, 0) if is_regulated else 0,
        final_limit=round(final, 0),
        has_absolute_cap=has_absolute_cap,
        high_value_applied=high_value_applied,
        property_value=property_value,
        senior_liens=senior_liens,
        small_deposit=deposit,
        details=details,
    )


# ---------------------------------------------------------------------------
# LangChain Tool
# ---------------------------------------------------------------------------


@tool
def calculate_ltv(
    property_value: float,
    region_type: str = "투기과열",
    borrower_type: str = "무주택",
    senior_liens: float = 0,
    deposit_region: str = "서울",
    has_tenant: bool = False,
) -> str:
    """LTV(주택담보대출비율) 계산기. 담보가치 기준 최대 대출한도 산출. 9억 초과 차등 LTV, 가격대별 절대한도 반영.

    Args:
        property_value: 주택 감정가 (만원 단위). 예: 70000 = 7억원
        region_type: 지역유형. 투기과열/조정대상/비규제 중 택1
        borrower_type: 차주유형. 무주택/서민실수요/생애최초/1주택처분/다주택 중 택1
        senior_liens: 선순위채권 잔액 (만원). 기본 0
        deposit_region: 소액임차보증금 지역. 서울/수도권과밀/광역시/기타 중 택1
        has_tenant: 임차인 유무. 기본 false

    Returns:
        JSON 결과: ltv_rate_pct, ltv_limit, absolute_limit, final_limit, high_value_applied, has_absolute_cap 포함
    """
    result = calculate_ltv_limit(
        property_value=property_value,
        region_type=region_type,
        borrower_type=borrower_type,
        senior_liens=senior_liens,
        deposit_region=deposit_region,
        has_tenant=has_tenant,
    )
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


def get_tools():
    """이 스킬의 LangChain 도구 목록"""
    return [calculate_ltv]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calculator.py",
        description="LTV (주택담보대출비율) 계산기 CLI",
    )
    sub = parser.add_subparsers(dest="command")

    calc = sub.add_parser("calculate", help="LTV 대출한도 계산")
    calc.add_argument(
        "--property-value",
        type=float,
        required=True,
        help="주택 감정가액 (만원)",
    )
    calc.add_argument(
        "--region-type",
        type=str,
        default="투기과열",
        choices=["투기과열", "조정대상", "비규제"],
        help="지역유형 (default: 투기과열)",
    )
    calc.add_argument(
        "--borrower-type",
        type=str,
        default="무주택",
        choices=["무주택", "서민실수요", "생애최초", "1주택처분", "다주택"],
        help="차주유형 (default: 무주택). 서민실수요=부부합산 연소득 9천만 이하 무주택 세대주",
    )
    calc.add_argument(
        "--senior-liens",
        type=float,
        default=0,
        help="선순위채권 잔액, 만원 (default: 0)",
    )
    calc.add_argument(
        "--deposit-region",
        type=str,
        default="서울",
        choices=["서울", "수도권과밀", "광역시", "기타"],
        help="소액임차보증금 지역 (default: 서울)",
    )
    calc.add_argument(
        "--has-tenant",
        action="store_true",
        default=False,
        help="임차인 유무 (default: false)",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "calculate":
        result = calculate_ltv_limit(
            property_value=args.property_value,
            region_type=args.region_type,
            borrower_type=args.borrower_type,
            senior_liens=args.senior_liens,
            deposit_region=args.deposit_region,
            has_tenant=args.has_tenant,
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
