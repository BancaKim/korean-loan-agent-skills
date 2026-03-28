"""
한국 부동산 대출 계산기 - LangChain Tools 모음
각 스킬의 references/tools.py에서 도구를 수집하여 제공합니다.

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

# 하이픈이 포함된 폴더명 → importlib로 import
_SKILL_FOLDERS = [
    "ltv-calculator",
    "dti-calculator",
    "dsr-calculator",
    "loan-affordability",
]


def _import_tools(skill_folder: str):
    """스킬 폴더의 references/tools.py를 import"""
    # references 패키지의 __init__.py 먼저 로드
    refs_dir = _skills_dir / skill_folder / "references"
    pkg_name = f"_skill_{skill_folder.replace('-', '_')}_refs"

    init_path = refs_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(pkg_name, init_path, submodule_search_locations=[str(refs_dir)])
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = pkg
    spec.loader.exec_module(pkg)

    # calculator.py 로드
    calc_name = f"{pkg_name}.calculator"
    calc_path = refs_dir / "calculator.py"
    calc_spec = importlib.util.spec_from_file_location(calc_name, calc_path)
    calc_mod = importlib.util.module_from_spec(calc_spec)
    sys.modules[calc_name] = calc_mod
    calc_spec.loader.exec_module(calc_mod)

    # tools.py 로드
    tools_name = f"{pkg_name}.tools"
    tools_path = refs_dir / "tools.py"
    tools_spec = importlib.util.spec_from_file_location(tools_name, tools_path)
    tools_mod = importlib.util.module_from_spec(tools_spec)
    sys.modules[tools_name] = tools_mod
    tools_spec.loader.exec_module(tools_mod)

    return tools_mod


def get_all_tools() -> list:
    """모든 스킬의 LangChain Tool을 수집하여 반환 (6개)"""
    all_tools = []
    for folder in _SKILL_FOLDERS:
        mod = _import_tools(folder)
        all_tools.extend(mod.get_tools())
    return all_tools


if __name__ == "__main__":
    print("=== 대출 계산기 Tool 로드 테스트 ===\n")
    tools = get_all_tools()
    for t in tools:
        print(f"  ✅ {t.name}")
    print(f"\n총 {len(tools)}개 도구 로드 완료")
