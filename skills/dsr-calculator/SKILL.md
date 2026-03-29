---
name: dsr-calculator
description: 한국 주택담보대출 DSR(총부채원리금상환비율) 계산 및 최대 대출 가능액 역산. 스트레스 가산금리 3단계(2025.7.1~) 반영. 사용자가 DSR 계산, DSR 한도, 스트레스 금리, 대출 가능액, 변동금리 vs 고정금리 비교를 물어볼 때 사용.
allowed-tools: calculate_dsr_tool, calculate_dsr_max_loan
---

# DSR (총부채원리금상환비율) 계산기

## ⚠️ 필수 규칙

**반드시 `calculate_dsr_tool` 또는 `calculate_dsr_max_loan` 도구를 호출하여 정확한 수치를 계산하세요.**
- DSR 비율 질문 → `calculate_dsr_tool` 호출
- 최대 대출 가능액 질문 → `calculate_dsr_max_loan` 호출
- 변동 vs 고정 비교 → 두 도구를 각각 호출하여 비교

## Workflow

### 1. 사용자 입력 파싱

| 파라미터 | 필수 | 기본값 | 설명 |
|---------|:---:|-------|------|
| annual_income | ✅ | - | 연소득 (만원) |
| loan_amount | ✅* | - | 대출금액 (만원) *calculate용 |
| loan_rate | ✅ | 4.5 | 약정 금리 (%) |
| loan_months | ✅ | 360 | 기간 (개월) |
| rate_type | | 변동 | 변동/혼합5년/혼합10년/고정 |
| region | | 수도권 | 수도권/지방 (서울→수도권) |
| sector | | 은행 | 은행(DSR 40%)/2금융(DSR 50%) |

### 2. 도구 호출 (필수!)

상황에 맞는 도구를 호출합니다.

**DSR 계산 예시:**
```
calculate_dsr_tool(
  annual_income=5000,        # 연소득 5천만
  loan_amount=30000,         # 3억 대출
  loan_rate=4.5,             # 금리 4.5%
  loan_months=360,           # 30년
  rate_type="변동",           # 변동금리 → 스트레스 +3.0%p
  region="수도권"
)
```

**최대 대출 가능액 역산 예시:**
```
calculate_dsr_max_loan(
  annual_income=5000,
  loan_rate=4.5,
  loan_months=360,
  rate_type="변동",
  region="수도권"
)
```

### 3. 결과 해석

- `stress_rate`: 스트레스 가산 적용 후 실제 DSR 산정 금리
- 변동금리 vs 고정금리 차이가 크면 금리유형 전환 추천
- DSR 초과 시: 고정금리 전환(가장 효과적), 만기 연장, 기존대출 상환 안내

## 핵심 규제 데이터

### DSR 한도
| 금융권 | DSR 한도 |
|--------|:-------:|
| 은행권 | **40%** |
| 2금융권 | **50%** |

### 스트레스 가산금리 (3단계, 2025.7.1~)
| 구분 | 기본 가산금리 |
|------|:----------:|
| 수도권/규제지역 주담대 | **+3.0%p** |
| 지방 주담대 | **+0.75%p** |

### 금리유형별 스트레스 적용비율
| 금리유형 | 적용비율 | 수도권 실제 가산 |
|---------|:------:|:-----------:|
| 변동금리 | 100% | **+3.0%p** |
| 혼합형 (5~9년) | 80% | +2.4%p |
| 혼합형 (9~15년) | 60% | +1.8%p |
| 순수 고정금리 | 0% | **+0.0%p** |

## 관련 스킬
- `dti-calculator`: DTI 계산 (기타대출 이자만 반영, 더 느슨)
- `ltv-calculator`: 담보가치 기준 한도
- `loan-affordability`: LTV·DTI·DSR 동시 적용 종합 한도
