"""
Korean Real Estate Loan Skills - DeepAgents Integration Example

LangChain DeepAgents에서 한국 부동산대출 스킬을 사용하는 예시.
skills/ 폴더를 에이전트에 등록하면, 대출 관련 질문 시 자동으로 매칭되어
계산기 실행 및 상품 안내를 수행합니다.

Usage:
    pip install deepagents
    python deepagent_example.py
"""

from pathlib import Path
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

# 스킬 디렉토리 경로
SKILLS_DIR = str(Path(__file__).parent.parent / "skills")

# 에이전트 생성
checkpointer = MemorySaver()

agent = create_deep_agent(
    model="claude-sonnet-4-20250514",
    skills=[f"{SKILLS_DIR}/"],
    checkpointer=checkpointer,
)


def ask(question: str, thread_id: str = "loan-consult-1"):
    """에이전트에 질문하기"""
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1]["content"]


if __name__ == "__main__":
    # 예시 1: 대출 가능액 질문 → loan-affordability 스킬 매칭
    print("=" * 60)
    print("질문: 연소득 6천만원인데 서울 7억 아파트 대출 얼마나 가능해?")
    print("=" * 60)
    answer = ask("연소득 6천만원인데 서울 7억 아파트 대출 얼마까지 가능해? 변동금리 4.5% 30년으로 알아봐줘")
    print(answer)

    # 예시 2: 상품 비교 → compare-products + didimdol + bogeumjari 스킬 매칭
    print("\n" + "=" * 60)
    print("질문: 디딤돌 vs 보금자리론 뭐가 유리해?")
    print("=" * 60)
    answer = ask(
        "연소득 5천만원, 무주택, 4.5억 아파트 사려는데 디딤돌이랑 보금자리론 중에 뭐가 유리해?",
        thread_id="loan-consult-2",
    )
    print(answer)

    # 예시 3: 신생아 특례 → newborn-purchase-loan 스킬 매칭
    print("\n" + "=" * 60)
    print("질문: 작년에 아이 낳았는데 대출 혜택 있어?")
    print("=" * 60)
    answer = ask(
        "작년에 아이 낳았는데 주택 구입 대출 혜택 있어? 부부합산 소득 9천만원이야",
        thread_id="loan-consult-3",
    )
    print(answer)
