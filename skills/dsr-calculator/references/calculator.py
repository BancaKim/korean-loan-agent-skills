"""
DSR (총부채원리금상환비율) 계산기
금감원 DSR 산정기준 반영 - 스트레스 가산금리 3단계 (2025.7.1~)

CLI Usage:
    python calculator.py calculate --annual-income 5000 --loan-amount 30000 \
        --loan-rate 4.5 --loan-months 360 --rate-type 변동 --region 수도권

    python calculator.py max-loan --annual-income 5000 --loan-rate 4.5 \
        --loan-months 360 --rate-type 변동 --region 수도권

    python calculator.py calculate --annual-income 5000 --loan-amount 30000 \
        --loan-rate 4.5 --loan-months 360 --rate-type 변동 --region 수도권 \
        --existing-loans '[{"balance":5000,"rate":5.0,"remaining_months":48,"method":"원리금균등","loan_type":"신용대출","rate_type":"변동"}]'
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

from langchain_core.tools import tool

# DSR 한도
DSR_LIMITS = {
    "은행": 0.40,
    "2금융": 0.50,
}

# 스트레스 기본 가산금리 (%p)
STRESS_BASE = {
    "수도권": 3.0,
    "규제지역": 3.0,
    "지방": 0.75,
}

STRESS_CREDIT_LOAN = 1.5  # 신용대출 (1억 초과) 가산

# 금리유형별 스트레스 적용비율
STRESS_RATIO = {
    "변동": 1.0,        # 5년 미만
    "혼합5년": 0.80,    # 고정 5~9년
    "혼합10년": 0.60,   # 고정 9~15년
    "혼합15년": 0.40,   # 고정 15~21년
    "고정": 0.0,        # 순수 고정
}

# 만기일시상환 산정만기 상한 (개월)
BULLET_MATURITY_CAP = {
    "주택담보대출": 120,    # 10년
    "신용대출": 60,         # 5년
    "마이너스통장": 120,    # 10년
    "한도대출": 120,        # 10년
    "오피스텔담보": 96,     # 8년
    "전세보증금담보": 48,   # 4년
    "카드론": 36,           # 3년
}


@dataclass
class ExistingLoan:
    """기존 대출"""
    balance: float         # 잔액 (만원)
    rate: float            # 약정 연이자율 (%)
    remaining_months: int  # 잔여개월
    method: str            # 상환방식 (원리금균등/원금균등/만기일시)
    loan_type: str = "주택담보대출"  # 대출유형
    rate_type: str = "변동"          # 금리유형


def _annual_payment_equal_pi(principal: float, annual_rate: float, months: int) -> float:
    """원리금균등 연간 상환액"""
    if annual_rate == 0:
        return (principal / months) * 12 if months > 0 else 0
    r = annual_rate / 100 / 12
    monthly = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)
    return monthly * 12


def _annual_payment_equal_p(principal: float, annual_rate: float, months: int) -> float:
    """원금균등 첫해 12개월 합산"""
    if months == 0:
        return 0
    r = annual_rate / 100 / 12
    monthly_principal = principal / months
    total = 0.0
    remaining = principal
    for _ in range(min(12, months)):
        interest = remaining * r
        total += monthly_principal + interest
        remaining -= monthly_principal
    return total


def _dsr_annual_payment(principal: float, rate: float, months: int, method: str,
                        loan_type: str = "주택담보대출") -> float:
    """DSR 산정용 연간 상환액 (만기일시는 원리금균등 전환)"""
    if method == "원리금균등":
        return _annual_payment_equal_pi(principal, rate, months)
    elif method == "원금균등":
        return _annual_payment_equal_p(principal, rate, months)
    elif method == "만기일시":
        # 원리금균등 전환(의제), 산정만기 상한 적용
        cap = BULLET_MATURITY_CAP.get(loan_type, 120)
        effective_months = min(months, cap) if months > 0 else cap
        return _annual_payment_equal_pi(principal, rate, effective_months)
    else:
        raise ValueError(f"알 수 없는 상환방식: {method}")


def _stress_rate(base_rate: float, rate_type: str, region: str) -> float:
    """스트레스 가산금리 적용한 DSR 산정금리"""
    stress_base = STRESS_BASE.get(region, 3.0)
    ratio = STRESS_RATIO.get(rate_type, 1.0)
    return base_rate + stress_base * ratio


def _reverse_max_loan_equal_pi(annual_payment: float, annual_rate: float, months: int) -> float:
    """원리금균등 최대 대출액 역산"""
    if annual_rate == 0:
        return annual_payment / 12 * months if months > 0 else 0
    r = annual_rate / 100 / 12
    monthly = annual_payment / 12
    return monthly * ((1 + r) ** months - 1) / (r * (1 + r) ** months)


@dataclass
class DSRResult:
    dsr_pct: float             # DSR (%)
    dsr_limit_pct: float       # DSR 한도 (%)
    is_pass: bool              # 통과 여부
    stress_rate: float         # 스트레스 적용 금리 (%)
    new_loan_annual: float     # 신규 대출 연상환액
    existing_loans_annual: float  # 기존 대출 연상환액
    total_annual: float        # 전체 연상환액
    annual_income: float       # 연소득


def calculate_dsr(
    annual_income: float,
    new_loan_amount: float,
    new_loan_rate: float,
    new_loan_months: int,
    new_loan_method: str = "원리금균등",
    new_loan_rate_type: str = "변동",
    region: str = "수도권",
    sector: str = "은행",
    existing_loans: list[ExistingLoan] | None = None,
) -> DSRResult:
    """
    DSR 계산

    Args:
        annual_income: 연소득 (만원)
        new_loan_amount: 신규 대출 원금 (만원)
        new_loan_rate: 약정 연이자율 (%)
        new_loan_months: 상환기간 (개월)
        new_loan_method: 상환방식
        new_loan_rate_type: 금리유형 (변동/혼합5년/혼합10년/고정)
        region: 지역 (수도권/지방/규제지역)
        sector: 금융권 (은행/2금융)
        existing_loans: 기존 대출 목록

    Returns:
        DSRResult
    """
    existing_loans = existing_loans or []

    # 신규대출: 스트레스 가산금리 적용
    effective_rate = _stress_rate(new_loan_rate, new_loan_rate_type, region)
    new_annual = _dsr_annual_payment(
        new_loan_amount, effective_rate, new_loan_months, new_loan_method, "주택담보대출"
    )

    # 기존대출: 약정금리 기준 (스트레스 소급 미적용)
    existing_annual = sum(
        _dsr_annual_payment(loan.balance, loan.rate, loan.remaining_months, loan.method, loan.loan_type)
        for loan in existing_loans
    )

    total = new_annual + existing_annual
    dsr = total / annual_income * 100

    limit = DSR_LIMITS.get(sector, 0.40) * 100

    return DSRResult(
        dsr_pct=round(dsr, 2),
        dsr_limit_pct=limit,
        is_pass=dsr <= limit,
        stress_rate=round(effective_rate, 2),
        new_loan_annual=round(new_annual, 1),
        existing_loans_annual=round(existing_annual, 1),
        total_annual=round(total, 1),
        annual_income=annual_income,
    )


@dataclass
class MaxLoanByDSRResult:
    max_loan: float           # 최대 대출 가능액 (만원)
    dsr_limit_pct: float      # DSR 한도
    stress_rate: float        # 적용 금리
    allowed_annual: float     # 허용 연상환액
    available_annual: float   # 신규대출 허용 연상환액
    by_method: dict | None = None   # 상환방식별 비교
    by_period: dict | None = None   # 기간별 비교
    by_rate_type: dict | None = None  # 금리유형별 비교


def calculate_max_mortgage_by_dsr(
    annual_income: float,
    loan_rate: float,
    loan_months: int,
    loan_method: str = "원리금균등",
    rate_type: str = "변동",
    region: str = "수도권",
    sector: str = "은행",
    existing_loans: list[ExistingLoan] | None = None,
) -> MaxLoanByDSRResult:
    """
    DSR 한도 내 최대 대출 가능액 역산

    Returns:
        MaxLoanByDSRResult (상환방식별/기간별/금리유형별 비교 포함)
    """
    existing_loans = existing_loans or []

    limit_rate = DSR_LIMITS.get(sector, 0.40)
    allowed_annual = annual_income * limit_rate

    existing_annual = sum(
        _dsr_annual_payment(loan.balance, loan.rate, loan.remaining_months, loan.method, loan.loan_type)
        for loan in existing_loans
    )

    available = allowed_annual - existing_annual
    if available <= 0:
        return MaxLoanByDSRResult(
            max_loan=0, dsr_limit_pct=limit_rate * 100,
            stress_rate=0, allowed_annual=round(allowed_annual, 1),
            available_annual=0,
        )

    effective_rate = _stress_rate(loan_rate, rate_type, region)

    # 주요 역산
    def _calc_max(method: str, rate: float, months: int) -> float:
        if method == "원리금균등":
            return _reverse_max_loan_equal_pi(available, rate, months)
        elif method == "만기일시":
            cap = BULLET_MATURITY_CAP["주택담보대출"]
            eff_months = min(months, cap)
            return _reverse_max_loan_equal_pi(available, rate, eff_months)
        else:  # 원금균등 - 이진탐색
            lo, hi = 0.0, annual_income * 200
            for _ in range(100):
                mid = (lo + hi) / 2
                annual = _annual_payment_equal_p(mid, rate, months)
                if annual <= available:
                    lo = mid
                else:
                    hi = mid
            return lo

    max_loan = _calc_max(loan_method, effective_rate, loan_months)

    # 상환방식별 비교
    by_method = {}
    for m in ["원리금균등", "원금균등", "만기일시"]:
        by_method[m] = round(_calc_max(m, effective_rate, loan_months), 0)

    # 기간별 비교 (10~40년)
    by_period = {}
    for years in [10, 15, 20, 25, 30, 35, 40]:
        months = years * 12
        by_period[f"{years}년"] = round(_calc_max(loan_method, effective_rate, months), 0)

    # 금리유형별 비교
    by_rate_type = {}
    for rt in ["변동", "혼합5년", "혼합10년", "고정"]:
        eff = _stress_rate(loan_rate, rt, region)
        by_rate_type[f"{rt}({eff:.1f}%)"] = round(_calc_max(loan_method, eff, loan_months), 0)

    return MaxLoanByDSRResult(
        max_loan=round(max_loan, 0),
        dsr_limit_pct=limit_rate * 100,
        stress_rate=round(effective_rate, 2),
        allowed_annual=round(allowed_annual, 1),
        available_annual=round(available, 1),
        by_method=by_method,
        by_period=by_period,
        by_rate_type=by_rate_type,
    )


# ---------------------------------------------------------------------------
# LangChain Tools
# ---------------------------------------------------------------------------


def _parse_loans_json(raw: str | None) -> list[ExistingLoan]:
    """JSON 문자열을 ExistingLoan 리스트로 변환"""
    if not raw:
        return []
    items = json.loads(raw)
    if not isinstance(items, list):
        items = [items]
    return [
        ExistingLoan(
            balance=item["balance"],
            rate=item["rate"],
            remaining_months=item["remaining_months"],
            method=item["method"],
            loan_type=item.get("loan_type", "주택담보대출"),
            rate_type=item.get("rate_type", "변동"),
        )
        for item in items
    ]


@tool
def calculate_dsr_tool(
    annual_income: float,
    loan_amount: float,
    loan_rate: float,
    loan_months: int,
    loan_method: str = "원리금균등",
    rate_type: str = "변동",
    region: str = "수도권",
    sector: str = "은행",
    existing_loans: Optional[str] = None,
) -> str:
    """DSR(총부채원리금상환비율) 계산기. 스트레스 가산금리 3단계(2025.7.1~) 반영.

    Args:
        annual_income: 연소득 (만원). 예: 5000 = 5천만원
        loan_amount: 신규 대출 원금 (만원). 예: 30000 = 3억원
        loan_rate: 약정 연이자율 (%). 예: 4.5
        loan_months: 상환기간 (개월). 예: 360 = 30년
        loan_method: 상환방식. 원리금균등/원금균등/만기일시 중 택1
        rate_type: 금리유형. 변동/혼합5년/혼합10년/고정 중 택1. 변동은 스트레스 +3.0%p, 고정은 0%
        region: 지역. 수도권/규제지역/지방 중 택1
        sector: 금융권. 은행(DSR 40%)/2금융(DSR 50%) 중 택1
        existing_loans: 기존 대출 JSON. 예: '[{"balance":5000,"rate":5.0,"remaining_months":48,"method":"원리금균등","loan_type":"신용대출","rate_type":"변동"}]'

    Returns:
        JSON 결과: dsr_pct, dsr_limit_pct, is_pass, stress_rate 포함
    """
    result = calculate_dsr(
        annual_income=annual_income,
        new_loan_amount=loan_amount,
        new_loan_rate=loan_rate,
        new_loan_months=loan_months,
        new_loan_method=loan_method,
        new_loan_rate_type=rate_type,
        region=region,
        sector=sector,
        existing_loans=_parse_loans_json(existing_loans),
    )
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


@tool
def calculate_dsr_max_loan(
    annual_income: float,
    loan_rate: float,
    loan_months: int,
    loan_method: str = "원리금균등",
    rate_type: str = "변동",
    region: str = "수도권",
    sector: str = "은행",
    existing_loans: Optional[str] = None,
) -> str:
    """DSR 한도 내 최대 대출 가능액 역산. 상환방식별/기간별/금리유형별 비교표 제공.

    Args:
        annual_income: 연소득 (만원). 예: 5000 = 5천만원
        loan_rate: 약정 연이자율 (%). 예: 4.5
        loan_months: 상환기간 (개월). 예: 360 = 30년
        loan_method: 상환방식. 원리금균등/원금균등/만기일시 중 택1
        rate_type: 금리유형. 변동/혼합5년/혼합10년/고정 중 택1
        region: 지역. 수도권/규제지역/지방 중 택1
        sector: 금융권. 은행(DSR 40%)/2금융(DSR 50%) 중 택1
        existing_loans: 기존 대출 JSON 문자열 (선택)

    Returns:
        JSON 결과: max_loan, by_method(상환방식별), by_period(기간별), by_rate_type(금리유형별) 비교 포함
    """
    result = calculate_max_mortgage_by_dsr(
        annual_income=annual_income,
        loan_rate=loan_rate,
        loan_months=loan_months,
        loan_method=loan_method,
        rate_type=rate_type,
        region=region,
        sector=sector,
        existing_loans=_parse_loans_json(existing_loans),
    )
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


def get_tools():
    """이 스킬의 LangChain 도구 목록"""
    return [calculate_dsr_tool, calculate_dsr_max_loan]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_existing_loans(raw: str | None) -> list[ExistingLoan]:
    """Parse --existing-loans JSON string into a list of ExistingLoan."""
    if not raw:
        return []
    items = json.loads(raw)
    if not isinstance(items, list):
        items = [items]
    return [
        ExistingLoan(
            balance=item["balance"],
            rate=item["rate"],
            remaining_months=item["remaining_months"],
            method=item["method"],
            loan_type=item.get("loan_type", "주택담보대출"),
            rate_type=item.get("rate_type", "변동"),
        )
        for item in items
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="DSR (총부채원리금상환비율) 계산기 CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- calculate --------------------------------------------------------
    calc = subparsers.add_parser("calculate", help="DSR 계산")
    calc.add_argument("--annual-income", type=float, required=True,
                      help="연소득 (만원)")
    calc.add_argument("--loan-amount", type=float, required=True,
                      help="신규 대출 원금 (만원)")
    calc.add_argument("--loan-rate", type=float, required=True,
                      help="약정 연이자율 (%%)")
    calc.add_argument("--loan-months", type=int, required=True,
                      help="상환기간 (개월)")
    calc.add_argument("--loan-method", type=str, default="원리금균등",
                      choices=["원리금균등", "원금균등", "만기일시"],
                      help="상환방식 (default: 원리금균등)")
    calc.add_argument("--rate-type", type=str, default="변동",
                      choices=list(STRESS_RATIO.keys()),
                      help="금리유형 (default: 변동)")
    calc.add_argument("--region", type=str, default="수도권",
                      choices=["수도권", "규제지역", "지방"],
                      help="지역 (default: 수도권)")
    calc.add_argument("--sector", type=str, default="은행",
                      choices=["은행", "2금융"],
                      help="금융권 (default: 은행)")
    calc.add_argument("--existing-loans", type=str, default=None,
                      help="기존 대출 JSON 문자열")

    # ---- max-loan ---------------------------------------------------------
    ml = subparsers.add_parser("max-loan", help="DSR 한도 내 최대 대출 가능액 역산")
    ml.add_argument("--annual-income", type=float, required=True,
                    help="연소득 (만원)")
    ml.add_argument("--loan-rate", type=float, required=True,
                    help="약정 연이자율 (%%)")
    ml.add_argument("--loan-months", type=int, required=True,
                    help="상환기간 (개월)")
    ml.add_argument("--loan-method", type=str, default="원리금균등",
                    choices=["원리금균등", "원금균등", "만기일시"],
                    help="상환방식 (default: 원리금균등)")
    ml.add_argument("--rate-type", type=str, default="변동",
                    choices=list(STRESS_RATIO.keys()),
                    help="금리유형 (default: 변동)")
    ml.add_argument("--region", type=str, default="수도권",
                    choices=["수도권", "규제지역", "지방"],
                    help="지역 (default: 수도권)")
    ml.add_argument("--sector", type=str, default="은행",
                    choices=["은행", "2금융"],
                    help="금융권 (default: 은행)")
    ml.add_argument("--existing-loans", type=str, default=None,
                    help="기존 대출 JSON 문자열")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    existing = _parse_existing_loans(args.existing_loans)

    if args.command == "calculate":
        result = calculate_dsr(
            annual_income=args.annual_income,
            new_loan_amount=args.loan_amount,
            new_loan_rate=args.loan_rate,
            new_loan_months=args.loan_months,
            new_loan_method=args.loan_method,
            new_loan_rate_type=args.rate_type,
            region=args.region,
            sector=args.sector,
            existing_loans=existing,
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))

    elif args.command == "max-loan":
        result = calculate_max_mortgage_by_dsr(
            annual_income=args.annual_income,
            loan_rate=args.loan_rate,
            loan_months=args.loan_months,
            loan_method=args.loan_method,
            rate_type=args.rate_type,
            region=args.region,
            sector=args.sector,
            existing_loans=existing,
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
