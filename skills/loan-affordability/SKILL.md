---
name: loan-affordability
description: 한국 주택담보대출 종합 대출가능액 계산. LTV·DTI·DSR 세 가지 규제를 동시 적용하여 실제 최대 대출 가능액 산출. 바인딩 규제 식별 및 한도 개선 시뮬레이션. 사용자가 "얼마까지 대출 가능?", "대출 한도", "최대 대출액", "대출가능액"을 물어볼 때 사용. Comprehensive Korean mortgage affordability calculator combining LTV, DTI, and DSR limits.
---

# 대출가능액 종합 계산기

## Workflow

### 1. 사용자 입력 수집

다음 정보를 사용자에게 확인:
- **필수**: 연소득(만원), 주택 감정가(만원), 금리(%), 상환기간(년/개월)
- **선택**: 지역유형, 차주유형, 상환방식, 금리유형, 금융권, 선순위채권, 기존대출

정보가 부족하면 기본값을 사용하되, 반드시 어떤 가정을 했는지 알려줍니다:
- 지역: 투기과열 (서울 가정)
- 차주: 무주택
- 금리유형: 변동
- 금융권: 은행

### 2. 종합 계산 실행

```bash
python [SKILLS_DIR]/loan-affordability/references/calculator.py calculate \
  --annual-income 6000 \
  --property-value 70000 \
  --loan-rate 4.5 \
  --loan-months 360 \
  --region-type 투기과열 \
  --borrower-type 무주택 \
  --rate-type 변동
```

### 3. 결과 해석 및 종합 안내

JSON 출력에서 다음을 사용자에게 설명:
- **LTV / DTI / DSR** 각각의 한도와 산출 근거
- **최종 한도** = 세 규제 중 가장 낮은 금액
- **바인딩 규제** = 한도를 결정한 병목 규제
- **한도 개선 시뮬레이션** (`improvement_tips`)

### 4. 추가 안내

바인딩 규제에 따른 맞춤 조언:
- **DSR 바인딩**: 고정금리 전환 → 스트레스 0% (가장 효과적), 만기 연장
- **LTV 바인딩**: 생애최초 자격 확인 (40%→70%), 저가 주택 고려
- **DTI 바인딩**: 기존 대출 상환, 비규제지역 고려

정책대출(디딤돌, 보금자리론, 신생아 특례) 대상이면 해당 스킬도 함께 안내합니다.

## 핵심 원칙

```
최종 대출가능액 = MIN(LTV한도, DTI한도, DSR한도, 가격대별 절대한도)
```

세 규제 중 **가장 낮은 금액**이 실제 한도. 하나라도 통과 못하면 대출 불가.

## 관련 스킬
- `ltv-calculator`: LTV 상세 (절대한도, 9억 차등)
- `dti-calculator`: DTI 상세 (기타대출 이자만)
- `dsr-calculator`: DSR 상세 (스트레스 가산금리)
- `didimdol-loan`: 디딤돌대출 (무주택 서민 저금리)
- `bogeumjari-loan`: 보금자리론 (장기 고정금리)
- `newborn-purchase-loan`: 신생아 특례 구입 (초저금리)
