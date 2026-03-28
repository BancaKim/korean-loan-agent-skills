#!/usr/bin/env python3
"""
DeepAgent 실제 응답 테스트
자연어 질문을 create_deep_agent()에 넣어서 실제 응답을 기록합니다.

Usage:
    .venv/bin/python tests/test_deepagent_eval.py          # 전체 20건
    .venv/bin/python tests/test_deepagent_eval.py --quick   # 핵심 5건만
"""

from __future__ import annotations
import os
import sys
import time
import json
import shutil
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from deepagents import create_deep_agent
from deepagents.backends.local_shell import LocalShellBackend
from langgraph.checkpoint.memory import MemorySaver

PROJECT_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = str(PROJECT_DIR / "skills")
MODEL = os.environ.get("TEST_MODEL", "gpt-4o-mini")

QUESTIONS = [
    {"id": 1, "q": "맞벌이 연소득 1억이고 서울 8억 아파트 사려고 해. 무주택이고 생애최초 아니고 변동금리야. 대출 가능한 금액이 얼마야?"},
    {"id": 2, "q": "사회초년생인데 연소득 4천만이야. 서울 5억짜리 첫 집 사려고 하는데 변동금리 4.5% 30년이면 얼마까지 돼?"},
    {"id": 3, "q": "연소득 6천만이고 서울 7억 아파트 생애최초야. 고정금리로 받으면 변동보다 유리해?"},
    {"id": 4, "q": "연소득 4천만이고 지방 3억짜리 아파트 보고 있어. 무주택이고 변동금리 4% 30년이면?"},
    {"id": 5, "q": "연소득 8천만 무주택 서민실수요자야. 서울 15억짜리 아파트 대출 한도가 얼마야?"},
    {"id": 6, "q": "연소득 8천만인데 이미 주담대 1억(3.5%)이랑 신용대출 3천만(5%)이 있어. 서울 9억 아파트 추가 대출 받을 수 있어?"},
    {"id": 7, "q": "연소득 6천만이고 지방(비규제) 4억 아파트 생애최초야. 고정금리 3.5% 30년이면?"},
    {"id": 8, "q": "연소득 5천만인데 1금융 안 되면 2금융(저축은행)은? 서울 6억 변동 5.5%야."},
    {"id": 9, "q": "연소득 2억이고 서울 25억 아파트 생애최초로 사려는데. 고정금리야. 얼마까지 돼?"},
    {"id": 10, "q": "연소득 7천만이고 서울 8억 생애최초야. 혼합형 10년 고정금리 4.5%면 스트레스가 얼마나 붙어?"},
    {"id": 11, "q": "연소득 3천만이고 지방 소도시 2억짜리 아파트야. 고정금리 3.8% 20년이면?"},
    {"id": 12, "q": "연소득 1.2억인데 이미 집이 한 채 있어. 서울 10억짜리로 갈아타려고 기존 집 처분 조건으로 대출 받으면?"},
    {"id": 13, "q": "연소득 5천만인데 3억 대출 고정금리 4.5% 30년으로 받으면 DSR이 몇 퍼센트야?"},
    {"id": 14, "q": "같은 조건인데 변동금리로 바꾸면? 스트레스 금리가 붙는다던데."},
    {"id": 15, "q": "연소득 5천만인데 변동금리에서 고정으로 바꾸면 대출 가능액이 얼마나 늘어나?"},
    {"id": 16, "q": "서울 12억 아파트인데 9억 넘는 부분은 LTV가 다르게 적용된다며?"},
    {"id": 17, "q": "이미 집이 2채 있는데 서울에서 한 채 더 살 수 있어? 대출 가능해?"},
    {"id": 18, "q": "연소득 8천만 이하 무주택인데 서민실수요자로 LTV 우대 받을 수 있어? 서울 7억이야."},
    {"id": 19, "q": "이미 신용대출 5천만(5%)이 있는데 DTI 계산할 때 이것도 포함돼? DSR이랑 뭐가 달라?"},
    {"id": 20, "q": "연소득 5천만이고 서울(투기과열)인데 DTI 기준으로 최대 얼마까지 대출 가능해?"},
]

# --quick 모드용 핵심 5건 (다양한 계산기 커버)
QUICK_IDS = {1, 5, 13, 16, 17}


def create_agent():
    return create_deep_agent(
        model=MODEL,
        backend=LocalShellBackend(
            root_dir=str(PROJECT_DIR),
            inherit_env=True,    # Python PATH 상속 (계산기 CLI 실행에 필수)
            timeout=60,          # 계산기 실행 타임아웃
        ),
        skills=[f"{SKILLS_DIR}/"],
        checkpointer=MemorySaver(),
    )


def run_questions(questions):
    print(f"=== DeepAgent 실제 응답 테스트 ({len(questions)}건) ===")
    print(f"모델: {MODEL}\n")

    agent = create_agent()
    results = []

    for i, item in enumerate(questions):
        tid = f"eval-{item['id']}-{int(time.time())}"
        print(f"[{i+1}/{len(questions)}] #{item['id']}: {item['q'][:50]}...")

        start = time.time()
        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": item["q"]}]},
                config={"configurable": {"thread_id": tid}},
            )
            elapsed = time.time() - start
            response = result["messages"][-1].content
            print(f"  ✅ 완료 ({elapsed:.0f}s)")
            results.append({"id": item["id"], "question": item["q"],
                           "response": response, "elapsed": round(elapsed, 1), "error": None})
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ❌ 오류 ({elapsed:.0f}s): {e}")
            results.append({"id": item["id"], "question": item["q"],
                           "response": None, "elapsed": round(elapsed, 1), "error": str(e)})

    return results


def generate_md(results):
    total = len(results)
    success = sum(1 for r in results if r["response"])
    avg_time = sum(r["elapsed"] for r in results) / total

    lines = [
        f"# DeepAgent 실제 응답 테스트 결과",
        f"",
        f"**{success}/{total} 응답 성공** | 모델: `{MODEL}` | 평균 응답: {avg_time:.0f}초 | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
    ]

    for r in results:
        lines.append(f"### #{r['id']}")
        lines.append(f"**질문:** {r['question']}")
        lines.append(f"")
        if r["response"]:
            lines.append(f"**응답 ({r['elapsed']}s):**")
            lines.append(f"")
            for line in r["response"].split("\n"):
                lines.append(f"> {line}")
        else:
            lines.append(f"**오류:** {r['error']}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

    return "\n".join(lines)


if __name__ == "__main__":
    quick = "--quick" in sys.argv

    if quick:
        questions = [q for q in QUESTIONS if q["id"] in QUICK_IDS]
        print("🚀 Quick 모드: 핵심 5건만 테스트\n")
    else:
        questions = QUESTIONS

    results = run_questions(questions)

    success = sum(1 for r in results if r["response"])
    print(f"\n{'='*50}")
    print(f"응답 성공: {success}/{len(results)}")

    # JSON으로도 저장
    json_out = Path(__file__).parent / "deepagent_results.json"
    json_out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON 저장: {json_out}")

    # 마크다운 저장
    md = generate_md(results)
    md_out = Path(__file__).parent / "DEEPAGENT_RESULTS.md"
    md_out.write_text(md, encoding="utf-8")
    print(f"MD 저장: {md_out}")
