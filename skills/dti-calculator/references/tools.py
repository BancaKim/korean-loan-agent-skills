"""
DTI 계산기 LangChain Tools
SKILL.md에서 참조하는 tool 정의. create_deep_agent(tools=[...])에 등록하여 사용.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional

from langchain_core.tools import tool

from . import calculator as _calc


@tool
def calculate_dti(
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
    result = _calc.calculate_dti(
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
def calculate_dti_max_loan(
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
    result = _calc.calculate_max_loan_by_dti(
        annual_income=annual_income,
        loan_rate=loan_rate,
        loan_months=loan_months,
        loan_method=loan_method,
        region=region,
        existing_mortgages=em,
        other_loans=ol,
    )
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


def _parse_mortgages(raw: Optional[str]) -> list:
    if not raw:
        return []
    items = json.loads(raw)
    return [
        _calc.Mortgage(
            balance=m["balance"],
            rate=m["rate"],
            remaining_months=m["remaining_months"],
            method=m.get("method", "원리금균등"),
        )
        for m in items
    ]


def _parse_other_loans(raw: Optional[str]) -> list:
    if not raw:
        return []
    items = json.loads(raw)
    return [_calc.OtherLoan(balance=o["balance"], rate=o["rate"]) for o in items]


def get_tools():
    """이 스킬의 도구 목록"""
    return [calculate_dti, calculate_dti_max_loan]
