"""
한국 부동산 대출 계산기 - LangChain Tools 모음
각 스킬의 references/calculator.py에서 @tool 도구를 수집하여 제공합니다.

Usage:
    from tools import get_all_tools

    agent = create_deep_agent(
        model="gpt-4o",
        tools=get_all_tools(),
        skills=["./skills/"],
    )
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_skills_dir = Path(__file__).resolve().parent / "skills"

_SKILL_FOLDERS = [
    "ltv-calculator",
    "dti-calculator",
    "dsr-calculator",
    "loan-affordability",
]


def _import_calculator(skill_folder: str):
    """하이픈 폴더의 calculator.py를 import"""
    module_name = f"_skill_{skill_folder.replace('-', '_')}_calc"
    module_path = _skills_dir / skill_folder / "references" / "calculator.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def get_all_tools() -> list:
    """모든 스킬의 LangChain Tool을 수집하여 반환 (6개)"""
    all_tools = []
    for folder in _SKILL_FOLDERS:
        mod = _import_calculator(folder)
        all_tools.extend(mod.get_tools())
    return all_tools


if __name__ == "__main__":
    print("=== 대출 계산기 Tool 로드 테스트 ===\n")
    tools = get_all_tools()
    for t in tools:
        print(f"  ✅ {t.name}")
    print(f"\n총 {len(tools)}개 도구 로드 완료")
