"""
대출가능액 종합 계산기 (CLI)
LTV/DTI/DSR 세 가지 규제를 동시 적용하여 실제 최대 대출 가능액 산출

Usage:
    python calculator.py calculate \
        --annual-income 6000 --property-value 70000 \
        --loan-rate 4.5 --loan-months 360 \
        --region-type 투기과열 --borrower-type 무주택 --rate-type 변동
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 같은 프로젝트 내 다른 계산기 import (하이픈 폴더명 -> importlib 사용)
# ---------------------------------------------------------------------------
_skills_dir = Path(__file__).resolve().parent.parent.parent


def _import_calculator(skill_folder: str):
    """하이픈이 포함된 폴더에서 calculator.py를 import"""
    module_name = f"{skill_folder.replace('-', '_')}_calc"
    module_path = _skills_dir / skill_folder / "references" / "calculator.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_ltv = _import_calculator("ltv-calculator")
_dti = _import_calculator("dti-calculator")
_dsr = _import_calculator("dsr-calculator")

calculate_ltv_limit = _ltv.calculate_ltv_limit
LTVResult = _ltv.LTVResult

calculate_max_loan_by_dti = _dti.calculate_max_loan_by_dti
MaxLoanByDTIResult = _dti.MaxLoanByDTIResult
Mortgage = _dti.Mortgage
OtherLoan = _dti.OtherLoan

calculate_max_mortgage_by_dsr = _dsr.calculate_max_mortgage_by_dsr
MaxLoanByDSRResult = _dsr.MaxLoanByDSRResult
ExistingLoan = _dsr.ExistingLoan

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class AffordabilityResult:
    ltv_limit: float        # LTV 한도 (만원)
    dti_limit: float        # DTI 한도 (만원)
    dsr_limit: float        # DSR 한도 (만원)
    final_limit: float      # 최종 한도 (만원)
    binding: str            # 바인딩 규제 (LTV/DTI/DSR)
    ltv_detail: LTVResult
    dti_detail: MaxLoanByDTIResult
    dsr_detail: MaxLoanByDSRResult
    improvement_tips: list[str]  # 한도 개선 시뮬레이션


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def _convert_mortgages_to_dti(existing_mortgages: list[dict] | None) -> list[Mortgage]:
    """기존 주담대를 DTI용 Mortgage 객체로 변환"""
    if not existing_mortgages:
        return []
    return [
        Mortgage(
            balance=m["balance"],
            rate=m["rate"],
            remaining_months=m["remaining_months"],
            method=m.get("method", "원리금균등"),
        )
        for m in existing_mortgages
    ]


def _convert_other_to_dti(other_loans: list[dict] | None) -> list[OtherLoan]:
    """기타대출을 DTI용 OtherLoan 객체로 변환"""
    if not other_loans:
        return []
    return [
        OtherLoan(balance=o["balance"], rate=o["rate"])
        for o in other_loans
    ]


def _convert_to_dsr_loans(
    existing_mortgages: list[dict] | None,
    other_loans: list[dict] | None,
) -> list[ExistingLoan]:
    """기존 대출을 DSR용 ExistingLoan 객체로 변환"""
    result = []
    for m in (existing_mortgages or []):
        result.append(ExistingLoan(
            balance=m["balance"],
            rate=m["rate"],
            remaining_months=m["remaining_months"],
            method=m.get("method", "원리금균등"),
            loan_type="주택담보대출",
            rate_type=m.get("rate_type", "변동"),
        ))
    for o in (other_loans or []):
        result.append(ExistingLoan(
            balance=o["balance"],
            rate=o["rate"],
            remaining_months=o.get("remaining_months", 60),
            method=o.get("method", "원리금균등"),
            loan_type=o.get("loan_type", "신용대출"),
            rate_type=o.get("rate_type", "변동"),
        ))
    return result


def _region_to_dsr_region(region_type: str) -> str:
    """지역유형을 DSR 지역으로 변환"""
    if region_type in ("투기과열", "조정대상"):
        return "수도권"
    return "지방"


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------


def calculate_loan_affordability(
    annual_income: float,
    property_value: float,
    loan_rate: float,
    loan_months: int,
    region_type: str = "투기과열",
    borrower_type: str = "무주택",
    repayment_method: str = "원리금균등",
    rate_type: str = "변동",
    sector: str = "은행",
    senior_liens: float = 0,
    existing_mortgages: list[dict] | None = None,
    other_loans: list[dict] | None = None,
) -> AffordabilityResult:
    """
    종합 대출가능액 산출 (LTV/DTI/DSR 동시 적용)

    Args:
        annual_income: 연소득 (만원)
        property_value: 주택 감정가 (만원)
        loan_rate: 약정 연이자율 (%)
        loan_months: 대출기간 (개월)
        region_type: 지역 (투기과열/조정대상/비규제)
        borrower_type: 차주유형 (무주택/서민실수요/생애최초/1주택처분/다주택)
        repayment_method: 상환방식
        rate_type: 금리유형 (변동/혼합5년/혼합10년/고정)
        sector: 금융권 (은행/2금융)
        senior_liens: 선순위채권 (만원)
        existing_mortgages: 기존 주담대 [{balance, rate, remaining_months, method}]
        other_loans: 기타대출 [{balance, rate, remaining_months, method, loan_type}]

    Returns:
        AffordabilityResult
    """
    # 1단계: LTV
    ltv_result = calculate_ltv_limit(
        property_value=property_value,
        region_type=region_type,
        borrower_type=borrower_type,
        senior_liens=senior_liens,
    )
    ltv_max = ltv_result.final_limit

    # 2단계: DTI
    dti_mortgages = _convert_mortgages_to_dti(existing_mortgages)
    dti_others = _convert_other_to_dti(other_loans)
    dti_result = calculate_max_loan_by_dti(
        annual_income=annual_income,
        loan_rate=loan_rate,
        loan_months=loan_months,
        loan_method=repayment_method,
        region=region_type,
        existing_mortgages=dti_mortgages,
        other_loans=dti_others,
    )
    dti_max = dti_result.max_loan

    # 3단계: DSR
    dsr_region = _region_to_dsr_region(region_type)
    dsr_loans = _convert_to_dsr_loans(existing_mortgages, other_loans)
    dsr_result = calculate_max_mortgage_by_dsr(
        annual_income=annual_income,
        loan_rate=loan_rate,
        loan_months=loan_months,
        loan_method=repayment_method,
        rate_type=rate_type,
        region=dsr_region,
        sector=sector,
        existing_loans=dsr_loans,
    )
    dsr_max = dsr_result.max_loan

    # 4단계: 최종 한도
    limits = {"LTV": ltv_max, "DTI": dti_max, "DSR": dsr_max}
    binding = min(limits, key=limits.get)
    final = limits[binding]

    # 한도 개선 시뮬레이션
    tips = _generate_improvement_tips(
        binding, annual_income, property_value, loan_rate, loan_months,
        repayment_method, rate_type, region_type, borrower_type, sector,
        dsr_region, dsr_loans, dsr_max,
    )

    return AffordabilityResult(
        ltv_limit=ltv_max,
        dti_limit=dti_max,
        dsr_limit=dsr_max,
        final_limit=final,
        binding=binding,
        ltv_detail=ltv_result,
        dti_detail=dti_result,
        dsr_detail=dsr_result,
        improvement_tips=tips,
    )


# ---------------------------------------------------------------------------
# Improvement tips
# ---------------------------------------------------------------------------


def _generate_improvement_tips(
    binding, annual_income, property_value, loan_rate, loan_months,
    method, rate_type, region_type, borrower_type, sector,
    dsr_region, dsr_loans, current_dsr_max,
) -> list[str]:
    """바인딩 규제별 한도 개선 시뮬레이션"""
    tips = []

    if binding == "DSR":
        # 고정금리 전환 시뮬레이션
        if rate_type != "고정":
            sim = calculate_max_mortgage_by_dsr(
                annual_income, loan_rate, loan_months, method,
                "고정", dsr_region, sector, dsr_loans,
            )
            diff = sim.max_loan - current_dsr_max
            if diff > 0:
                tips.append(f"고정금리 전환 시: DSR {current_dsr_max/10000:.1f}억 -> {sim.max_loan/10000:.1f}억 (+{diff/10000:.1f}억)")

        # 만기 연장 (40년)
        if loan_months < 480:
            sim = calculate_max_mortgage_by_dsr(
                annual_income, loan_rate, 480, method,
                rate_type, dsr_region, sector, dsr_loans,
            )
            diff = sim.max_loan - current_dsr_max
            if diff > 0:
                tips.append(f"만기 40년 연장 시: DSR {current_dsr_max/10000:.1f}억 -> {sim.max_loan/10000:.1f}억 (+{diff/10000:.1f}억)")

    elif binding == "LTV":
        if borrower_type == "무주택" and region_type in ("투기과열", "조정대상"):
            # 서민실수요자 우대 안내
            sim_seomin = calculate_ltv_limit(property_value, region_type, "서민실수요")
            current_ltv = calculate_ltv_limit(property_value, region_type, "무주택").final_limit
            diff_seomin = sim_seomin.final_limit - current_ltv
            if diff_seomin > 0 and annual_income <= 9000:
                tips.append(f"서민실수요자 자격 시: LTV {sim_seomin.ltv_rate_pct}% -> +{diff_seomin/10000:.1f}억 (연소득 9천만 이하 무주택)")
            # 생애최초 우대 안내
            sim = calculate_ltv_limit(property_value, region_type, "생애최초")
            diff = sim.final_limit - current_ltv
            if diff > 0:
                tips.append(f"생애최초 자격 시: LTV {sim.ltv_rate_pct}% -> +{diff/10000:.1f}억")

    elif binding == "DTI":
        if region_type != "비규제":
            tips.append("비규제지역 매수 시 DTI 60% 적용 가능")

    return tips


# ---------------------------------------------------------------------------
# Pretty-print (kept for backward compat / interactive use)
# ---------------------------------------------------------------------------


def print_result(r: AffordabilityResult):
    """결과 출력"""
    print("┌─────────────────────────────────────────────┐")
    print("│           대출가능액 종합 분석 결과            │")
    print("├──────────┬──────────┬────────────────────────┤")
    print("│  규제    │  한도    │  산출 근거              │")
    print("├──────────┼──────────┼────────────────────────┤")
    print(f"│  LTV     │ {r.ltv_limit/10000:>5.1f}억  │ {r.ltv_detail.details:<22s} │")
    print(f"│  DTI     │ {r.dti_limit/10000:>5.1f}억  │ DTI {r.dti_detail.dti_limit_pct:.0f}% 역산{' ':>12s} │")
    print(f"│  DSR     │ {r.dsr_limit/10000:>5.1f}억  │ 스트레스 {r.dsr_detail.stress_rate}% 적용{' ':>5s} │")
    print("├──────────┼──────────┼────────────────────────┤")
    binding_mark = f"바인딩: {r.binding}"
    print(f"│ ★ 최종   │ {r.final_limit/10000:>5.1f}억  │ {binding_mark:<22s} │")
    print("└──────────┴──────────┴────────────────────────┘")

    if r.improvement_tips:
        print("\n▶ 한도 개선 시뮬레이션:")
        for tip in r.improvement_tips:
            print(f"  · {tip}")


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------


def _dataclass_to_dict(obj: Any) -> Any:
    """Recursively convert dataclass instances (and common types) to dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _dataclass_to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def result_to_json(r: AffordabilityResult) -> str:
    """AffordabilityResult -> pretty-printed JSON string."""
    payload: Dict[str, Any] = {
        "ltv_limit": r.ltv_limit,
        "dti_limit": r.dti_limit,
        "dsr_limit": r.dsr_limit,
        "final_limit": r.final_limit,
        "binding": r.binding,
        "improvement_tips": r.improvement_tips,
        "ltv_detail": _dataclass_to_dict(r.ltv_detail),
        "dti_detail": _dataclass_to_dict(r.dti_detail),
        "dsr_detail": _dataclass_to_dict(r.dsr_detail),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI (argparse)
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calculator.py",
        description="대출가능액 종합 계산기 - LTV/DTI/DSR 동시 적용",
    )
    sub = parser.add_subparsers(dest="command")

    calc = sub.add_parser("calculate", help="종합 대출가능액 산출")

    # Required arguments
    calc.add_argument("--annual-income", type=float, required=True,
                      help="연소득 (만원)")
    calc.add_argument("--property-value", type=float, required=True,
                      help="주택 감정가 (만원)")
    calc.add_argument("--loan-rate", type=float, required=True,
                      help="약정 연이자율 (%%)")
    calc.add_argument("--loan-months", type=int, required=True,
                      help="대출기간 (개월)")

    # Optional arguments with defaults
    calc.add_argument("--region-type", type=str, default="투기과열",
                      choices=["투기과열", "조정대상", "비규제"],
                      help="지역유형 (default: 투기과열)")
    calc.add_argument("--borrower-type", type=str, default="무주택",
                      choices=["무주택", "서민실수요", "생애최초", "1주택처분", "다주택"],
                      help="차주유형 (default: 무주택). 서민실수요=연소득 9천만 이하 무주택")
    calc.add_argument("--repayment-method", type=str, default="원리금균등",
                      choices=["원리금균등", "원금균등", "만기일시"],
                      help="상환방식 (default: 원리금균등)")
    calc.add_argument("--rate-type", type=str, default="변동",
                      choices=["변동", "혼합5년", "혼합10년", "고정"],
                      help="금리유형 (default: 변동)")
    calc.add_argument("--sector", type=str, default="은행",
                      choices=["은행", "2금융"],
                      help="금융권 (default: 은행)")
    calc.add_argument("--senior-liens", type=float, default=0,
                      help="선순위채권 (만원, default: 0)")

    # JSON-string arguments for existing debts
    calc.add_argument("--existing-mortgages", type=str, default=None,
                      help='기존 주담대 JSON 배열 (예: \'[{"balance":10000,"rate":3.5,"remaining_months":240}]\')')
    calc.add_argument("--other-loans", type=str, default=None,
                      help='기타대출 JSON 배열 (예: \'[{"balance":2000,"rate":5.0}]\')')

    return parser


def _parse_json_list(raw: str | None) -> list[dict] | None:
    """Parse a JSON string into a list of dicts, or return None."""
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"JSON 파싱 오류: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, list):
        print("JSON은 배열이어야 합니다.", file=sys.stderr)
        sys.exit(1)
    return data


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "calculate":
        existing_mortgages = _parse_json_list(args.existing_mortgages)
        other_loans = _parse_json_list(args.other_loans)

        result = calculate_loan_affordability(
            annual_income=args.annual_income,
            property_value=args.property_value,
            loan_rate=args.loan_rate,
            loan_months=args.loan_months,
            region_type=args.region_type,
            borrower_type=args.borrower_type,
            repayment_method=args.repayment_method,
            rate_type=args.rate_type,
            sector=args.sector,
            senior_liens=args.senior_liens,
            existing_mortgages=existing_mortgages,
            other_loans=other_loans,
        )

        print(result_to_json(result))


if __name__ == "__main__":
    main()
