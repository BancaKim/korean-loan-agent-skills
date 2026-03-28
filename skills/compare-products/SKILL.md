---
name: compare-products
description: 한국 부동산 대출 상품 비교. 두 개 이상의 대출 상품을 나란히 비교 분석. 사용자가 "A vs B", "어떤 대출이 좋을까", "디딤돌 보금자리 비교", "상품 비교"를 요청할 때 사용. Side-by-side comparison of Korean mortgage and Jeonse loan products.
---

# 대출 상품 비교

## Workflow

### 1. 비교 대상 식별

사용자가 언급한 상품명을 다음 스킬에서 매칭:
- `didimdol-loan`: 디딤돌대출
- `bogeumjari-loan`: 보금자리론
- `newborn-purchase-loan`: 신생아 특례 구입
- `beotimok-jeonse-loan`: 버팀목 전세 (일반/청년/신혼)
- `newborn-jeonse-loan`: 신생아 특례 전세

### 2. 해당 스킬 참조

비교 대상 스킬의 SKILL.md를 읽어 최신 데이터를 확인합니다.

### 3. 비교 테이블 생성

다음 항목을 포함한 마크다운 비교표:

| 비교 항목 |
|----------|
| 운영기관 |
| 소득기준 |
| 주택가격/보증금 한도 |
| 최대 대출한도 |
| 금리 범위 |
| 금리유형 (고정/변동) |
| 최장 대출기간 |
| LTV / DTI |
| 우대금리 |
| 특수 조건 (출산, 신혼 등) |

### 4. 사용자 맞춤 추천

사용자의 소득, 주택가격, 가구 상황에 따라:
- 각 상품의 장단점 요약
- 자격이 되는 상품 표시
- 가장 유리한 상품 추천 (금리 기준)
