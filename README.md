# 🏠 Korean Real Estate Loan Agent Skills

한국 부동산대출 규제·정책대출 AI 에이전트 스킬 모음

LLM 에이전트(LangChain DeepAgents, LangGraph 등)가 한국 부동산 대출 상담을 정확하게 수행할 수 있도록 하는 **도메인 스킬 패키지**입니다.

## 왜 필요한가?

한국 부동산대출 규제는 복잡합니다:
- **LTV/DTI/DSR** 세 가지 규제가 동시에 적용되어 가장 낮은 한도가 최종 한도
- **스트레스 가산금리** 3단계 (변동 +3.0%p, 혼합 +2.4%p, 고정 0%)로 금리유형에 따라 한도가 크게 달라짐
- **정책대출** (디딤돌, 보금자리론, 신생아 특례)은 각각 자격요건·금리·한도가 다름
- 규제지역 **절대한도** (15억↓ 6억, 25억↓ 4억), **9억 초과 차등 LTV** 등 예외 규칙 다수

LLM이 이런 규제를 hallucination 없이 정확하게 계산하려면 **검증된 계산 로직**과 **구조화된 도메인 지식**이 필요합니다.

## 스킬 구성

### 규제 계산기 (Python CLI 포함)

| 스킬 | 설명 |
|------|------|
| **dti-calculator** | DTI(총부채상환비율) 계산, 최대 대출 가능액 역산 |
| **dsr-calculator** | DSR 계산, 스트레스 가산금리 3단계 반영, 금리유형별 비교 |
| **ltv-calculator** | LTV 계산, 규제지역 절대한도, 9억 초과 차등 |
| **loan-affordability** | **종합** - LTV·DTI·DSR 동시 적용, 바인딩 규제 식별, 개선 시뮬레이션 |

### 정책대출 상품 가이드

| 스킬 | 설명 |
|------|------|
| **didimdol-loan** | 디딤돌대출 - 무주택 서민 저금리 (2.55%~) |
| **bogeumjari-loan** | 보금자리론 - 장기 고정금리 최대 50년 (4.05%~) |
| **newborn-purchase-loan** | 신생아 특례 구입 - 출산가구 초저금리 (1.80%~) |
| **beotimok-jeonse-loan** | 버팀목 전세 - 일반·청년·신혼 3종 |
| **newborn-jeonse-loan** | 신생아 특례 전세 - 출산가구 전세 (1.30%~) |
| **compare-products** | 대출 상품 비교 분석 |

## 설치

### 1. 스킬 다운로드

```bash
# 프로젝트 루트에서
git clone https://github.com/BancaKim/korean-loan-agent-skills.git

# 또는 기존 프로젝트의 skills/ 디렉토리에 직접 추가
cd your-project/
git clone https://github.com/BancaKim/korean-loan-agent-skills.git ./skills/korean-loan
```

### 2. DeepAgents 프로젝트에 통합

DeepAgents는 `skills` 파라미터에 **스킬 폴더들이 있는 디렉토리 경로**를 전달합니다.
이 레포의 `skills/` 폴더가 그 디렉토리입니다.

```
your-project/                          # 당신의 DeepAgents 프로젝트
├── app.py                             # 에이전트 코드
└── korean-loan-agent-skills/          # ← 이 레포를 클론
    ├── README.md
    ├── skills/                        # ← 이 경로를 skills 파라미터에 전달
    │   ├── dsr-calculator/
    │   │   ├── SKILL.md
    │   │   └── references/calculator.py
    │   ├── didimdol-loan/
    │   │   └── SKILL.md
    │   └── ...
    └── examples/
```

**핵심**: `create_deep_agent(skills=[...])` 에 전달하는 경로는 SKILL.md 파일들이 들어있는 **폴더들의 부모 디렉토리**여야 합니다.

## 빠른 시작

### 방법 1: FilesystemBackend (가장 간단)

```python
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

# 스킬 경로를 프로젝트 구조에 맞게 지정
SKILLS_PATH = "./korean-loan-agent-skills/skills/"

agent = create_deep_agent(
    model="claude-sonnet-4-20250514",
    backend=FilesystemBackend(root_dir="."),
    skills=[SKILLS_PATH],
    checkpointer=MemorySaver(),
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "연소득 6천만원인데 서울 7억 아파트 대출 얼마까지 가능해?"}]},
    config={"configurable": {"thread_id": "consult-1"}},
)
```

### 방법 2: StateBackend (스킬을 파일로 직접 전달)

```python
from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver

SKILLS_DIR = Path("./korean-loan-agent-skills/skills")

# 모든 SKILL.md + calculator.py를 files dict로 로드
skills_files = {}
for skill_dir in SKILLS_DIR.iterdir():
    if not skill_dir.is_dir():
        continue
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        key = f"/skills/{skill_dir.name}/SKILL.md"
        skills_files[key] = create_file_data(skill_md.read_text())
    refs = skill_dir / "references"
    if refs.exists():
        for f in refs.iterdir():
            key = f"/skills/{skill_dir.name}/references/{f.name}"
            skills_files[key] = create_file_data(f.read_text())

agent = create_deep_agent(
    skills=["/skills/"],
    checkpointer=MemorySaver(),
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "DSR 40% 넘으면 고정금리로 바꾸면 얼마나 나아져?"}]},
    "files": skills_files,
    config={"configurable": {"thread_id": "consult-1"}},
)
```

### 방법 3: StoreBackend (InMemoryStore)

서버리스 환경이나 원격 스킬 로딩에 적합합니다.
→ [`examples/store_backend_example.py`](examples/store_backend_example.py) 참조

### 에이전트 동작 흐름

위 코드로 에이전트에 "연소득 6천만원인데 서울 7억 아파트 대출 얼마까지 가능해?"를 물으면:

1. **Match** — `loan-affordability` 스킬의 description과 매칭
2. **Read** — SKILL.md 전체 로드, Workflow 단계 확인
3. **Execute** — `calculator.py calculate --annual-income 6000 --property-value 70000 ...` 실행
4. **Respond** — JSON 결과 해석 → "LTV 2.8억, DSR 2.9억 중 **LTV가 바인딩**, 생애최초면 +2.1억 가능" 안내

## 디렉토리 구조

```
skills/
├── AGENTS.md                          # 스킬 인덱스
├── dti-calculator/
│   ├── SKILL.md                       # 에이전트용 스킬 명세
│   └── references/
│       └── calculator.py              # DTI 계산 CLI
├── dsr-calculator/
│   ├── SKILL.md
│   └── references/
│       └── calculator.py              # DSR + 스트레스 가산 계산 CLI
├── ltv-calculator/
│   ├── SKILL.md
│   └── references/
│       └── calculator.py              # LTV + 절대한도 계산 CLI
├── loan-affordability/
│   ├── SKILL.md
│   └── references/
│       └── calculator.py              # 종합 (LTV+DTI+DSR) CLI
├── didimdol-loan/
│   └── SKILL.md                       # 디딤돌대출 가이드
├── bogeumjari-loan/
│   └── SKILL.md                       # 보금자리론 가이드
├── newborn-purchase-loan/
│   └── SKILL.md                       # 신생아 특례 구입
├── beotimok-jeonse-loan/
│   └── SKILL.md                       # 버팀목 전세
├── newborn-jeonse-loan/
│   └── SKILL.md                       # 신생아 특례 전세
└── compare-products/
    └── SKILL.md                       # 상품 비교
examples/
├── deepagent_example.py               # DeepAgents 통합 예시
└── store_backend_example.py           # StoreBackend 예시
```

## 스킬 작동 방식

[Agent Skills 스펙](https://docs.langchain.com/oss/python/deepagents/skills)을 따릅니다:

1. **Progressive Disclosure**: 에이전트는 먼저 각 SKILL.md의 frontmatter(`description`)만 읽어 매칭
2. **Match**: 사용자 질문과 관련된 스킬 선택 (예: "DSR 계산해줘" → `dsr-calculator`)
3. **Read**: 매칭된 스킬의 전체 SKILL.md 로드
4. **Execute**: Workflow에 따라 계산기 실행 또는 정보 제공

## 계산 정확도 검증 (Evaluation)

금감원 DSR 산정기준 + 금융위 가계부채 관리방안 기반 Ground Truth로 검증한 20건 evaluation set 결과입니다.

**20/20 통과** | Ground Truth: 금감원 DSR 산정기준 + 금융위 가계부채 관리방안 기반

| # | 질문 | 정답 | 계산 결과 | |
|:-:|------|------|:-------:|:-:|
| | **"대출 얼마나 받을 수 있어?" (종합 12건)** | | | |
| 1 | 맞벌이 연소득 1억이고 서울 8억 아파트 사려고 해. 무주택이고 생애최초 아니고 변동금리야. 대출 가능한 금액이 얼마야? | 담보 한도(LTV)에 걸려서 최대 **3.2억** | 3.2억 | **PASS** |
| 2 | 사회초년생인데 연소득 4천만이야. 서울 5억짜리 첫 집 사려고 하는데 변동금리 4.5% 30년이면 얼마까지 돼? | 소득 대비 상환 부담(DSR)에 걸려서 LTV보다 적게 나옴 | DSR 한도 적용 | **PASS** |
| 3 | 연소득 6천만이고 서울 7억 아파트 생애최초야. 고정금리로 받으면 변동보다 유리해? | 고정이라 스트레스 가산 없지만 그래도 소득 대비 상환 한도(DSR)가 **3.9억**으로 제일 적음 | DSR 3.9억 | **PASS** |
| 4 | 연소득 4천만이고 지방 3억짜리 아파트 보고 있어. 무주택이고 변동금리 4% 30년이면? | 지방이라 스트레스 가산이 0.75%p만 붙어서 수도권보다 유리 | 스트레스 4.75% | **PASS** |
| 5 | 연소득 8천만 무주택 서민실수요자야. 서울 15억짜리 아파트 대출 한도가 얼마야? | LTV 70%면 10.5억인데 **절대한도 6억**이 적용돼서 최대 6억 | 6억 | **PASS** |
| 6 | 연소득 8천만인데 이미 주담대 1억(3.5%)이랑 신용대출 3천만(5%)이 있어. 서울 9억 아파트 추가 대출 받을 수 있어? | 기존 대출 때문에 갚을 수 있는 여유가 크게 줄어서 **1.9억**밖에 안 됨 | 1.9억 | **PASS** |
| 7 | 연소득 6천만이고 지방(비규제) 4억 아파트 생애최초야. 고정금리 3.5% 30년이면? | 비규제라 LTV 80%, 고정이라 스트레스 0% → 담보 한도 **3.2억** | 3.2억 | **PASS** |
| 8 | 연소득 5천만인데 1금융 안 되면 2금융(저축은행)은? 서울 6억 변동 5.5%야. | 2금융은 DSR 한도가 50%라 1금융(40%)보다 여유 있음 | DSR 50% 적용 | **PASS** |
| 9 | 연소득 2억이고 서울 25억 아파트 생애최초로 사려는데. 고정금리야. 얼마까지 돼? | LTV 70%면 17.5억이지만 **25억 초과 절대한도 4억**이 적용 | 4억 | **PASS** |
| 10 | 연소득 7천만이고 서울 8억 생애최초야. 혼합형 10년 고정금리 4.5%면 스트레스가 얼마나 붙어? | 혼합10년은 스트레스 60% 적용 → 4.5% + 1.8% = **6.3%**로 계산 | 6.3% | **PASS** |
| 11 | 연소득 3천만이고 지방 소도시 2억짜리 아파트야. 고정금리 3.8% 20년이면? | 비규제 LTV 70% = **1.4억** | 1.4억 | **PASS** |
| 12 | 연소득 1.2억인데 이미 집이 한 채 있어. 서울 10억짜리로 갈아타려고 기존 집 처분 조건으로 대출 받으면? | 1주택 처분조건 LTV 50% = **5억**이 제일 적어서 최대 5억 | 5억 | **PASS** |
| | **"DSR이 몇 %야?" (3건)** | | | |
| 13 | 연소득 5천만인데 3억 대출 고정금리 4.5% 30년으로 받으면 DSR이 몇 퍼센트야? | 고정이라 스트레스 가산 없이 **36.48%** → 40% 이하라 통과 | 36.48% | **PASS** |
| 14 | 같은 조건인데 변동금리로 바꾸면? 스트레스 금리가 붙는다던데. | 변동이라 +3.0%p 붙어서 7.5%로 계산 → **50.34%** → 40% 초과라 안 됨 | 50.34% | **PASS** |
| 15 | 연소득 5천만인데 변동금리에서 고정으로 바꾸면 대출 가능액이 얼마나 늘어나? | 고정이 변동보다 **1.3배 이상** 더 받을 수 있음 | 비교표 포함 | **PASS** |
| | **"담보 대비 얼마까지 돼?" (LTV 3건)** | | | |
| 16 | 서울 12억 아파트인데 9억 넘는 부분은 LTV가 다르게 적용된다며? | 9억까지 40% + 초과분 20% → **4.2억** | 4.2억 | **PASS** |
| 17 | 이미 집이 2채 있는데 서울에서 한 채 더 살 수 있어? 대출 가능해? | 다주택자는 규제지역에서 LTV 0% → **대출 불가** | 불가 | **PASS** |
| 18 | 연소득 8천만 이하 무주택인데 서민실수요자로 LTV 우대 받을 수 있어? 서울 7억이야. | 서민실수요자는 LTV 70% 적용 → **4.9억** | 4.9억 | **PASS** |
| | **"DTI는 어떻게 계산돼?" (2건)** | | | |
| 19 | 이미 신용대출 5천만(5%)이 있는데 DTI 계산할 때 이것도 포함돼? DSR이랑 뭐가 달라? | DTI는 신용대출의 **이자만** 반영(250만/년). DSR은 원리금 전체 포함이라 더 불리함 | 250만/년 | **PASS** |
| 20 | 연소득 5천만이고 서울(투기과열)인데 DTI 기준으로 최대 얼마까지 대출 가능해? | 서민 실수요자 DTI 60% 적용 | 60% 적용 | **PASS** |

> 상세 결과: [`tests/EVAL_RESULTS.md`](tests/EVAL_RESULTS.md) | 테스트 스크립트: [`tests/eval_scenarios.py`](tests/eval_scenarios.py)

## DeepAgent 실제 응답 테스트

`create_deep_agent()`에 스킬을 로드한 후 자연어 질문 20건을 넣어 실제 응답을 기록한 결과입니다.

**3/20 PASS (15%)** | 평균 점수: 29/100 | 모델: `gpt-4o` | Judge: `gpt-4o` | 평균 응답: 6초

> **평가 방법**: Ground Truth(정답)의 핵심 수치/사실을 LLM Judge가 응답과 비교하여 PASS/FAIL 자동 판정.
> 핵심 사실의 2/3 이상을 정확히 전달해야 PASS. 수치는 ±5% 오차 허용.

| # | 질문 (자연어) | 판정 | 점수 | 사유 |
|:-:|-------------|:----:|:----:|------|
| 1 | 맞벌이 연소득 1억, 서울 8억, 무주택, 변동금리 | ✅ PASS | 80 | LTV 40%, 3.2억 정확 |
| 2 | 연소득 4천만, 서울 5억 첫 집, 변동 4.5% 30년 | ❌ FAIL | 0 | 월 상환액만 계산, LTV/DSR 미언급 |
| 3 | 연소득 6천만, 서울 7억 생애최초, 고정 vs 변동 | ❌ FAIL | 0 | 스트레스 가산금리 미언급, 일반론만 |
| 4 | 연소득 4천만, 지방 3억, 변동 4% 30년 | ❌ FAIL | 0 | LTV/스트레스 가산 미언급 |
| 5 | 연소득 8천만 서민실수요자, 서울 15억 | ❌ FAIL | 33 | 6억 언급했으나 서민실수요 LTV 70% 미설명 |
| 6 | 기존대출 1.3억 보유, 서울 9억 추가대출 | ❌ FAIL | 40 | DSR 개념 언급했으나 구체 한도 미제시 |
| 7 | 연소득 6천만, 지방 비규제 4억 생애최초 고정 3.5% | ❌ FAIL | 0 | 월 상환액만 계산, LTV 80% 미언급 |
| 8 | 연소득 5천만, 2금융(저축은행) 가능성 | ❌ FAIL | 0 | 2금융 DSR 50% 미언급, 일반론만 |
| 9 | 연소득 2억, 서울 25억 생애최초 고정 | ❌ FAIL | 0 | 절대한도 4억 미언급 |
| 10 | 연소득 7천만, 서울 8억 생애최초 혼합10년 | ❌ FAIL | 0 | 스트레스 60%, 6.3% 미언급 |
| 11 | 연소득 3천만, 지방 2억 고정 3.8% 20년 | ❌ FAIL | 0 | LTV 70%, 1.4억 미언급 |
| 12 | 연소득 1.2억, 1주택 처분조건 갈아타기 | ❌ FAIL | 33 | 처분조건 언급했으나 LTV 50%, 5억 부정확 |
| 13 | 연소득 5천만, 3억 고정 4.5% 30년 DSR | ✅ PASS | 100 | **DSR 36.50%** 정확 (정답 36.48%) |
| 14 | 같은 조건 변동금리로 바꾸면? | ❌ FAIL | 0 | +3.0%p, 7.5%, 50.34% 미언급 |
| 15 | 변동→고정 대출가능액 차이 | ❌ FAIL | 20 | 고정 유리 언급했으나 구체 수치 없음 |
| 16 | 서울 12억 9억 초과 차등 LTV | ✅ PASS | 100 | 40%/20% → **4.2억** 완벽 정확 |
| 17 | 다주택자 서울 추가 매수 가능? | ❌ FAIL | 33 | 규제 언급했으나 LTV 0% 명시 안 함 |
| 18 | 서민실수요자 LTV 우대 가능? 서울 7억 | ❌ FAIL | 50 | LTV 70% 언급했으나 4.9억 미산출 |
| 19 | 신용대출 DTI 포함 여부, DSR 차이 | ❌ FAIL | 50 | DTI/DSR 차이 설명했으나 250만원 미언급 |
| 20 | 연소득 5천만 투기과열 DTI 최대 대출 | ❌ FAIL | 50 | DTI 40% 가정 (정답 60%) |

### 분석

**PASS한 3건**은 모델의 사전 지식(LTV 40%, 9억 차등)이나 계산기 CLI 실행(#13 DSR)으로 정확한 수치를 제시한 경우입니다.

**FAIL한 17건**의 주요 패턴:
- 🔴 **계산기 미호출 (12건)**: 스킬의 calculator.py를 실행하지 않고 일반 지식으로 답변
- 🟡 **부분 정확 (5건)**: 개념은 맞지만 구체적 수치가 부정확하거나 누락

> **시사점**: 현재 DeepAgents + gpt-4o 조합에서는 스킬의 계산기 CLI를 적극 호출하지 않는 경향이 있습니다.
> SKILL.md의 Workflow 지시를 더 명확하게 하거나, 모델의 tool-use 능력이 향상되면 정확도가 크게 개선될 것으로 예상됩니다.

> 상세 결과: [`tests/DEEPAGENT_RESULTS.md`](tests/DEEPAGENT_RESULTS.md) | 테스트 스크립트: [`tests/test_deepagent_eval.py`](tests/test_deepagent_eval.py)

### 검증 방법

- **DSR**: 금감원 DSR 산정기준(원리금균등 공식, 스트레스 3단계) 기반 수학적 검증
- **LTV**: 금융위 2025.10.15 대책 규정 (절대한도, 9억 차등, 서민실수요 70%, 다주택 0%)
- **종합**: LTV·DTI·DSR 각각 계산 후 가장 적은 금액이 실제 한도
- **DTI**: 신DTI 산정기준 (기타대출 이자만 반영, DSR과의 핵심 차이 검증)

## 반영된 규제 기준

| 규제 | 기준일 | 내용 |
|------|--------|------|
| 가계부채 관리방안 | 2025.10.15 | 규제지역 재지정, 절대한도 |
| 스트레스 DSR 3단계 | 2025.7.1 | 수도권 +3.0%p, 지방 +0.75%p |
| 신생아 특례 확대 | 2025.6.27 | 전세 한도 3억 상향 |
| 정책대출 금리 | 2026.03 | 디딤돌·보금자리론 최신 금리 |

## 기여하기

- 규제 변경 시 SKILL.md 및 calculator.py 상수 업데이트
- 새로운 대출 상품 추가 시 스킬 폴더 생성 (SKILL.md 필수)
- 계산기 정확도 검증 (은행 심사 결과 대조) 환영

## License

MIT
