#!/usr/bin/env python3
"""
LLM Judge: DeepAgent 응답을 Ground Truth와 비교하여 PASS/FAIL 판정

Usage:
    .venv/bin/python tests/eval_judge.py
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from openai import OpenAI

client = OpenAI()
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gpt-4o")

# Ground Truth (eval_scenarios.py 기반, 핵심 수치만 추출)
GROUND_TRUTH = {
    1: {
        "question": "맞벌이 연소득 1억이고 서울 8억 아파트 사려고 해. 무주택이고 생애최초 아니고 변동금리야. 대출 가능한 금액이 얼마야?",
        "answer": "LTV 40% 적용 → 최대 대출 한도 3.2억(32,000만원). 담보(LTV) 한도가 가장 적어서 이것이 최종 한도.",
        "key_facts": ["LTV 40%", "대출 한도 3.2억 또는 32,000만원", "LTV가 제한 요소(바인딩)"],
    },
    2: {
        "question": "사회초년생인데 연소득 4천만이야. 서울 5억짜리 첫 집 사려고 하는데 변동금리 4.5% 30년이면 얼마까지 돼?",
        "answer": "생애최초로 LTV 70% = 3.5억이지만, DSR(소득 대비 상환 비율)이 더 적어서 DSR이 최종 한도를 결정.",
        "key_facts": ["생애최초 LTV 70%", "LTV 한도 3.5억", "DSR이 제한 요소"],
    },
    3: {
        "question": "연소득 6천만이고 서울 7억 아파트 생애최초야. 고정금리로 받으면 변동보다 유리해?",
        "answer": "고정금리는 스트레스 가산금리가 0%이므로 변동(+3.0%p)보다 DSR이 유리. 고정이면 약정금리 그대로 4.5%로 DSR 계산.",
        "key_facts": ["고정금리 스트레스 가산 0%", "변동금리 스트레스 +3.0%p", "고정이 DSR에서 유리"],
    },
    4: {
        "question": "연소득 4천만이고 지방 3억짜리 아파트 보고 있어. 무주택이고 변동금리 4% 30년이면?",
        "answer": "비규제지역 LTV 70% = 2.1억. 지방 변동금리 스트레스 가산은 0.75%p → 4.75%로 DSR 계산.",
        "key_facts": ["LTV 70%", "대출 한도 2.1억", "스트레스 가산 0.75%p", "스트레스 적용 금리 4.75%"],
    },
    5: {
        "question": "연소득 8천만 무주택 서민실수요자야. 서울 15억짜리 아파트 대출 한도가 얼마야?",
        "answer": "서민실수요자 LTV 70% = 10.5억이지만 규제지역 절대한도 6억(15억 이하)이 적용 → 최종 6억.",
        "key_facts": ["서민실수요자 LTV 70%", "절대한도 6억", "최종 한도 6억"],
    },
    6: {
        "question": "연소득 8천만인데 이미 주담대 1억(3.5%)이랑 신용대출 3천만(5%)이 있어. 서울 9억 아파트 추가 대출 받을 수 있어?",
        "answer": "기존 대출의 원리금 상환액이 DSR에 포함되어 여유가 크게 줄어듦. DSR이 최종 한도를 결정하여 약 1.9억 정도.",
        "key_facts": ["기존 대출이 DSR에 포함", "DSR이 제한 요소", "최종 한도 약 1.9~2억"],
    },
    7: {
        "question": "연소득 6천만이고 지방(비규제) 4억 아파트 생애최초야. 고정금리 3.5% 30년이면?",
        "answer": "비규제 생애최초 LTV 80% = 3.2억. 고정금리라 스트레스 가산 0% → 약정금리 그대로 DSR 계산.",
        "key_facts": ["비규제 생애최초 LTV 80%", "대출 한도 3.2억", "고정 스트레스 0%"],
    },
    8: {
        "question": "연소득 5천만인데 1금융 안 되면 2금융(저축은행)은? 서울 6억 변동 5.5%야.",
        "answer": "2금융은 DSR 한도가 50%(1금융 40%)라서 여유가 더 있음. LTV 40% = 2.4억.",
        "key_facts": ["2금융 DSR 한도 50%", "1금융 DSR 40%", "LTV 2.4억"],
    },
    9: {
        "question": "연소득 2억이고 서울 25억 아파트 생애최초로 사려는데. 고정금리야. 얼마까지 돼?",
        "answer": "생애최초 LTV 70%면 17.5억이지만 25억 이하 절대한도 4억 적용 → 최종 4억.",
        "key_facts": ["절대한도 4억", "25억 이하 절대한도 적용", "최종 한도 4억"],
    },
    10: {
        "question": "연소득 7천만이고 서울 8억 생애최초야. 혼합형 10년 고정금리 4.5%면 스트레스가 얼마나 붙어?",
        "answer": "혼합10년은 스트레스 60% 적용 → 3.0%p × 60% = 1.8%p → 4.5% + 1.8% = 6.3%로 DSR 계산.",
        "key_facts": ["혼합10년 스트레스 60%", "가산 1.8%p", "적용금리 6.3%"],
    },
    11: {
        "question": "연소득 3천만이고 지방 소도시 2억짜리 아파트야. 고정금리 3.8% 20년이면?",
        "answer": "비규제 무주택 LTV 70% = 1.4억이 최종 한도.",
        "key_facts": ["LTV 70%", "대출 한도 1.4억"],
    },
    12: {
        "question": "연소득 1.2억인데 이미 집이 한 채 있어. 서울 10억짜리로 갈아타려고 기존 집 처분 조건으로 대출 받으면?",
        "answer": "1주택 처분조건 LTV 50% = 5억. LTV가 최종 한도를 결정.",
        "key_facts": ["1주택 처분조건 LTV 50%", "대출 한도 5억", "LTV가 제한 요소"],
    },
    13: {
        "question": "연소득 5천만인데 3억 대출 고정금리 4.5% 30년으로 받으면 DSR이 몇 퍼센트야?",
        "answer": "고정금리라 스트레스 가산 없이 4.5%로 계산 → DSR 약 36.48%. 40% 이하라 통과.",
        "key_facts": ["DSR 약 36.5% (36.48%)", "40% 이하 통과", "스트레스 가산 0%"],
    },
    14: {
        "question": "같은 조건인데 변동금리로 바꾸면? 스트레스 금리가 붙는다던데.",
        "answer": "변동금리면 +3.0%p 가산 → 7.5%로 DSR 계산 → 약 50.34%. 40% 초과라 통과 불가.",
        "key_facts": ["스트레스 +3.0%p", "적용금리 7.5%", "DSR 약 50% (50.34%)", "40% 초과 불통과"],
    },
    15: {
        "question": "연소득 5천만인데 변동금리에서 고정으로 바꾸면 대출 가능액이 얼마나 늘어나?",
        "answer": "고정이 변동보다 스트레스 가산이 없어서 대출 가능액이 더 많음. 고정이 1.3배 이상 유리.",
        "key_facts": ["고정이 변동보다 대출 가능액 많음", "스트레스 가산 차이가 원인"],
    },
    16: {
        "question": "서울 12억 아파트인데 9억 넘는 부분은 LTV가 다르게 적용된다며?",
        "answer": "9억까지 40% + 초과분(3억) 20% = 3.6억 + 0.6억 = 4.2억.",
        "key_facts": ["9억 이하 40%", "9억 초과 20%", "총 대출 한도 4.2억"],
    },
    17: {
        "question": "이미 집이 2채 있는데 서울에서 한 채 더 살 수 있어? 대출 가능해?",
        "answer": "다주택자는 규제지역(투기과열)에서 LTV 0% → 주택담보대출 불가.",
        "key_facts": ["다주택자 LTV 0%", "대출 불가", "규제지역"],
    },
    18: {
        "question": "연소득 8천만 이하 무주택인데 서민실수요자로 LTV 우대 받을 수 있어? 서울 7억이야.",
        "answer": "서민실수요자(부부합산 연소득 9천만 이하 무주택) LTV 70% 우대 → 4.9억.",
        "key_facts": ["서민실수요자 LTV 70%", "대출 한도 4.9억"],
    },
    19: {
        "question": "이미 신용대출 5천만(5%)이 있는데 DTI 계산할 때 이것도 포함돼? DSR이랑 뭐가 달라?",
        "answer": "DTI는 기타대출의 이자만 반영(5천만×5%=250만원/년). DSR은 원리금 전체를 포함해서 더 불리.",
        "key_facts": ["DTI는 이자만 반영", "연 250만원", "DSR은 원리금 전체 포함", "DSR이 더 엄격"],
    },
    20: {
        "question": "연소득 5천만이고 서울(투기과열)인데 DTI 기준으로 최대 얼마까지 대출 가능해?",
        "answer": "투기과열 서민실수요자 DTI 60% 적용. 연 상환 가능액 = 5천만 × 60% = 3천만원.",
        "key_facts": ["DTI 60%", "연 상환 가능 3천만원"],
    },
}

JUDGE_PROMPT = """당신은 한국 부동산 대출 전문가 평가자입니다.
AI 에이전트의 응답이 Ground Truth(정답)의 핵심 사실을 맞게 전달했는지 판정합니다.

## 평가 기준
- **PASS**: 응답이 key_facts의 핵심 수치/사실을 **대부분(2/3 이상)** 정확하게 포함하거나, 그에 근접한 설명을 함
  - 숫자는 ±5% 오차 허용 (예: 3.2억 vs 3.0억은 FAIL, 36.48% vs 36.50%는 PASS)
  - "은행에 문의하세요" 같은 회피 답변만 있고 구체적 수치가 없으면 FAIL
- **FAIL**: 핵심 수치가 틀리거나, 구체적 답변 없이 일반론만 제시

## 판정 입력

**질문:** {question}

**Ground Truth (정답):**
{answer}

**핵심 사실 (key_facts):**
{key_facts}

**AI 에이전트 응답:**
{response}

## 출력 형식 (JSON만 출력)
{{"verdict": "PASS" 또는 "FAIL", "score": 0~100, "matched_facts": ["매칭된 사실1", ...], "missed_facts": ["놓친 사실1", ...], "reason": "판정 근거 1~2문장"}}"""


def judge_response(qid: int, response: str) -> dict:
    gt = GROUND_TRUTH[qid]
    prompt = JUDGE_PROMPT.format(
        question=gt["question"],
        answer=gt["answer"],
        key_facts=json.dumps(gt["key_facts"], ensure_ascii=False),
        response=response,
    )

    result = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )

    return json.loads(result.choices[0].message.content)


def main():
    # DeepAgent 응답 로드
    results_path = Path(__file__).parent / "deepagent_results.json"
    if not results_path.exists():
        print("❌ deepagent_results.json이 없습니다. 먼저 test_deepagent_eval.py를 실행하세요.")
        sys.exit(1)

    responses = json.loads(results_path.read_text(encoding="utf-8"))

    print(f"=== LLM Judge 평가 (모델: {JUDGE_MODEL}) ===")
    print(f"DeepAgent 응답 {len(responses)}건 평가 중...\n")

    judgments = []
    pass_count = 0

    for resp in responses:
        qid = resp["id"]
        if resp["response"] is None:
            print(f"  [SKIP] #{qid} - 응답 없음 (오류)")
            judgments.append({"id": qid, "verdict": "ERROR", "score": 0, "reason": resp["error"]})
            continue

        print(f"  #{qid}: {resp['question'][:50]}...", end=" ", flush=True)
        judgment = judge_response(qid, resp["response"])
        verdict = judgment["verdict"]
        score = judgment.get("score", 0)

        if verdict == "PASS":
            pass_count += 1
            print(f"✅ PASS ({score}점)")
        else:
            print(f"❌ FAIL ({score}점) - {judgment.get('reason', '')[:60]}")

        judgments.append({"id": qid, "question": resp["question"], **judgment})

    total = len(responses)
    print(f"\n{'='*50}")
    print(f"결과: {pass_count}/{total} PASS ({pass_count/total*100:.0f}%)")
    avg_score = sum(j.get("score", 0) for j in judgments) / total
    print(f"평균 점수: {avg_score:.0f}/100")

    # JSON 저장
    out_json = Path(__file__).parent / "judge_results.json"
    out_json.write_text(json.dumps(judgments, ensure_ascii=False, indent=2), encoding="utf-8")

    # 마크다운 생성
    md_lines = [
        "# LLM Judge 평가 결과",
        "",
        f"**{pass_count}/{total} PASS** | 평균 점수: {avg_score:.0f}/100 | Judge: `{JUDGE_MODEL}` | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| # | 질문 | 판정 | 점수 | 사유 |",
        "|:-:|------|:----:|:----:|------|",
    ]

    for j in judgments:
        q = j.get("question", "")[:40] + "..." if len(j.get("question", "")) > 40 else j.get("question", "")
        v = "✅ PASS" if j["verdict"] == "PASS" else "❌ FAIL"
        reason = j.get("reason", "")[:60]
        md_lines.append(f"| {j['id']} | {q} | {v} | {j.get('score', 0)} | {reason} |")

    md_lines.extend(["", "---", ""])

    for j in judgments:
        md_lines.append(f"### #{j['id']} {j['verdict']}")
        md_lines.append(f"**점수:** {j.get('score', 0)}/100")
        md_lines.append("")
        if j.get("matched_facts"):
            md_lines.append(f"**맞은 사실:** {', '.join(j['matched_facts'])}")
        if j.get("missed_facts"):
            md_lines.append(f"**놓친 사실:** {', '.join(j['missed_facts'])}")
        if j.get("reason"):
            md_lines.append(f"**사유:** {j['reason']}")
        md_lines.append("")

    md_out = Path(__file__).parent / "JUDGE_RESULTS.md"
    md_out.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n저장: {out_json}")
    print(f"저장: {md_out}")


if __name__ == "__main__":
    main()
