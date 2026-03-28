---
name: ltv-calculator
description: 한국 주택담보대출 LTV(주택담보대출비율) 계산기. 담보가치 기준 최대 대출 가능액 산출, 2025.10.15 대책 절대한도 반영, 9억 초과 차등 LTV 적용. 사용자가 LTV, 담보인정비율, 규제지역 대출한도, 생애최초 LTV를 물어볼 때 사용. Calculates Korean mortgage LTV limits with absolute caps.
---

# LTV (주택담보대출비율) 계산기

## Workflow

### 1. 사용자 입력 수집

다음 정보를 사용자에게 확인:
- **필수**: 주택 감정가(만원), 지역유형(투기과열/조정대상/비규제), 차주유형(무주택/생애최초/1주택처분/다주택)
- **선택**: 선순위채권 잔액, 소액임차보증금 지역, 임차인 유무

### 2. 계산 실행

```bash
python [SKILLS_DIR]/ltv-calculator/references/calculator.py calculate \
  --property-value 70000 \
  --region-type 투기과열 \
  --borrower-type 무주택
```

**선순위채권/임차인 있는 경우:**
```bash
python [SKILLS_DIR]/ltv-calculator/references/calculator.py calculate \
  --property-value 70000 \
  --region-type 투기과열 \
  --borrower-type 무주택 \
  --senior-liens 5000 \
  --deposit-region 서울 \
  --has-tenant
```

### 3. 결과 해석

- `has_absolute_cap`: 절대한도 적용 여부 (규제지역 15억↑ 주택에서 중요)
- `high_value_applied`: 9억 초과 차등 LTV 적용 여부
- 생애최초 자격이면 LTV 40%→70%로 대폭 상향됨을 안내

## 핵심 규제 데이터 (계산기에 내장)

### 규제지역 LTV
| 차주 유형 | LTV 한도 |
|----------|:-------:|
| 무주택자 | **40%** |
| 생애최초 | **70%** (6개월 내 전입) |
| 1주택자 (처분조건) | **50%** |
| 다주택자 | **0%** (대출 불가) |

### 비규제지역 LTV
| 차주 유형 | LTV 한도 |
|----------|:-------:|
| 무주택자 | **70%** |
| 생애최초 | **80%** |
| 다주택자 | **60%** |

### 가격대별 절대한도 (규제지역, 2025.10.15)
| 주택 시가 | 절대한도 |
|----------|:-------:|
| 15억 이하 | **6억원** |
| 15억~25억 | **4억원** |
| 25억 초과 | **2억원** |

### 9억 초과 차등 (투기과열, 무주택)
- 9억 이하분: 40%, 9억 초과분: 20%
- 예: 12억 → 9억×40% + 3억×20% = **4.2억**

## 관련 스킬
- `dti-calculator`: 소득 대비 상환비율 한도
- `dsr-calculator`: 스트레스 DSR 포함 전체 부채 한도
- `loan-affordability`: LTV·DTI·DSR 동시 적용 종합 한도
