# Release Certification Checklist

## Quick Certification Commands

```bash
# Local smoke (requires production build on :3100)
npx playwright test e2e/release-smoke.spec.ts --project=chromium --workers=1

# Production post-deploy smoke
E2E_BASE_URL=https://proptech-ai-copilot.vercel.app npx playwright test e2e/production-smoke.spec.ts --project=chromium

# Full report
node scripts/release-cert-report.mjs
node scripts/release-cert-report.mjs --production
```

## Reviewer Manual Checklist (30 min)

### Navigation & Landing
- [ ] Homepage loads within 5s
- [ ] 5-step guided journey visible
- [ ] Sidebar navigation works for all modules

### Aegis-Credit (Strong / Borderline / Stressed)
| Scenario | Income | Debt | Cash | Properties | Mortgages | Price | Expected |
|----------|--------|------|------|-----------|-----------|-------|----------|
| Strong | 80,000 | 5,000 | 5,000,000 | 0 | 0 | 15,000,000 | Green / 0 |
| Borderline | 60,000 | 15,000 | 2,000,000 | 1 | 1 | 15,000,000 | Yellow / 30 |
| Stressed | 40,000 | 25,000 | 500,000 | 2 | 2 | 20,000,000 | Red / 100 |

- [ ] Form labels localized for all 4 locales
- [ ] No lending/approval language
- [ ] Result updates when inputs change

### Valuation
- [ ] City/District/Road selectable
- [ ] Estimate returns visible result
- [ ] Changing city clears stale result

### Loan / Affordability
- [ ] Price input → Calculate → Result
- [ ] Changing price clears old result

### Market Insight
- [ ] Page loads
- [ ] No data shows appropriate message (not positive)

### Decision (Journey Step 5)
- [ ] Readiness summary visible
- [ ] Attention panel visible

### Locale Matrix
| Locale | Journey Title | Aegis CTA | No Raw Keys |
|--------|--------------|-----------|-------------|
| zh-TW | 用五個步驟整理看房資訊 | 執行房貸風險分析 | ✓ |
| en | Organize the viewing decision... | Run risk analysis | ✓ |
| ja | 内見判断を5つの手順で整理 | リスク分析を実行 | ✓ |
| ko | 내방 판단을 다섯 단계로 정리 | 위험 분석 실행 | ✓ |

### Mobile Matrix
- [ ] 360px: no overflow, CTA reachable
- [ ] 390px: no overflow, forms usable
- [ ] 430px: no overflow, results readable

### Trust Boundary
- [ ] No 信用評分 / 聯徵分數
- [ ] No bank approval / loan guarantee language
- [ ] Disclaimers visible on Aegis page

## Production Baseline Comparison

Previous scores:
- Product: 63/100
- Demo: 70/100
- Enterprise: 41/100

After deployment, compare against these baselines.

## Release Blocker Definitions

| Level | Criteria | Action |
|-------|----------|--------|
| P0 | App unusable, critical crash, trust violation | BLOCK release |
| P1 | Wrong evidence, stale result, major i18n gap | BLOCK release |
| P2 | Polish, minor UX | Document, do not block |

---

## Demo Rehearsal Scenarios

### DEMO A: Normal Taipei Buyer

**Context**: First-time buyer in Taipei, comfortable financial position.

**Inputs**:
- Aegis: Income 80,000 / Debt 5,000 / Cash 5,000,000 / 0 properties / 0 mortgages / Price 15,000,000
- Valuation: 臺北市 → 大安區 → 和平東路二段 → 30坪 → 15年 → 8F

**Expected Flow**:
1. Start → Guided Journey step 1
2. Navigate to Aegis via sidebar → Fill form → Green result
3. Show valuation estimate → Reasonable price
4. Show loan calculation
5. Navigate to Decision step → Readiness summary

**What judge notices**: Clear workflow, no stale data, localized interface.

**Fallback**: If Render backend is cold (35s), mention it's a cold start then continue.

### DEMO B: Stressed / Risk Case

**Context**: Over-leveraged buyer with high debt.

**Inputs**:
- Aegis: Income 40,000 / Debt 25,000 / Cash 500,000 / 2 properties / 2 mortgages / Price 20,000,000

**Expected Flow**:
1. Fill Aegis → Red result with 4 risk factors
2. Show traces: 每月負債占收入超過 50%, 可用現金低於物件價格 20%, etc.
3. Navigate to Decision → Attention panel shows items
4. Switch locale to EN → All labels update, backend traces remain Chinese

**What judge notices**: Clear risk communication, no false approval, truthful i18n.
