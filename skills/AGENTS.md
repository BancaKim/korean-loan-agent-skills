# Korean Real Estate Loan Skills

한국 부동산대출 규제·정책대출 AI 에이전트 스킬 모음.
LangChain DeepAgents, LangGraph, CrewAI 등 LLM 에이전트 프레임워크에서 사용할 수 있는 도메인 스킬입니다.

## 스킬 목록

### 규제 계산기 (Python CLI 포함)

| 폴더 | 설명 | CLI |
|------|------|:---:|
| `dti-calculator/` | DTI(총부채상환비율) 계산, 최대 대출 가능액 역산 | ✅ |
| `dsr-calculator/` | DSR(총부채원리금상환비율) 계산, 스트레스 가산금리 3단계 | ✅ |
| `ltv-calculator/` | LTV(주택담보대출비율) 계산, 규제지역 절대한도 | ✅ |
| `loan-affordability/` | 대출가능액 종합 (LTV·DTI·DSR 동시 적용, 개선 시뮬레이션) | ✅ |

### 정책대출 상품 가이드

| 폴더 | 설명 |
|------|------|
| `bogeumjari-loan/` | 보금자리론 (한국주택금융공사, 장기 고정금리, 최대 50년) |
| `didimdol-loan/` | 디딤돌대출 (주택도시기금, 무주택 서민 저금리) |
| `newborn-purchase-loan/` | 신생아 특례 디딤돌대출 (출산 2년 내, 초저금리 구입) |
| `beotimok-jeonse-loan/` | 버팀목 전세대출 (일반·청년·신혼 3종) |
| `newborn-jeonse-loan/` | 신생아 특례 버팀목 전세대출 (출산 2년 내) |
