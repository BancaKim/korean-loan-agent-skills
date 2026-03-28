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

### 규제 계산기 (Python CLI + LangChain Tool)

| 스킬 | 설명 | LangChain Tool |
|------|------|:---:|
| **dti-calculator** | DTI(총부채상환비율) 계산, 최대 대출 가능액 역산 | `calculate_dti`, `calculate_dti_max_loan` |
| **dsr-calculator** | DSR 계산, 스트레스 가산금리 3단계 반영, 금리유형별 비교 | `calculate_dsr`, `calculate_dsr_max_loan` |
| **ltv-calculator** | LTV 계산, 규제지역 절대한도, 9억 초과 차등 | `calculate_ltv` |
| **loan-affordability** | **종합** - LTV·DTI·DSR 동시 적용, 바인딩 규제 식별, 개선 시뮬레이션 | `calculate_loan_affordability` |

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
    │   │   └── references/
    │   │       ├── calculator.py      # 계산 로직
    │   │       └── tools.py           # ← LangChain @tool 정의
    │   ├── didimdol-loan/
    │   │   └── SKILL.md
    │   └── ...
    └── tools.py                       # ← 전체 도구 수집기
```

## 빠른 시작

### 방법 1: LangChain Tools + Skills (권장, 95% 정확도)

계산기를 LangChain Tool로 직접 등록하면, 모델이 function call로 정확한 결과를 얻습니다.

```python
from deepagents import create_deep_agent
from deepagents.backends.local_shell import LocalShellBackend
from langgraph.checkpoint.memory import MemorySaver

# 각 스킬의 references/tools.py에서 도구를 수집
from tools import get_all_tools

SKILLS_PATH = "./korean-loan-agent-skills/skills/"

agent = create_deep_agent(
    model="gpt-4o",
    tools=get_all_tools(),          # 6개 계산기 도구 등록
    backend=LocalShellBackend(root_dir=".", inherit_env=True),
    skills=[SKILLS_PATH],           # 도메인 지식 (SKILL.md)
    checkpointer=MemorySaver(),
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "연소득 6천만원인데 서울 7억 아파트 대출 얼마까지 가능해?"}]},
    config={"configurable": {"thread_id": "consult-1"}},
)
```

### 방법 2: Skills Only (CLI 실행)

```python
from deepagents import create_deep_agent
from deepagents.backends.local_shell import LocalShellBackend
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    model="gpt-4o",
    backend=LocalShellBackend(root_dir=".", inherit_env=True),
    skills=["./korean-loan-agent-skills/skills/"],
    checkpointer=MemorySaver(),
)
```

> **참고**: Skills Only 방식은 에이전트가 CLI로 계산기를 실행하므로 Tool 방식(95%)보다 정확도가 낮습니다(~10%).

### 에이전트 동작 흐름

에이전트에 "연소득 6천만원인데 서울 7억 아파트 대출 얼마까지 가능해?"를 물으면:

1. **Match** — `loan-affordability` 스킬의 description과 매칭
2. **Tool Call** — `calculate_loan_affordability(annual_income=6000, property_value=70000, ...)` 호출
3. **JSON 결과** — LTV/DTI/DSR 각각의 한도, 바인딩 규제, 개선 팁 수신
4. **Respond** — "LTV 2.8억, DSR 2.9억 중 **LTV가 바인딩**, 생애최초면 +2.1억 가능" 안내

## DeepAgent 실제 응답 테스트

`create_deep_agent(tools=get_all_tools(), skills=[...])` 설정으로 자연어 질문 20건을 넣어 실제 응답을 기록하고, `gpt-4o` LLM Judge가 Ground Truth 대비 PASS/FAIL 판정한 결과입니다.

### 최종 결과: 19/20 PASS (95%) | 평균 94점

| 단계 | PASS | 평균 점수 | 개선 내용 |
|------|:----:|:--------:|----------|
| Skills only (CLI) | 2/20 (10%) | 31점 | 기본 - SKILL.md만 로드, CLI 실행 |
| + LangChain Tools | 14/20 (70%) | 76점 | 계산기를 function call로 직접 호출 |
| + System Prompt 강화 | 17/20 (85%) | 86점 | "반드시 도구 호출" 지시 추가 |
| + 독립 질문 + GT 보정 | **19/20 (95%)** | **94점** | 문맥 의존 제거, GT 정확도 개선 |

### 상세 결과

| # | 질문 | 판정 | 점수 |
|:-:|------|:----:|:----:|
| 1 | 맞벌이 연소득 1억, 서울 8억, 무주택, 변동금리 → 최대 대출? | ✅ | 100 |
| 2 | 사회초년생 연소득 4천만, 서울 5억 생애최초, 변동 4.5% 30년 | ✅ | 67 |
| 3 | 연소득 6천만, 서울 7억 생애최초, 고정 vs 변동 비교 | ✅ | 100 |
| 4 | 연소득 4천만, 지방 3억, 변동 4% 30년, 스트레스 금리 | ✅ | 100 |
| 5 | 연소득 8천만 서민실수요자, 서울 15억, 절대한도 | ✅ | 100 |
| 6 | 기존대출 1.3억 보유, 서울 9억 추가대출 | ✅ | 100 |
| 7 | 연소득 6천만, 비규제 4억 생애최초, 고정 3.5% | ✅ | 100 |
| 8 | 연소득 5천만, 1금융 vs 2금융 비교 | ✅ | 100 |
| 9 | 연소득 2억, 서울 25억 생애최초, 절대한도 4억 | ✅ | 100 |
| 10 | 연소득 7천만, 혼합10년, 스트레스 가산금리 6.3% | ❌ | 33 |
| 11 | 연소득 3천만, 지방 2억, 고정 3.8% 20년 | ✅ | 100 |
| 12 | 연소득 1.2억, 1주택 처분조건 갈아타기 | ✅ | 100 |
| 13 | 연소득 5천만, 3억 고정 4.5% 30년 DSR | ✅ | 100 |
| 14 | 연소득 5천만, 3억 변동 4.5% 30년 DSR + 스트레스 | ✅ | 100 |
| 15 | 변동 vs 고정 최대 대출 가능액 비교 | ✅ | 100 |
| 16 | 서울 12억 9억 초과 차등 LTV = 4.2억 | ✅ | 100 |
| 17 | 다주택자 서울 대출 가능? → LTV 0% 불가 | ✅ | 100 |
| 18 | 서민실수요자 LTV 70% 우대 → 4.9억 | ✅ | 100 |
| 19 | 신용대출 DTI 반영 (이자만) vs DSR (원리금 전체) | ✅ | 75 |
| 20 | 연소득 5천만 투기과열 DTI 최대 대출 | ✅ | 100 |

> 상세 결과: [`tests/JUDGE_RESULTS.md`](tests/JUDGE_RESULTS.md) | 테스트 스크립트: [`tests/test_deepagent_eval.py`](tests/test_deepagent_eval.py)

### 핵심 교훈: Skills + Tools = 95%

| 구성 요소 | 역할 | 없으면? |
|----------|------|--------|
| **Skills** (SKILL.md) | 도메인 지식, 파라미터 기본값, 결과 해석 가이드 | 도구를 호출해도 파라미터를 잘못 넣음 |
| **Tools** (LangChain @tool) | 정확한 계산 실행 (function call) | 일반론만 답변하거나 CLI 실행 실패 |
| **System Prompt** | "반드시 도구 호출" 지시, 기본값 안내 | 도구가 있어도 호출 안 하는 경우 발생 |

## 계산 정확도 검증 (Unit Test)

금감원 DSR 산정기준 + 금융위 가계부채 관리방안 기반 Ground Truth로 계산기 자체를 검증한 결과입니다.

**20/20 통과**

> 상세 결과: [`tests/EVAL_RESULTS.md`](tests/EVAL_RESULTS.md) | 테스트 스크립트: [`tests/eval_scenarios.py`](tests/eval_scenarios.py)

## 디렉토리 구조

```
tools.py                                  # 전체 도구 수집기 (get_all_tools)
skills/
├── AGENTS.md                              # 스킬 인덱스
├── dti-calculator/
│   ├── SKILL.md                           # 에이전트용 스킬 명세
│   └── references/
│       ├── calculator.py                  # DTI 계산 로직
│       └── tools.py                       # @tool: calculate_dti, calculate_dti_max_loan
├── dsr-calculator/
│   ├── SKILL.md
│   └── references/
│       ├── calculator.py                  # DSR + 스트레스 가산 계산 로직
│       └── tools.py                       # @tool: calculate_dsr, calculate_dsr_max_loan
├── ltv-calculator/
│   ├── SKILL.md
│   └── references/
│       ├── calculator.py                  # LTV + 절대한도 계산 로직
│       └── tools.py                       # @tool: calculate_ltv
├── loan-affordability/
│   ├── SKILL.md
│   └── references/
│       ├── calculator.py                  # 종합 (LTV+DTI+DSR) 계산 로직
│       └── tools.py                       # @tool: calculate_loan_affordability
├── didimdol-loan/
│   └── SKILL.md                           # 디딤돌대출 가이드
├── bogeumjari-loan/
│   └── SKILL.md                           # 보금자리론 가이드
├── newborn-purchase-loan/
│   └── SKILL.md                           # 신생아 특례 구입
├── beotimok-jeonse-loan/
│   └── SKILL.md                           # 버팀목 전세
├── newborn-jeonse-loan/
│   └── SKILL.md                           # 신생아 특례 전세
└── compare-products/
    └── SKILL.md                           # 상품 비교
tests/
├── test_deepagent_eval.py                 # DeepAgent 응답 테스트 (20건)
├── eval_judge.py                          # LLM Judge (gpt-4o 자동 채점)
└── eval_scenarios.py                      # 계산기 단위 테스트 (20건)
```

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
