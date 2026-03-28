---
name: dti-calculator
description: 한국 주택담보대출 DTI(총부채상환비율) 계산 및 DTI 기준 최대 대출 가능액 역산. 사용자가 DTI 계산, DTI 한도, 소득 대비 상환비율, 신DTI 기준 대출 한도를 물어볼 때 사용. Calculates Korean mortgage DTI ratio and reverse-calculates max loan amount within DTI limits.
---

# DTI (총부채상환비율) 계산기

## ⚠️ 필수 규칙

**반드시 `calculate_dti` 또는 `calculate_dti_max_loan` 도구를 호출하여 정확한 수치를 계산하세요.**
- DTI 비율 질문 → `calculate_dti` 호출
- 최대 대출 가능액 질문 → `calculate_dti_max_loan` 호출

## Workflow

### 1. 사용자 입력 파싱

| 파라미터 | 필수 | 기본값 | 설명 |
|---------|:---:|-------|------|
| annual_income | ✅ | - | 연소득 (만원) |
| loan_amount | ✅* | - | 대출금액 (만원) *calculate용 |
| loan_rate | ✅ | 4.5 | 금리 (%) |
| loan_months | ✅ | 360 | 기간 (개월) |
| region | | 투기과열 | 투기과열(40%)/조정대상(50%)/비규제(60%) |

### 2. 도구 호출 (필수!)

상황에 맞는 도구를 호출합니다.

**DTI 계산 예시:**
```
calculate_dti(
  annual_income=5000,        # 연소득 5천만
  loan_amount=30000,         # 3억 대출
  loan_rate=4.5,
  loan_months=360,
  region="투기과열",
  existing_mortgages='[{"balance":10000,"rate":3.5,"remaining_months":240,"method":"원리금균등"}]',
  other_loans='[{"balance":5000,"rate":5.0}]'
)
```

**DTI 기준 최대 대출 가능액 역산:**
```
calculate_dti_max_loan(
  annual_income=5000,
  loan_rate=4.5,
  loan_months=360,
  region="투기과열"
)
```

### 3. 결과 해석

- DTI 비율과 한도 대비 여유/초과 정도
- 초과 시: 대출금액 축소, 상환기간 연장, 기타대출 상환 등 개선 방안
- **DTI는 기타대출의 이자만 포함** (DSR보다 느슨함을 안내)

## 핵심 규제 데이터

### DTI 한도율
| 지역 | DTI 한도 |
|------|:-------:|
| 투기지역·투기과열지구 | **40%** |
| 조정대상지역 | **50%** |
| 비규제지역 | **60%** |
| 서민·실수요자 (연소득 7천만 이하 무주택) | **60%** |

### 신DTI 산정 공식
```
신DTI(%) = (A + B + C) / 연소득 × 100
A = 해당 주담대 연간 원리금 상환액
B = 기존 주담대 연간 원리금 상환액
C = 기타대출 연간 이자 상환액 ← DSR과의 핵심 차이 (이자만!)
```

### DTI vs DSR 차이
- **DTI**: 기타대출의 **이자만** 포함, 스트레스 가산 없음
- **DSR**: **모든** 대출 **원리금** 포함, 스트레스 가산금리 적용
- 현행 실무에서 DTI와 DSR **모두** 통과해야 대출 승인

## 관련 스킬
- `dsr-calculator`: DSR 계산 (전체 부채 원리금 기준, 스트레스 포함)
- `ltv-calculator`: 담보가치 기준 한도
- `loan-affordability`: LTV·DTI·DSR 동시 적용 종합 한도
