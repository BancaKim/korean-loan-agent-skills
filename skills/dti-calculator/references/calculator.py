#!/usr/bin/env python3
"""
DTI (총부채상환비율) 계산기
신DTI 산정기준 반영 - 주택담보대출 심사용

Usage:
    python calculator.py calculate --annual-income 5000 --loan-amount 30000 --loan-rate 4.5 --loan-months 360
    python calculator.py max-loan --annual-income 5000 --loan-rate 4.5 --loan-months 360
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional, List

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Constants - 한국 부동산 규제 상수
# ---------------------------------------------------------------------------

# DTI 한도율
DTI_LIMITS = {
    "투기과열": 0.40,
    "조정대상": 0.50,
    "비규제": 0.60,
}

# 서민·실수요자 (연소득 7천만원 이하 무주택자) → 지역 불문 60%
SEOMIN_DTI_LIMIT = 0.60
SEOMIN_INCOME_THRESHOLD = 7000  # 만원

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Mortgage:
    """기존 주담대"""
    balance: float       # 잔액 (만원)
    rate: float          # 연이자율 (%)
    remaining_months: int  # 잔여개월
    method: str = "원리금균등"  # 원리금균등/원금균등/만기일시


@dataclass
class OtherLoan:
    """기타대출 (신용대출, 카드론 등) - DTI에서는 이자만 반영"""
    balance: float  # 잔액 (만원)
    rate: float     # 연이자율 (%)


# ---------------------------------------------------------------------------
# Internal calculation helpers
# ---------------------------------------------------------------------------


def _annual_payment_equal_principal_interest(principal: float, annual_rate: float, months: int) -> float:
    """원리금균등 연간 상환액"""
    if annual_rate == 0:
        return (principal / months) * 12
    r = annual_rate / 100 / 12
    monthly = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)
    return monthly * 12


def _annual_payment_equal_principal(principal: float, annual_rate: float, months: int) -> float:
    """원금균등 첫해 12개월 합산 (최대 상환액 기준)"""
    r = annual_rate / 100 / 12
    monthly_principal = principal / months
    total = 0.0
    remaining = principal
    for i in range(min(12, months)):
        interest = remaining * r
        total += monthly_principal + interest
        remaining -= monthly_principal
    return total


def _annual_payment_bullet(principal: float, annual_rate: float) -> float:
    """만기일시 연이자 (원금은 만기 상환)"""
    return principal * annual_rate / 100


def _annual_repayment(principal: float, rate: float, months: int, method: str) -> float:
    """상환방식별 연간 상환액"""
    if method == "원리금균등":
        return _annual_payment_equal_principal_interest(principal, rate, months)
    elif method == "원금균등":
        return _annual_payment_equal_principal(principal, rate, months)
    elif method == "만기일시":
        return _annual_payment_bullet(principal, rate)
    else:
        raise ValueError(f"알 수 없는 상환방식: {method}")


def _reverse_max_loan_equal_pi(annual_payment: float, annual_rate: float, months: int) -> float:
    """원리금균등 최대 대출액 역산"""
    if annual_rate == 0:
        return annual_payment / 12 * months
    r = annual_rate / 100 / 12
    monthly_payment = annual_payment / 12
    return monthly_payment * ((1 + r) ** months - 1) / (r * (1 + r) ** months)


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------


@dataclass
class DTIResult:
    dti_pct: float                 # DTI (%)
    dti_limit_pct: float           # 적용 DTI 한도 (%)
    is_pass: bool                  # 통과 여부
    new_mortgage_annual: float     # 신규 주담대 연상환액
    existing_mortgage_annual: float  # 기존 주담대 연상환액
    other_loan_interest_annual: float  # 기타대출 연이자
    total_annual: float            # 분자 합계
    annual_income: float           # 연소득


@dataclass
class MaxLoanByDTIResult:
    max_loan: float          # 최대 대출 가능액 (만원)
    dti_limit_pct: float     # 적용 DTI 한도
    allowed_annual: float    # 허용 연상환액
    available_annual: float  # 신규대출 허용 연상환액


# ---------------------------------------------------------------------------
# Core calculation functions
# ---------------------------------------------------------------------------


def calculate_dti(
    annual_income: float,
    new_loan_amount: float,
    new_loan_rate: float,
    new_loan_months: int,
    new_loan_method: str = "원리금균등",
    region: str = "투기과열",
    existing_mortgages: list[Mortgage] | None = None,
    other_loans: list[OtherLoan] | None = None,
    is_seomin: bool = False,
) -> DTIResult:
    """
    DTI 계산

    Args:
        annual_income: 연소득 (만원)
        new_loan_amount: 신규 주담대 원금 (만원)
        new_loan_rate: 약정 연이자율 (%)
        new_loan_months: 상환기간 (개월)
        new_loan_method: 상환방식
        region: 지역 (투기과열/조정대상/비규제)
        existing_mortgages: 기존 주담대 목록
        other_loans: 기타대출 목록 (이자만 DTI 반영)
        is_seomin: 서민·실수요자 여부 (연소득 7천만 이하 무주택)

    Returns:
        DTIResult
    """
    existing_mortgages = existing_mortgages or []
    other_loans = other_loans or []

    # A: 신규 주담대 연간 원리금
    new_annual = _annual_repayment(new_loan_amount, new_loan_rate, new_loan_months, new_loan_method)

    # B: 기존 주담대 연간 원리금
    existing_annual = sum(
        _annual_repayment(m.balance, m.rate, m.remaining_months, m.method)
        for m in existing_mortgages
    )

    # C: 기타대출 연간 이자만 (DTI의 핵심 차이)
    other_interest = sum(
        loan.balance * loan.rate / 100
        for loan in other_loans
    )

    total = new_annual + existing_annual + other_interest
    dti = total / annual_income * 100

    # DTI 한도
    if is_seomin or annual_income <= SEOMIN_INCOME_THRESHOLD:
        limit = SEOMIN_DTI_LIMIT * 100
    else:
        limit = DTI_LIMITS.get(region, 0.60) * 100

    return DTIResult(
        dti_pct=round(dti, 2),
        dti_limit_pct=limit,
        is_pass=dti <= limit,
        new_mortgage_annual=round(new_annual, 1),
        existing_mortgage_annual=round(existing_annual, 1),
        other_loan_interest_annual=round(other_interest, 1),
        total_annual=round(total, 1),
        annual_income=annual_income,
    )


def calculate_max_loan_by_dti(
    annual_income: float,
    loan_rate: float,
    loan_months: int,
    loan_method: str = "원리금균등",
    region: str = "투기과열",
    existing_mortgages: list[Mortgage] | None = None,
    other_loans: list[OtherLoan] | None = None,
    is_seomin: bool = False,
) -> MaxLoanByDTIResult:
    """
    DTI 기준 최대 대출 가능액 역산

    Returns:
        MaxLoanByDTIResult
    """
    existing_mortgages = existing_mortgages or []
    other_loans = other_loans or []

    # DTI 한도
    if is_seomin or annual_income <= SEOMIN_INCOME_THRESHOLD:
        limit_rate = SEOMIN_DTI_LIMIT
    else:
        limit_rate = DTI_LIMITS.get(region, 0.60)

    allowed_annual = annual_income * limit_rate

    existing_annual = sum(
        _annual_repayment(m.balance, m.rate, m.remaining_months, m.method)
        for m in existing_mortgages
    )
    other_interest = sum(
        loan.balance * loan.rate / 100
        for loan in other_loans
    )

    available = allowed_annual - existing_annual - other_interest
    if available <= 0:
        return MaxLoanByDTIResult(
            max_loan=0,
            dti_limit_pct=limit_rate * 100,
            allowed_annual=round(allowed_annual, 1),
            available_annual=0,
        )

    # 역산
    if loan_method == "원리금균등":
        max_loan = _reverse_max_loan_equal_pi(available, loan_rate, loan_months)
    elif loan_method == "만기일시":
        # 연이자 = P × r → P = available / r
        max_loan = available / (loan_rate / 100) if loan_rate > 0 else 0
    else:
        # 원금균등: 이진탐색
        lo, hi = 0.0, annual_income * 100
        for _ in range(100):
            mid = (lo + hi) / 2
            annual = _annual_payment_equal_principal(mid, loan_rate, loan_months)
            if annual <= available:
                lo = mid
            else:
                hi = mid
        max_loan = lo

    return MaxLoanByDTIResult(
        max_loan=round(max_loan, 0),
        dti_limit_pct=limit_rate * 100,
        allowed_annual=round(allowed_annual, 1),
        available_annual=round(available, 1),
    )


# ---------------------------------------------------------------------------
# LangChain Tools
# ---------------------------------------------------------------------------


@tool
def calculate_dti_tool(
    annual_income: float,
    loan_amount: float,
    loan_rate: float,
    loan_months: int,
    loan_method: str = "원리금균등",
    region: str = "투기과열",
    existing_mortgages: Optional[str] = None,
    other_loans: Optional[str] = None,
) -> str:
    """DTI(총부채상환비율) 계산기. 기타대출은 이자만 반영 (DSR과의 핵심 차이).

    Args:
        annual_income: 연소득 (만원). 예: 5000 = 5천만원
        loan_amount: 신규 주담대 원금 (만원). 예: 30000 = 3억원
        loan_rate: 약정 연이자율 (%). 예: 4.5
        loan_months: 상환기간 (개월). 예: 360 = 30년
        loan_method: 상환방식. 원리금균등/원금균등/만기일시 중 택1
        region: 지역. 투기과열(DTI 40%)/조정대상(50%)/비규제(60%) 중 택1
        existing_mortgages: 기존 주담대 JSON. 예: '[{"balance":10000,"rate":3.5,"remaining_months":240,"method":"원리금균등"}]'
        other_loans: 기타대출 JSON. 예: '[{"balance":5000,"rate":5.0}]' (DTI에서는 이자만 반영)

    Returns:
        JSON 결과: dti_pct, dti_limit_pct, is_pass, other_loan_interest_annual 포함
    """
    em = _parse_mortgages(existing_mortgages)
    ol = _parse_other_loans(other_loans)
    result = calculate_dti(
        annual_income=annual_income,
        new_loan_amount=loan_amount,
        new_loan_rate=loan_rate,
        new_loan_months=loan_months,
        new_loan_method=loan_method,
        region=region,
        existing_mortgages=em,
        other_loans=ol,
    )
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


@tool
def calculate_dti_max_loan_tool(
    annual_income: float,
    loan_rate: float,
    loan_months: int,
    loan_method: str = "원리금균등",
    region: str = "투기과열",
    existing_mortgages: Optional[str] = None,
    other_loans: Optional[str] = None,
) -> str:
    """DTI 기준 최대 대출 가능액 역산.

    Args:
        annual_income: 연소득 (만원). 예: 5000 = 5천만원
        loan_rate: 약정 연이자율 (%). 예: 4.5
        loan_months: 상환기간 (개월). 예: 360 = 30년
        loan_method: 상환방식. 원리금균등/원금균등/만기일시 중 택1
        region: 지역. 투기과열(DTI 40%)/조정대상(50%)/비규제(60%) 중 택1
        existing_mortgages: 기존 주담대 JSON (선택)
        other_loans: 기타대출 JSON (선택, 이자만 반영)

    Returns:
        JSON 결과: max_loan, dti_limit_pct, allowed_annual, available_annual 포함
    """
    em = _parse_mortgages(existing_mortgages)
    ol = _parse_other_loans(other_loans)
    result = calculate_max_loan_by_dti(
        annual_income=annual_income,
        loan_rate=loan_rate,
        loan_months=loan_months,
        loan_method=loan_method,
        region=region,
        existing_mortgages=em,
        other_loans=ol,
    )
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


def get_tools():
    """이 스킬의 LangChain 도구 목록"""
    return [calculate_dti_tool, calculate_dti_max_loan_tool]


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------


def _parse_mortgages(json_str: str | None) -> list[Mortgage]:
    """Parse JSON string into list of Mortgage objects."""
    if not json_str:
        return []
    items = json.loads(json_str)
    return [
        Mortgage(
            balance=m["balance"],
            rate=m["rate"],
            remaining_months=m["remaining_months"],
            method=m.get("method", "원리금균등"),
        )
        for m in items
    ]


def _parse_other_loans(json_str: str | None) -> list[OtherLoan]:
    """Parse JSON string into list of OtherLoan objects."""
    if not json_str:
        return []
    items = json.loads(json_str)
    return [OtherLoan(balance=o["balance"], rate=o["rate"]) for o in items]


# ---------------------------------------------------------------------------
# CLI handlers
# ---------------------------------------------------------------------------


def _handle_calculate(args: argparse.Namespace) -> None:
    """Handle the 'calculate' subcommand."""
    existing_mortgages = _parse_mortgages(args.existing_mortgages)
    other_loans = _parse_other_loans(args.other_loans)

    result = calculate_dti(
        annual_income=args.annual_income,
        new_loan_amount=args.loan_amount,
        new_loan_rate=args.loan_rate,
        new_loan_months=args.loan_months,
        new_loan_method=args.loan_method,
        region=args.region,
        existing_mortgages=existing_mortgages,
        other_loans=other_loans,
        is_seomin=args.seomin,
    )

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


def _handle_max_loan(args: argparse.Namespace) -> None:
    """Handle the 'max-loan' subcommand."""
    existing_mortgages = _parse_mortgages(args.existing_mortgages)
    other_loans = _parse_other_loans(args.other_loans)

    result = calculate_max_loan_by_dti(
        annual_income=args.annual_income,
        loan_rate=args.loan_rate,
        loan_months=args.loan_months,
        loan_method=args.loan_method,
        region=args.region,
        existing_mortgages=existing_mortgages,
        other_loans=other_loans,
        is_seomin=args.seomin,
    )

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calculator.py",
        description="DTI (총부채상환비율) 계산기 - 신DTI 산정기준 반영",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- shared arguments ---------------------------------------------------
    def _add_common_args(sub: argparse.ArgumentParser) -> None:
        sub.add_argument(
            "--annual-income", type=float, required=True,
            help="연소득 (만원)",
        )
        sub.add_argument(
            "--loan-rate", type=float, required=True,
            help="약정 연이자율 (%%)",
        )
        sub.add_argument(
            "--loan-months", type=int, required=True,
            help="상환기간 (개월, 예: 360 = 30년)",
        )
        sub.add_argument(
            "--loan-method", type=str, default="원리금균등",
            choices=["원리금균등", "원금균등", "만기일시"],
            help="상환방식 (default: 원리금균등)",
        )
        sub.add_argument(
            "--region", type=str, default="투기과열",
            choices=["투기과열", "조정대상", "비규제"],
            help="지역 (default: 투기과열)",
        )
        sub.add_argument(
            "--existing-mortgages", type=str, default=None,
            help='기존 주담대 JSON 배열, e.g. \'[{"balance":10000,"rate":3.5,"remaining_months":240,"method":"원리금균등"}]\'',
        )
        sub.add_argument(
            "--other-loans", type=str, default=None,
            help='기타대출 JSON 배열, e.g. \'[{"balance":5000,"rate":5.0}]\'',
        )
        sub.add_argument(
            "--seomin", action="store_true", default=False,
            help="서민·실수요자 여부 (연소득 7천만 이하 무주택)",
        )

    # --- calculate subcommand -----------------------------------------------
    calc_parser = subparsers.add_parser(
        "calculate",
        help="DTI 계산 (신규 대출의 DTI 산출)",
    )
    _add_common_args(calc_parser)
    calc_parser.add_argument(
        "--loan-amount", type=float, required=True,
        help="신규 주담대 원금 (만원)",
    )
    calc_parser.set_defaults(func=_handle_calculate)

    # --- max-loan subcommand ------------------------------------------------
    max_parser = subparsers.add_parser(
        "max-loan",
        help="DTI 기준 최대 대출 가능액 역산",
    )
    _add_common_args(max_parser)
    max_parser.set_defaults(func=_handle_max_loan)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except json.JSONDecodeError as exc:
        error = {"error": f"JSON 파싱 실패: {exc}"}
        print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        error = {"error": str(exc)}
        print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
