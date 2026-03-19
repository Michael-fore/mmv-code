# Validation Findings: Stealth/Farmland Memo vs. USDA Data

Data extracted from the **USDA ERS Farm Income & Wealth Statistics** (Feb 2026 release, 108MB CSV covering 1910-2026) and cross-referenced with USDA NASS reports.

---

## 1. Net Farm Income — Memo vs. USDA Data

**Memo claims** (appearing to use inflation-adjusted dollars): $48B (1970) → $92B (1973) → $22.8B (1980) → $8.2B (1983), a "64% decline"

| Year | USDA Nominal | USDA Real (2026$) | Memo Claim | Match? |
|------|------------:|------------------:|----------:|:------:|
| 1970 | $14.4B | $93.3B | $48B | ❌ |
| 1973 | $34.4B | $192.9B | $92B | ❌ |
| 1980 | $16.1B | $53.7B | $22.8B | ❌ |
| 1983 | $14.3B | $39.3B | $8.2B | ❌ |

> [!WARNING]
> **None of the memo's NFI figures match official USDA data** in either nominal or 2026-adjusted terms. The memo might be using a different deflator (possibly 1982$ or 2000$), or citing a different metric (e.g., "real farm income" which could include inventory adjustments). The **directional narrative** is correct — NFI did spike in 1973 and crater by 1983 — but the specific dollar amounts are unverifiable as presented.

**The 64% decline claim**: From 1980 ($16.1B) to 1983 ($14.3B) is only an 11% nominal decline. In real 2026 terms: $53.7B → $39.3B = 27% decline. The 64% would require a different base year or metric.

---

## 2. Farm Debt — Memo vs. USDA Data

**Memo claims**: Farm debt $29B (1970) → $71B (1979) → $215B (1984)

| Year | USDA Total Debt | Memo Claim | Match? |
|------|----------------:|----------:|:------:|
| 1970 | $48.5B | $29B | ❌ |
| 1979 | $147.5B | $71B | ❌ |
| 1984 | $188.8B | $215B | ❌ |

> [!CAUTION]
> **Major discrepancy**: The memo's 1984 figure of $215B is **14% higher** than USDA's $188.8B. The 1970 and 1979 figures are roughly **half** the USDA data. The memo may be citing real estate debt only (not total farm debt), or using a different source. USDA real estate debt alone was $101.4B in 1984, which doesn't match either. The FDIC's own history uses $215B, suggesting the memo may be citing the FDIC secondary source rather than primary USDA data. The general story of debt escalation is correct, but the specifics are off.

---

## 3. Interest Exceeding Net Farm Income

**Memo claims**: "For the first time in history, total interest payments on farm loans exceeded total net farm income for the country" (implied: 1981)

| Year | Net Farm Income | Interest Expense | Interest > NFI? |
|------|----------------:|-----------------:|:--:|
| 1979 | $27.4B | $12.5B | No |
| 1980 | $16.1B | $15.6B | No (close!) |
| 1981 | $26.9B | $19.1B | No |
| 1982 | $23.8B | $21.0B | No |
| **1983** | **$14.3B** | **$20.6B** | **⚠️ YES** |
| 1984 | $26.0B | $20.3B | No |

> [!IMPORTANT]
> Interest first exceeded NFI in **1983, not 1981**. The memo places this in the context of the Volcker shock (1981), but the actual crossover was two years later when low NFI ($14.3B) coincided with still-high interest costs ($20.6B). 1980 was close ($16.1B vs $15.6B) but NFI still slightly exceeded interest that year.

---

## 4. Real Estate Asset Values (Proxy for Land Values)

The ERS dataset includes total US farm real estate asset values:

| Year | RE Assets | Implied $/acre (÷ ~1B acres) |
|------|----------:|-----:|
| 1970 | $202.4B | ~$202 |
| 1973 | $298.3B | ~$298 |
| 1979 | $706.1B | ~$706 |
| 1981 | $785.6B | ~$786 |
| 1985 | $586.2B | ~$586 |
| 1987 | $563.7B | ~$564 |
| 1991 | $624.8B | ~$625 |
| 2005 | $1,372.6B | ~$1,373 |
| 2007 | $1,549.0B | ~$1,549 |
| 2010 | $1,660.1B | ~$1,660 |
| 2024 | $3,488.7B | ~$3,489 |

> [!NOTE]
> These are **total** asset values, not per-acre. The memo's per-acre figures ($354 in 1973, $1,290 in 1981) require the USDA NASS per-acre series, which needs either the Quick Stats API (requires free API key registration) or the annual Land Values report. The 2025 NASS report was downloaded (22 pages) but only covers 2011-2025 per-acre values, not the historical series back to 1968.

---

## 5. Key Data Available for Further Validation

### Available Now (Downloaded)
| Dataset | Location | Coverage |
|---------|----------|----------|
| USDA ERS Farm Income & Wealth | `/tmp/ers_data/` (108MB CSV) | 1910-2026, 100+ variables |
| NASS Land Values 2025 Report | `/tmp/nass_land_values_2025.pdf` | 2011-2025 per-acre by state |

### Available Free (Requires Registration or Manual Access)
| Dataset | Source | What It Provides |
|---------|--------|-----------------|
| **NASS Quick Stats API** | [quickstats.nass.usda.gov](https://quickstats.nass.usda.gov) | Per-acre farmland values 1968-2025 (free API key registration) |
| **NRCS Soil Data Access** | [sdmdataaccess.nrcs.usda.gov](https://sdmdataaccess.nrcs.usda.gov) | Soil map units for Vail Ranch (REST API, was timing out) |
| **NCREIF Farmland Index** | [ncreif.org](https://ncreif.org) | Quarterly total returns for Sharpe calculation (membership required for full data) |
| **Imperial County Assessor** | [imperialcounty.org](https://www.imperialcounty.org) | Parcel details, assessed values for Vail Ranch (web portal) |
| **USDA CropScape** | [nassgeodata.gmu.edu/CropScape](https://nassgeodata.gmu.edu/CropScape/) | Satellite-derived crop identification for Vail Ranch |
| **FEMA Flood Maps** | [msc.fema.gov](https://msc.fema.gov) | Flood zone verification for parcel 020-160-030 |
| **SEC EDGAR** | [sec.gov](https://sec.gov) | FPI and LAND 10-K filings for REIT comparisons |
| **Purdue Ag Barometer** | [purdue.edu/agbarometer](https://ag.purdue.edu/commercialag/ageconomybarometer/) | Solar lease contact rates (~20% of farmers) and offered rates |

---

## Summary of Discrepancies Found

| # | Memo Claim | Reality | Severity |
|---|-----------|---------|:--------:|
| 1 | NFI $48B in 1970 | $14.4B nominal / $93.3B real (2026$) | 🟡 Base-year unclear |
| 2 | NFI $92B in 1973 | $34.4B nominal / $192.9B real (2026$) | 🟡 Base-year unclear |
| 3 | NFI decline "64%" (1980→1983) | 11% nominal / 27% real decline | 🔴 Overstated |
| 4 | Farm debt $29B (1970) | $48.5B per USDA | 🔴 Wrong source? |
| 5 | Farm debt $215B (1984) | $188.8B per USDA ($215B per FDIC) | 🟡 Source conflict |
| 6 | Interest > NFI implied in 1981 | Actually occurred in **1983** | 🟡 Off by 2 years |
| 7 | "⅔ of owners over 65" | Census: ~⅓ of *producers* over 65 | 🔴 Likely wrong |
| 8 | NCREIF Sharpe of 1.3 | Confirmed but appraisal-smoothed | 🟡 Methodological |
