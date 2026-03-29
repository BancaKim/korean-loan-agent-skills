---
name: loan-affordability
description: 한국 주택담보대출 종합 대출가능액 계산. LTV·DTI·DSR 세 가지 규제를 동시 적용하여 실제 최대 대출 가능액 산출. 바인딩 규제 식별 및 한도 개선 시뮬레이션. 사용자가 "얼마까지 대출 가능?", "대출 한도", "최대 대출액", "대출가능액"을 물어볼 때 사용.
allowed-tools: calculate_loan_affordability_tool
---

# 대출가능액 종합 계산기

## ⚠️ 필수 규칙

**반드시 `calculate_loan_affordability_tool` 도구를 호출하여 정확한 수치를 계산하세요.**
절대로 도구 호출 없이 답변하지 마세요. 사용자가 대출 한도를 물어보면 반드시 도구를 실행하고 그 결과를 기반으로 답변합니다.

## Workflow

### 1. 사용자 입력 파싱

사용자 메시지에서 다음 정보를 추출합니다:

| 파라미터 | 필수 | 기본값 | 설명 |
|---------|:---:|-------|------|
| annual_income | ✅ | - | 연소득 (만원). "6천만"→6000 |
| property_value | ✅ | - | 주택가격 (만원). "7억"→70000 |
| loan_rate | ✅ | 4.5 | 금리 (%). 미언급 시 4.5% |
| loan_months | ✅ | 360 | 기간 (개월). "30년"→360 |
| region_type | | 투기과열 | 서울→투기과열, 지방→비규제 |
| borrower_type | | 무주택 | 무주택/서민실수요/생애최초/1주택처분/다주택 |
| rate_type | | 변동 | 변동/혼합5년/혼합10년/고정 |
| sector | | 은행 | 은행/2금융 |

### 2. 도구 호출 (필수!)

`calculate_loan_affordability_tool` 도구를 파라미터와 함께 호출합니다.

**기본 호출 예시:**
```
calculate_loan_affordability_tool(
  annual_income=6000,        # 연소득 6천만
  property_value=70000,      # 7억 아파트
  loan_rate=4.5,             # 금리 4.5%
  loan_months=360,           # 30년
  region_type="투기과열",     # 서울
  borrower_type="무주택",
  rate_type="변동"
)
```

**기존 대출이 있는 경우:**
```
calculate_loan_affordability_tool(
  annual_income=8000,
  property_value=90000,
  loan_rate=4.0,
  loan_months=360,
  region_type="투기과열",
  borrower_type="무주택",
  rate_type="혼합5년",
  existing_mortgages='[{"balance":10000,"rate":3.5,"remaining_months":240,"method":"원리금균등"}]',
  other_loans='[{"balance":3000,"rate":5.0,"remaining_months":36,"method":"원리금균등","loan_type":"신용대출"}]'
)
```

### 3. 결과 해석 및 안내

JSON 결과에서 다음을 사용자에게 설명:

**필수 안내 사항:**
- **LTV / DTI / DSR** 각각의 한도와 산출 근거
- **최종 한도** = 세 규제 중 가장 낮은 금액
- **바인딩 규제** = 한도를 결정한 병목 규제
- **한도 개선 팁** (improvement_tips)

**답변 형식 예시:**
```
📊 대출가능액 종합 분석 결과

✅ LTV 한도: X.X억원 (LTV 40%)
✅ DTI 한도: X.X억원 (DTI 40%)
✅ DSR 한도: X.X억원 (DSR 40%, 스트레스 적용 금리 X.X%)

🎯 최종 대출 가능액: X.X억원
📌 제한 요소: [바인딩 규제]

💡 한도 개선 방법:
- [improvement_tips 내용]
```

### 4. 바인딩별 맞춤 조언

- **DSR 바인딩**: 고정금리 전환 → 스트레스 0% (가장 효과적), 만기 연장
- **LTV 바인딩**: 생애최초 자격 확인 (40%→70%), 저가 주택 고려
- **DTI 바인딩**: 기존 대출 상환, 비규제지역 고려

## 핵심 원칙

```
최종 대출가능액 = MIN(LTV한도, DTI한도, DSR한도, 가격대별 절대한도)
```

세 규제 중 **가장 낮은 금액**이 실제 한도. 하나라도 통과 못하면 대출 불가.

## 관련 스킬
- `ltv-calculator`: LTV 상세 (절대한도, 9억 차등)
- `dti-calculator`: DTI 상세 (기타대출 이자만)
- `dsr-calculator`: DSR 상세 (스트레스 가산금리)
