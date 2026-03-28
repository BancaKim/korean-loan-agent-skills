"""
StoreBackend Example - 스킬을 InMemoryStore에 로드하여 사용

FilesystemBackend 없이 스킬 파일을 직접 메모리에 올려서 사용하는 예시.
서버리스 환경이나 원격 스킬 로딩에 유용합니다.
"""

from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

SKILLS_DIR = Path(__file__).parent.parent / "skills"


def load_skills_to_store(store: InMemoryStore, skills_dir: Path):
    """스킬 디렉토리의 모든 SKILL.md를 스토어에 로드"""
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        # SKILL.md 로드
        key = f"/skills/{skill_dir.name}/SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        store.put(
            namespace=("filesystem",),
            key=key,
            value=create_file_data(content),
        )
        print(f"  Loaded: {key}")

        # references/ 하위 파일 로드
        refs_dir = skill_dir / "references"
        if refs_dir.exists():
            for ref_file in refs_dir.iterdir():
                if ref_file.is_file():
                    ref_key = f"/skills/{skill_dir.name}/references/{ref_file.name}"
                    ref_content = ref_file.read_text(encoding="utf-8")
                    store.put(
                        namespace=("filesystem",),
                        key=ref_key,
                        value=create_file_data(ref_content),
                    )
                    print(f"  Loaded: {ref_key}")


if __name__ == "__main__":
    store = InMemoryStore()

    print("Loading skills...")
    load_skills_to_store(store, SKILLS_DIR)

    agent = create_deep_agent(
        model="claude-sonnet-4-20250514",
        backend=(lambda rt: StoreBackend(rt)),
        store=store,
        skills=["/skills/"],
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "DSR이 뭐야? 연소득 5천만원에 3억 변동금리 4.5% 30년이면 DSR 통과해?",
                }
            ]
        },
        config={"configurable": {"thread_id": "dsr-test"}},
    )

    print("\n" + "=" * 60)
    print(result["messages"][-1]["content"])
