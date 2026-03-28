#!/usr/bin/env python3
"""
Evaluation Set: 20건 시나리오
금감원 DSR 산정기준 + 금융위 가계부채 관리방안 기반 Ground Truth와 계산기 결과를 비교합니다.
"""

from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
PYTHON = sys.executable


def run_calc(calculator: str, subcommand: str, args: list[str]) -> dict:
    script = SKILLS_DIR / calculator / "references" / "calculator.py"
    cmd = [PYTHON, str(script), subcommand] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:200])
    return json.loads(result.stdout)


EVAL_SET = [

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # "대출 얼마나 받을 수 있어?" — 종합 대출가능액 (12건)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    {
        "id": 1,
        "name": "맞벌이 연소득 1억, 서울 8억 아파트",
        "desc": "맞벌이 연소득 1억이고 서울 8억 아파트 사려고 해. 무주택이고 생애최초 아니고 변동금리야. 대출 가능한 금액이 얼마야?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "10000", "--property-value", "80000",
                 "--loan-rate", "4.5", "--loan-months", "360",
                 "--region-type", "투기과열", "--borrower-type", "무주택",
                 "--rate-type", "변동"],
        "ground_truth": {"binding": "LTV", "ltv_limit": 32000.0},
        "check": lambda r, gt: r["binding"] == "LTV" and r["ltv_limit"] == gt["ltv_limit"],
    },
    {
        "id": 2,
        "name": "사회초년생 첫 집, 서울 5억",
        "desc": "사회초년생인데 연소득 4천만이야. 서울 5억짜리 첫 집 사려고 하는데 변동금리 4.5% 30년이면 얼마까지 돼?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "4000", "--property-value", "50000",
                 "--loan-rate", "4.5", "--loan-months", "360",
                 "--region-type", "투기과열", "--borrower-type", "생애최초",
                 "--rate-type", "변동"],
        "ground_truth": {"binding": "DSR", "ltv_limit": 35000.0},
        "check": lambda r, gt: r["binding"] == "DSR" and r["ltv_limit"] == gt["ltv_limit"],
    },
    {
        "id": 3,
        "name": "고정금리로 바꾸면 유리해?",
        "desc": "연소득 6천만이고 서울 7억 아파트 생애최초야. 고정금리로 받으면 변동보다 유리해?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "6000", "--property-value", "70000",
                 "--loan-rate", "4.5", "--loan-months", "360",
                 "--region-type", "투기과열", "--borrower-type", "생애최초",
                 "--rate-type", "고정"],
        "ground_truth": {"binding": "DSR"},
        "check": lambda r, gt: r["binding"] == "DSR" and r["dsr_detail"]["stress_rate"] == 4.5,
    },
    {
        "id": 4,
        "name": "지방 소도시 3억 아파트",
        "desc": "연소득 4천만이고 지방 3억짜리 아파트 보고 있어. 무주택이고 변동금리 4% 30년이면?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "4000", "--property-value", "30000",
                 "--loan-rate", "4.0", "--loan-months", "360",
                 "--region-type", "비규제", "--borrower-type", "무주택",
                 "--rate-type", "변동"],
        "ground_truth": {"ltv_limit": 21000.0},
        "check": lambda r, gt: r["ltv_limit"] == gt["ltv_limit"] and r["dsr_detail"]["stress_rate"] == 4.75,
    },
    {
        "id": 5,
        "name": "서울 15억 아파트, 절대한도",
        "desc": "연소득 8천만 무주택 서민실수요자야. 서울 15억짜리 아파트 대출 한도가 얼마야?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "8000", "--property-value", "150000",
                 "--loan-rate", "4.5", "--loan-months", "360",
                 "--region-type", "투기과열", "--borrower-type", "서민실수요",
                 "--rate-type", "변동"],
        "ground_truth": {"ltv_limit": 60000.0},
        "check": lambda r, gt: r["ltv_detail"]["has_absolute_cap"] and r["ltv_limit"] == gt["ltv_limit"],
    },
    {
        "id": 6,
        "name": "기존 대출 있는데 추가로 받을 수 있어?",
        "desc": "연소득 8천만인데 이미 주담대 1억(3.5%)이랑 신용대출 3천만(5%)이 있어. 서울 9억 아파트 추가 대출 받을 수 있어?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "8000", "--property-value", "90000",
                 "--loan-rate", "4.0", "--loan-months", "360",
                 "--region-type", "투기과열", "--borrower-type", "무주택",
                 "--rate-type", "혼합5년",
                 "--existing-mortgages", '[{"balance":10000,"rate":3.5,"remaining_months":240,"method":"원리금균등"}]',
                 "--other-loans", '[{"balance":3000,"rate":5.0,"remaining_months":36,"method":"원리금균등","loan_type":"신용대출"}]'],
        "ground_truth": {"binding": "DSR"},
        "check": lambda r, gt: r["binding"] == "DSR" and r["final_limit"] < r["ltv_limit"],
    },
    {
        "id": 7,
        "name": "비규제 지방, 생애최초, 고정금리 (최선 조건)",
        "desc": "연소득 6천만이고 지방(비규제) 4억 아파트 생애최초야. 고정금리 3.5% 30년이면?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "6000", "--property-value", "40000",
                 "--loan-rate", "3.5", "--loan-months", "360",
                 "--region-type", "비규제", "--borrower-type", "생애최초",
                 "--rate-type", "고정"],
        "ground_truth": {"ltv_limit": 32000.0},
        "check": lambda r, gt: r["ltv_limit"] == gt["ltv_limit"] and r["dsr_detail"]["stress_rate"] == 3.5,
    },
    {
        "id": 8,
        "name": "1금융 안 되면 2금융은?",
        "desc": "연소득 5천만인데 1금융 안 되면 2금융(저축은행)은? 서울 6억 변동 5.5%야.",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "5000", "--property-value", "60000",
                 "--loan-rate", "5.5", "--loan-months", "360",
                 "--region-type", "투기과열", "--borrower-type", "무주택",
                 "--rate-type", "변동", "--sector", "2금융"],
        "ground_truth": {"ltv_limit": 24000.0},
        "check": lambda r, gt: r["ltv_limit"] == gt["ltv_limit"] and r["dsr_detail"]["dsr_limit_pct"] == 50.0,
    },
    {
        "id": 9,
        "name": "서울 25억 초고가 아파트",
        "desc": "연소득 2억이고 서울 25억 아파트 생애최초로 사려는데. 고정금리야. 얼마까지 돼?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "20000", "--property-value", "250000",
                 "--loan-rate", "4.0", "--loan-months", "360",
                 "--region-type", "투기과열", "--borrower-type", "생애최초",
                 "--rate-type", "고정"],
        "ground_truth": {"binding": "LTV", "ltv_limit": 40000.0},
        "check": lambda r, gt: r["binding"] == "LTV" and r["ltv_limit"] == gt["ltv_limit"] and r["ltv_detail"]["has_absolute_cap"],
    },
    {
        "id": 10,
        "name": "혼합형 10년 고정금리면 스트레스가 얼마나 붙어?",
        "desc": "연소득 7천만이고 서울 8억 생애최초야. 혼합형 10년 고정금리 4.5%면 스트레스가 얼마나 붙어?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "7000", "--property-value", "80000",
                 "--loan-rate", "4.5", "--loan-months", "360",
                 "--region-type", "투기과열", "--borrower-type", "생애최초",
                 "--rate-type", "혼합10년"],
        "ground_truth": {"binding": "DSR"},
        "check": lambda r, gt: r["binding"] == "DSR" and r["dsr_detail"]["stress_rate"] == 6.3,
    },
    {
        "id": 11,
        "name": "연소득 3천만, 지방 2억 소형 아파트",
        "desc": "연소득 3천만이고 지방 소도시 2억짜리 아파트야. 고정금리 3.8% 20년이면?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "3000", "--property-value", "20000",
                 "--loan-rate", "3.8", "--loan-months", "240",
                 "--region-type", "비규제", "--borrower-type", "무주택",
                 "--rate-type", "고정"],
        "ground_truth": {"ltv_limit": 14000.0},
        "check": lambda r, gt: r["ltv_limit"] == gt["ltv_limit"],
    },
    {
        "id": 12,
        "name": "집 한 채 있는데 갈아타기 대출",
        "desc": "연소득 1.2억인데 이미 집이 한 채 있어. 서울 10억짜리로 갈아타려고 기존 집 처분 조건으로 대출 받으면?",
        "calculator": "loan-affordability",
        "sub": "calculate",
        "args": ["--annual-income", "12000", "--property-value", "100000",
                 "--loan-rate", "4.0", "--loan-months", "360",
                 "--region-type", "투기과열", "--borrower-type", "1주택처분",
                 "--rate-type", "혼합5년"],
        "ground_truth": {"ltv_limit": 50000.0, "binding": "LTV"},
        "check": lambda r, gt: r["ltv_limit"] == gt["ltv_limit"] and r["binding"] == "LTV",
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # "DSR이 몇 %야?" (3건)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    {
        "id": 13,
        "name": "고정금리 DSR",
        "desc": "연소득 5천만인데 3억 대출 고정금리 4.5% 30년으로 받으면 DSR이 몇 퍼센트야?",
        "calculator": "dsr-calculator",
        "sub": "calculate",
        "args": ["--annual-income", "5000", "--loan-amount", "30000",
                 "--loan-rate", "4.5", "--loan-months", "360",
                 "--rate-type", "고정", "--region", "수도권"],
        "ground_truth": {"dsr_pct": 36.48, "stress_rate": 4.5, "is_pass": True},
        "check": lambda r, gt: abs(r["dsr_pct"] - gt["dsr_pct"]) < 0.1 and r["is_pass"],
    },
    {
        "id": 14,
        "name": "변동금리면 스트레스 금리 붙는다던데",
        "desc": "같은 조건인데 변동금리로 바꾸면? 스트레스 금리가 붙는다던데.",
        "calculator": "dsr-calculator",
        "sub": "calculate",
        "args": ["--annual-income", "5000", "--loan-amount", "30000",
                 "--loan-rate", "4.5", "--loan-months", "360",
                 "--rate-type", "변동", "--region", "수도권"],
        "ground_truth": {"dsr_pct": 50.34, "stress_rate": 7.5, "is_pass": False},
        "check": lambda r, gt: abs(r["dsr_pct"] - gt["dsr_pct"]) < 0.1 and r["stress_rate"] == 7.5 and not r["is_pass"],
    },
    {
        "id": 15,
        "name": "변동에서 고정으로 바꾸면 얼마나 더 받을 수 있어?",
        "desc": "연소득 5천만인데 변동금리에서 고정으로 바꾸면 대출 가능액이 얼마나 늘어나?",
        "calculator": "dsr-calculator",
        "sub": "max-loan",
        "args": ["--annual-income", "5000", "--loan-rate", "4.5",
                 "--loan-months", "360", "--rate-type", "변동", "--region", "수도권"],
        "ground_truth": {},
        "check": lambda r, gt: (
            r["max_loan"] > 0
            and "by_rate_type" in r
            and any(v > r["max_loan"] for k, v in r["by_rate_type"].items() if "고정" in k)
        ),
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # "담보 대비 얼마까지 돼?" — LTV (3건)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    {
        "id": 16,
        "name": "9억 넘는 아파트는 LTV가 다르게 적용된다며?",
        "desc": "서울 12억 아파트인데 9억 넘는 부분은 LTV가 다르게 적용된다며?",
        "calculator": "ltv-calculator",
        "sub": "calculate",
        "args": ["--property-value", "120000", "--region-type", "투기과열",
                 "--borrower-type", "무주택"],
        "ground_truth": {"final_limit": 42000.0, "high_value_applied": True},
        "check": lambda r, gt: r["final_limit"] == gt["final_limit"] and r["high_value_applied"],
    },
    {
        "id": 17,
        "name": "집 2채 있는데 하나 더 살 수 있어?",
        "desc": "이미 집이 2채 있는데 서울에서 한 채 더 살 수 있어? 대출 가능해?",
        "calculator": "ltv-calculator",
        "sub": "calculate",
        "args": ["--property-value", "70000", "--region-type", "투기과열",
                 "--borrower-type", "다주택"],
        "ground_truth": {"final_limit": 0, "ltv_rate_pct": 0},
        "check": lambda r, gt: r["final_limit"] == 0,
    },
    {
        "id": 18,
        "name": "서민실수요자 LTV 우대",
        "desc": "연소득 8천만 이하 무주택인데 서민실수요자로 LTV 우대 받을 수 있어? 서울 7억이야.",
        "calculator": "ltv-calculator",
        "sub": "calculate",
        "args": ["--property-value", "70000", "--region-type", "투기과열",
                 "--borrower-type", "서민실수요"],
        "ground_truth": {"ltv_rate_pct": 70.0, "final_limit": 49000.0},
        "check": lambda r, gt: r["final_limit"] == gt["final_limit"] and r["ltv_rate_pct"] == 70.0,
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # "DTI는 어떻게 계산돼?" (2건)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    {
        "id": 19,
        "name": "기존 신용대출이 DTI에 어떻게 반영돼?",
        "desc": "이미 신용대출 5천만(5%)이 있는데 DTI 계산할 때 이것도 포함돼? DSR이랑 뭐가 달라?",
        "calculator": "dti-calculator",
        "sub": "calculate",
        "args": ["--annual-income", "5000", "--loan-amount", "30000",
                 "--loan-rate", "4.5", "--loan-months", "360",
                 "--existing-mortgages", '[{"balance":10000,"rate":3.5,"remaining_months":240,"method":"원리금균등"}]',
                 "--other-loans", '[{"balance":5000,"rate":5.0}]'],
        "ground_truth": {"other_loan_interest_annual": 250.0, "dti_pct": 55.4, "is_pass": True},
        "check": lambda r, gt: r["other_loan_interest_annual"] == 250.0 and abs(r["dti_pct"] - gt["dti_pct"]) < 0.1,
    },
    {
        "id": 20,
        "name": "DTI 기준 최대 대출 가능액",
        "desc": "연소득 5천만이고 서울(투기과열)인데 DTI 기준으로 최대 얼마까지 대출 가능해?",
        "calculator": "dti-calculator",
        "sub": "max-loan",
        "args": ["--annual-income", "5000", "--loan-rate", "4.5",
                 "--loan-months", "360", "--region", "투기과열"],
        "ground_truth": {},
        "check": lambda r, gt: r["max_loan"] > 0 and r["dti_limit_pct"] == 60.0,
    },
]


def run_evaluation():
    print(f"=== Evaluation Set ({len(EVAL_SET)}건) ===\n")
    results = []

    for ev in EVAL_SET:
        try:
            output = run_calc(ev["calculator"], ev["sub"], ev["args"])
            passed = ev["check"](output, ev["ground_truth"])
            status = "PASS" if passed else "FAIL"

            key_vals = {}
            for k in ev["ground_truth"]:
                if k in output:
                    key_vals[k] = output[k]

            print(f"  [{status}] #{ev['id']} {ev['name']}")
            if not passed:
                print(f"    기대: {ev['ground_truth']}")
                print(f"    실제: {key_vals}")

            results.append({**ev, "output": output, "passed": passed, "key_vals": key_vals})

        except Exception as e:
            print(f"  [ERROR] #{ev['id']} {ev['name']}: {e}")
            results.append({**ev, "output": None, "passed": False, "key_vals": {}})

    return results


def generate_eval_md(results):
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    lines = [
        f"# Evaluation Results",
        f"",
        f"**{passed}/{total} 통과** | Ground Truth: 금감원 DSR 산정기준 + 금융위 가계부채 관리방안 기반 | {datetime.now().strftime('%Y-%m-%d')}",
        f"",
        f"## 요약",
        f"",
        f"| # | 질문 | 계산기 | 결과 |",
        f"|:-:|------|--------|:----:|",
    ]

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        q = r["desc"][:60] + "..." if len(r["desc"]) > 60 else r["desc"]
        lines.append(f"| {r['id']} | {q} | `{r['calculator']}` | **{status}** |")

    lines.extend([
        f"",
        f"## 상세",
        f"",
    ])

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        lines.append(f"### #{r['id']} [{status}] {r['name']}")
        lines.append(f"> {r['desc']}")
        lines.append(f"")

    return "\n".join(lines)


if __name__ == "__main__":
    results = run_evaluation()

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n{'='*50}")
    print(f"결과: {passed}/{total} 통과")

    md = generate_eval_md(results)
    out = Path(__file__).parent / "EVAL_RESULTS.md"
    out.write_text(md, encoding="utf-8")
    print(f"결과 저장: {out}")

    sys.exit(0 if passed == total else 1)
