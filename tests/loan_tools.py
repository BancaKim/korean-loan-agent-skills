"""
호환성 래퍼 — 루트 tools.py로 이전됨.
기존 코드에서 `from loan_tools import get_all_tools`를 사용하는 경우 호환.

도구 정의는 각 스킬의 references/tools.py에 있습니다:
  - skills/ltv-calculator/references/tools.py
  - skills/dti-calculator/references/tools.py
  - skills/dsr-calculator/references/tools.py
  - skills/loan-affordability/references/tools.py

수집기: tools.py (프로젝트 루트)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools import get_all_tools  # noqa: F401, E402

if __name__ == "__main__":
    tools = get_all_tools()
    for t in tools:
        print(f"  ✅ {t.name}")
    print(f"\n총 {len(tools)}개 도구")
