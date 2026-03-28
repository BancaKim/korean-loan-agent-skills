"""
종합 대출가능액 계산기 LangChain Tool
SKILL.md에서 참조하는 tool 정의. create_deep_agent(tools=[...])에 등록하여 사용.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional

from langchain_core.tools import tool

from . import calculator as _calc


@tool
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
    existing_mortgages: Optional[str] = None,
    other_loans: Optional[str] = None,
) -> str:
    """한국 주택담보대출 종합 대출가능액 계산기. LTV·DTI·DSR 세 가지 규제를 동시 적용하여 최대 대출 가능액 산출.

    Args:
        annual_income: 연소득 (만원 단위). 예: 6000 = 6천만원
        property_value: 주택 감정가 (만원 단위). 예: 70000 = 7억원
        loan_rate: 약정 연이자율 (%). 예: 4.5
        loan_months: 대출기간 (개월). 예: 360 = 30년
        region_type: 지역유형. 투기과열(서울 등)/조정대상/비규제 중 택1
        borrower_type: 차주유형. 무주택/서민실수요/생애최초/1주택처분/다주택 중 택1
        repayment_method: 상환방식. 원리금균등/원금균등/만기일시 중 택1
        rate_type: 금리유형. 변동/혼합5년/혼합10년/고정 중 택1
        sector: 금융권. 은행/2금융 중 택1
        senior_liens: 선순위채권 잔액 (만원). 기본 0
        existing_mortgages: 기존 주담대 JSON 문자열. 예: '[{"balance":10000,"rate":3.5,"remaining_months":240,"method":"원리금균등"}]'
        other_loans: 기타대출 JSON 문자열. 예: '[{"balance":5000,"rate":5.0,"remaining_months":36,"method":"원리금균등","loan_type":"신용대출"}]'

    Returns:
        JSON 결과: ltv_limit, dti_limit, dsr_limit, final_limit, binding(바인딩 규제), improvement_tips 포함
    """
    em = json.loads(existing_mortgages) if existing_mortgages else None
    ol = json.loads(other_loans) if other_loans else None

    result = _calc.calculate_loan_affordability(
        annual_income=annual_income,
        property_value=property_value,
        loan_rate=loan_rate,
        loan_months=loan_months,
        region_type=region_type,
        borrower_type=borrower_type,
        repayment_method=repayment_method,
        rate_type=rate_type,
        sector=sector,
        senior_liens=senior_liens,
        existing_mortgages=em,
        other_loans=ol,
    )
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


def get_tools():
    """이 스킬의 도구 목록"""
    return [calculate_loan_affordability]
