"""
DSR 계산기 LangChain Tools
SKILL.md에서 참조하는 tool 정의. create_deep_agent(tools=[...])에 등록하여 사용.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional

from langchain_core.tools import tool

from . import calculator as _calc


@tool
def calculate_dsr(
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
    el = _parse_existing_loans(existing_loans)
    result = _calc.calculate_dsr(
        annual_income=annual_income,
        new_loan_amount=loan_amount,
        new_loan_rate=loan_rate,
        new_loan_months=loan_months,
        new_loan_method=loan_method,
        new_loan_rate_type=rate_type,
        region=region,
        sector=sector,
        existing_loans=el,
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
    el = _parse_existing_loans(existing_loans)
    result = _calc.calculate_max_mortgage_by_dsr(
        annual_income=annual_income,
        loan_rate=loan_rate,
        loan_months=loan_months,
        loan_method=loan_method,
        rate_type=rate_type,
        region=region,
        sector=sector,
        existing_loans=el,
    )
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


def _parse_existing_loans(raw: Optional[str]) -> list:
    if not raw:
        return []
    items = json.loads(raw)
    return [
        _calc.ExistingLoan(
            balance=item["balance"],
            rate=item["rate"],
            remaining_months=item["remaining_months"],
            method=item["method"],
            loan_type=item.get("loan_type", "주택담보대출"),
            rate_type=item.get("rate_type", "변동"),
        )
        for item in items
    ]


def get_tools():
    """이 스킬의 도구 목록"""
    return [calculate_dsr, calculate_dsr_max_loan]
