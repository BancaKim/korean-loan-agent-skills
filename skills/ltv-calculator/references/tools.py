"""
LTV 계산기 LangChain Tool
SKILL.md에서 참조하는 tool 정의. create_deep_agent(tools=[...])에 등록하여 사용.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from langchain_core.tools import tool

# 같은 references/ 내의 calculator.py import
from . import calculator as _calc


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
    result = _calc.calculate_ltv_limit(
        property_value=property_value,
        region_type=region_type,
        borrower_type=borrower_type,
        senior_liens=senior_liens,
        deposit_region=deposit_region,
        has_tenant=has_tenant,
    )
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


def get_tools():
    """이 스킬의 도구 목록"""
    return [calculate_ltv]
