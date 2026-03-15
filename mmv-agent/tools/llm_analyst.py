"""
LLM Analyst — structured analytical reasoning for real estate underwriting.

Routes analysis tasks to the appropriate LLM (Gemini for standard tasks,
Claude Opus for complex reasoning) with deterministic rule-based fallbacks
when no API keys are available.

Architecture rules:
    - Primary model: Gemini (cheap, fast, good enough)
    - Complex reasoning: Claude Opus (risk_assessment, exit_analysis)
    - Always include deterministic fallbacks
"""

from __future__ import annotations

import json
import os
import statistics
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

StatementType = Literal["FACT", "INFERENCE"]
ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]

COMPLEX_SECTIONS: set[str] = {"risk_assessment", "exit_analysis"}
SUPPORTED_SECTIONS: set[str] = {
    "land_values",
    "cap_rate",
    "risk_assessment",
    "crop_production",
    "exit_analysis",
}

# Benchmark constants used by deterministic analysis
_CAP_RATE_BENCHMARKS: dict[str, float] = {
    "farmland_national_avg": 3.2,
    "ranchland_national_avg": 2.8,
    "irrigated_premium": 0.5,
}

_RISK_WEIGHT: dict[str, float] = {
    "water": 0.25,
    "climate": 0.20,
    "market": 0.20,
    "regulatory": 0.15,
    "operational": 0.10,
    "financial": 0.10,
}


# ---------------------------------------------------------------------------
# Statement builder helpers
# ---------------------------------------------------------------------------

def _stmt(
    statement: str,
    stmt_type: StatementType,
    confidence: ConfidenceLevel,
    confidence_reason: str,
    source_citation: str,
) -> dict[str, str]:
    """Build a validated statement dict matching the structured output schema."""
    return {
        "statement": statement,
        "type": stmt_type,
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "source_citation": source_citation,
    }


# ---------------------------------------------------------------------------
# LLM integration helpers (thin wrappers — real calls only when keys exist)
# ---------------------------------------------------------------------------

def _gemini_api_key() -> str | None:
    """Return the Gemini API key if configured, else None."""
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")


def _anthropic_api_key() -> str | None:
    """Return the Anthropic API key if configured, else None."""
    return os.environ.get("ANTHROPIC_API_KEY")


def _build_analysis_prompt(section_name: str, section_data: dict, raw_data: dict | None) -> str:
    """Construct a structured prompt for LLM-based section analysis.

    The prompt asks the model to return a JSON array of statement objects
    conforming to the output schema.
    """
    context_block = ""
    if raw_data:
        context_block = (
            "\n\nAdditional context from the full underwriting dataset:\n"
            f"```json\n{json.dumps(raw_data, indent=2, default=str)}\n```"
        )

    return f"""You are an expert agricultural real estate underwriting analyst.

Analyze the following **{section_name}** data and produce structured analytical
insights. Return ONLY a JSON array of objects with this schema:

{{
  "statement": "<analytical insight>",
  "type": "FACT" | "INFERENCE",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "confidence_reason": "<why this confidence level>",
  "source_citation": "<data point or calculation>"
}}

Rules:
- FACT statements must be directly derivable from the provided numbers.
- INFERENCE statements should combine multiple data points or apply domain
  knowledge (cap-rate benchmarks, regional comparisons, risk heuristics).
- Provide at least 3 statements, more for complex sections.
- Confidence must reflect data quality and derivation certainty.

Section data:
```json
{json.dumps(section_data, indent=2, default=str)}
```{context_block}

Return ONLY the JSON array — no markdown fences, no commentary."""


def _call_gemini(prompt: str) -> list[dict] | None:
    """Call Google Gemini and parse the structured JSON response.

    Returns None on any failure so the caller can fall back to deterministic.
    """
    api_key = _gemini_api_key()
    if not api_key:
        return None

    try:
        import google.generativeai as genai  # type: ignore[import-untyped]

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception:  # noqa: BLE001 — broad catch intentional for fallback
        return None


def _call_claude(prompt: str) -> list[dict] | None:
    """Call Anthropic Claude Opus and parse the structured JSON response.

    Returns None on any failure so the caller can fall back to deterministic.
    """
    api_key = _anthropic_api_key()
    if not api_key:
        return None

    try:
        import anthropic  # type: ignore[import-untyped]

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(message.content[0].text)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Deterministic section analysers
# ---------------------------------------------------------------------------

def _analyze_land_values(data: dict) -> list[dict]:
    """Generate FACT + INFERENCE statements for a land_values section."""
    results: list[dict] = []

    price_per_acre = data.get("price_per_acre")
    total_acres = data.get("total_acres")
    comparable_sales = data.get("comparable_sales", [])
    historical_prices = data.get("historical_prices", {})
    improvements_value = data.get("improvements_value", 0)
    asking_price = data.get("asking_price")

    # --- FACTs ---
    if price_per_acre is not None and total_acres is not None:
        raw_land_value = price_per_acre * total_acres
        results.append(_stmt(
            f"Raw land value at ${price_per_acre:,.0f}/acre across "
            f"{total_acres:,.0f} acres totals ${raw_land_value:,.0f}.",
            "FACT", "HIGH",
            "Direct multiplication of provided per-acre price and acreage.",
            f"price_per_acre={price_per_acre}, total_acres={total_acres}",
        ))

    if comparable_sales:
        comp_prices = [c.get("price_per_acre", 0) for c in comparable_sales if c.get("price_per_acre")]
        if comp_prices:
            avg_comp = statistics.mean(comp_prices)
            results.append(_stmt(
                f"Average comparable sale price is ${avg_comp:,.0f}/acre "
                f"based on {len(comp_prices)} transactions.",
                "FACT", "HIGH",
                "Arithmetic mean of verified comparable sales.",
                f"comparable_sales[{len(comp_prices)} records]",
            ))

            if price_per_acre:
                delta_pct = ((price_per_acre - avg_comp) / avg_comp) * 100
                direction = "above" if delta_pct > 0 else "below"
                results.append(_stmt(
                    f"Subject property price is {abs(delta_pct):.1f}% {direction} "
                    f"the comparable average (${price_per_acre:,.0f} vs ${avg_comp:,.0f}).",
                    "INFERENCE", "HIGH" if len(comp_prices) >= 3 else "MEDIUM",
                    f"{'Strong' if len(comp_prices) >= 3 else 'Limited'} comp set "
                    f"({len(comp_prices)} sales) supports this comparison.",
                    "price_per_acre vs mean(comparable_sales.price_per_acre)",
                ))

    # Historical trend
    if historical_prices and len(historical_prices) >= 2:
        sorted_years = sorted(historical_prices.keys())
        first_year, last_year = sorted_years[0], sorted_years[-1]
        first_val, last_val = historical_prices[first_year], historical_prices[last_year]
        year_span = int(last_year) - int(first_year)
        if year_span > 0 and first_val > 0:
            cagr = ((last_val / first_val) ** (1 / year_span) - 1) * 100
            results.append(_stmt(
                f"Land values show a {cagr:.1f}% CAGR over {year_span} years "
                f"(${first_val:,.0f} in {first_year} to ${last_val:,.0f} in {last_year}).",
                "FACT", "HIGH",
                "Calculated from provided historical price series.",
                f"historical_prices[{first_year}..{last_year}]",
            ))
            if cagr > 5:
                results.append(_stmt(
                    "Appreciation materially exceeds long-term farmland averages (~3%), "
                    "suggesting strong local demand drivers or speculative pressure.",
                    "INFERENCE", "MEDIUM",
                    "Comparison to national USDA farmland appreciation benchmarks.",
                    f"CAGR={cagr:.1f}% vs national avg ~3%",
                ))

    if improvements_value and asking_price:
        land_only = asking_price - improvements_value
        pct_improvements = (improvements_value / asking_price) * 100
        results.append(_stmt(
            f"Improvements account for {pct_improvements:.1f}% of asking price "
            f"(${improvements_value:,.0f} of ${asking_price:,.0f}); "
            f"implied bare-land value is ${land_only:,.0f}.",
            "FACT", "HIGH",
            "Direct subtraction from asking price.",
            f"asking_price={asking_price}, improvements_value={improvements_value}",
        ))

    return results


def _analyze_cap_rate(data: dict) -> list[dict]:
    """Generate FACT + INFERENCE statements for a cap_rate section."""
    results: list[dict] = []

    noi = data.get("noi")
    property_value = data.get("property_value")
    cap_rate = data.get("cap_rate")
    rental_income = data.get("rental_income")
    operating_expenses = data.get("operating_expenses")
    lease_terms = data.get("lease_terms", {})
    property_type = data.get("property_type", "farmland")

    # Derive cap rate if not provided
    if cap_rate is None and noi is not None and property_value:
        cap_rate = (noi / property_value) * 100

    if noi is not None and property_value:
        results.append(_stmt(
            f"Net Operating Income of ${noi:,.0f} on a ${property_value:,.0f} "
            f"valuation yields a {cap_rate:.2f}% capitalization rate.",
            "FACT", "HIGH",
            "Direct NOI / value calculation.",
            f"noi={noi}, property_value={property_value}",
        ))

    if cap_rate is not None:
        benchmark_key = f"{property_type}_national_avg"
        benchmark = _CAP_RATE_BENCHMARKS.get(benchmark_key, 3.0)
        spread = cap_rate - benchmark
        if spread > 0:
            verdict = "higher yield but potentially more risk"
        else:
            verdict = "lower yield suggesting a premium/lower-risk asset"
        results.append(_stmt(
            f"Cap rate of {cap_rate:.2f}% is {abs(spread):.2f}pp "
            f"{'above' if spread > 0 else 'below'} the national {property_type} "
            f"average of {benchmark:.1f}% — {verdict}.",
            "INFERENCE", "MEDIUM",
            "National averages are broad; local sub-markets may diverge.",
            f"cap_rate={cap_rate:.2f}% vs benchmark={benchmark}%",
        ))

    if rental_income and operating_expenses:
        expense_ratio = (operating_expenses / rental_income) * 100
        results.append(_stmt(
            f"Operating expense ratio is {expense_ratio:.1f}% "
            f"(${operating_expenses:,.0f} / ${rental_income:,.0f}).",
            "FACT", "HIGH",
            "Direct ratio from provided income and expense figures.",
            f"operating_expenses={operating_expenses}, rental_income={rental_income}",
        ))
        if expense_ratio > 45:
            results.append(_stmt(
                "Expense ratio exceeds 45%, indicating significant management "
                "overhead or deferred maintenance that may compress net yields.",
                "INFERENCE", "MEDIUM",
                "Threshold based on typical ag-property operating ranges (30-45%).",
                f"expense_ratio={expense_ratio:.1f}%",
            ))

    if lease_terms:
        remaining_years = lease_terms.get("remaining_years")
        escalation = lease_terms.get("annual_escalation_pct")
        if remaining_years is not None:
            stability = "strong" if remaining_years >= 5 else "limited"
            results.append(_stmt(
                f"Current lease has {remaining_years} years remaining, "
                f"providing {stability} income visibility.",
                "FACT", "HIGH" if remaining_years >= 3 else "MEDIUM",
                "Lease term directly from provided data.",
                f"lease_terms.remaining_years={remaining_years}",
            ))
        if escalation is not None and noi is not None:
            projected_noi_5yr = noi * ((1 + escalation / 100) ** 5)
            results.append(_stmt(
                f"With {escalation}% annual escalation, projected NOI in 5 years "
                f"reaches ${projected_noi_5yr:,.0f} (from current ${noi:,.0f}).",
                "INFERENCE", "MEDIUM",
                "Assumes escalation clause is exercised consistently; "
                "actual rents may be renegotiated.",
                f"noi={noi}, escalation={escalation}%",
            ))

    return results


def _analyze_risk_assessment(data: dict) -> list[dict]:
    """Generate FACT + INFERENCE statements for a risk_assessment section."""
    results: list[dict] = []

    risk_factors: dict[str, Any] = data.get("risk_factors", {})
    overall_score = data.get("overall_risk_score")

    # Aggregate weighted risk
    if risk_factors:
        weighted_sum = 0.0
        weight_total = 0.0
        high_risks: list[str] = []
        for category, details in risk_factors.items():
            score = details if isinstance(details, (int, float)) else details.get("score", 0)
            weight = _RISK_WEIGHT.get(category, 0.10)
            weighted_sum += score * weight
            weight_total += weight
            if score >= 7:
                high_risks.append(category)

        if weight_total > 0:
            weighted_avg = weighted_sum / weight_total
            results.append(_stmt(
                f"Weighted aggregate risk score is {weighted_avg:.1f}/10 "
                f"across {len(risk_factors)} assessed categories.",
                "FACT", "HIGH",
                "Weighted average using standard MMV risk-weight matrix.",
                f"risk_factors=[{', '.join(risk_factors.keys())}]",
            ))

        if high_risks:
            results.append(_stmt(
                f"Elevated risk detected in: {', '.join(high_risks)}. "
                "These categories scored 7+ out of 10 and require mitigation plans.",
                "FACT", "HIGH",
                "Threshold of 7/10 flags categories needing active management.",
                f"high_risk_categories={high_risks}",
            ))

    # Water-specific analysis
    water = risk_factors.get("water", {})
    if isinstance(water, dict):
        aquifer_decline = water.get("aquifer_decline_rate")
        water_rights = water.get("water_rights_secured", False)
        if aquifer_decline is not None:
            severity = "critical" if aquifer_decline > 2 else "manageable" if aquifer_decline > 0.5 else "stable"
            results.append(_stmt(
                f"Aquifer decline rate of {aquifer_decline} ft/year is classified as {severity}.",
                "INFERENCE", "MEDIUM",
                "Classification based on USGS depletion rate thresholds for agricultural sustainability.",
                f"water.aquifer_decline_rate={aquifer_decline}",
            ))
        if not water_rights:
            results.append(_stmt(
                "Water rights are NOT secured — this represents a material risk to "
                "long-term operational viability and property valuation.",
                "FACT", "HIGH",
                "Binary assessment from provided water-rights status.",
                "water.water_rights_secured=False",
            ))

    # Climate
    climate = risk_factors.get("climate", {})
    if isinstance(climate, dict):
        drought_freq = climate.get("drought_frequency")
        flood_zone = climate.get("flood_zone")
        if drought_freq:
            results.append(_stmt(
                f"Drought frequency is categorized as '{drought_freq}', "
                "impacting crop insurance costs and yield reliability.",
                "INFERENCE", "MEDIUM",
                "Qualitative assessment; precise impact depends on crop mix and irrigation.",
                f"climate.drought_frequency={drought_freq}",
            ))
        if flood_zone:
            in_zone = flood_zone not in ("X", "none", None)
            results.append(_stmt(
                f"Property is {'within' if in_zone else 'outside'} a FEMA flood zone "
                f"(zone: {flood_zone}).",
                "FACT", "HIGH",
                "FEMA flood zone classification from provided data.",
                f"climate.flood_zone={flood_zone}",
            ))

    if overall_score is not None:
        band = "low" if overall_score <= 3 else "moderate" if overall_score <= 6 else "high"
        results.append(_stmt(
            f"Overall risk score of {overall_score}/10 places this property in the "
            f"'{band}' risk band.",
            "FACT", "HIGH",
            "Direct mapping of provided score to risk bands (0-3 low, 4-6 moderate, 7-10 high).",
            f"overall_risk_score={overall_score}",
        ))

    return results


def _analyze_crop_production(data: dict) -> list[dict]:
    """Generate FACT + INFERENCE statements for a crop_production section."""
    results: list[dict] = []

    crops: list[dict] = data.get("crops", [])
    total_acres = data.get("total_cultivable_acres")
    historical_yields = data.get("historical_yields", {})
    soil_quality = data.get("soil_quality")

    if crops:
        crop_names = [c.get("name", "unknown") for c in crops]
        results.append(_stmt(
            f"Property cultivates {len(crops)} crop type(s): {', '.join(crop_names)}.",
            "FACT", "HIGH",
            "Enumerated from provided crop list.",
            f"crops=[{', '.join(crop_names)}]",
        ))

        # Diversification
        if len(crops) == 1:
            results.append(_stmt(
                "Single-crop operation carries elevated concentration risk — "
                "adverse weather, pests, or price drops in one commodity affect 100% of revenue.",
                "INFERENCE", "HIGH",
                "Single-commodity exposure is a well-established agricultural risk factor.",
                f"crop_count=1 ({crop_names[0]})",
            ))
        elif len(crops) >= 3:
            results.append(_stmt(
                "Multi-crop diversification across 3+ commodities provides meaningful "
                "revenue hedging against single-commodity price shocks.",
                "INFERENCE", "HIGH",
                "Diversification reduces portfolio variance — standard risk principle.",
                f"crop_count={len(crops)}",
            ))

        # Revenue mix
        total_revenue = sum(c.get("revenue", 0) for c in crops)
        if total_revenue > 0:
            results.append(_stmt(
                f"Total crop revenue is ${total_revenue:,.0f}.",
                "FACT", "HIGH",
                "Sum of per-crop revenue figures.",
                "sum(crops[].revenue)",
            ))
            for crop in crops:
                rev = crop.get("revenue", 0)
                if rev > 0:
                    share = (rev / total_revenue) * 100
                    results.append(_stmt(
                        f"{crop.get('name', 'Unknown')} contributes {share:.0f}% of "
                        f"crop revenue (${rev:,.0f}).",
                        "FACT", "HIGH",
                        "Revenue share calculation.",
                        f"{crop.get('name')}.revenue / total_revenue",
                    ))

    # Yield trends
    if historical_yields:
        for crop_name, yields_by_year in historical_yields.items():
            if len(yields_by_year) >= 2:
                sorted_years = sorted(yields_by_year.keys())
                values = [yields_by_year[y] for y in sorted_years]
                avg_yield = statistics.mean(values)
                latest_yield = values[-1]
                trend_pct = ((latest_yield - avg_yield) / avg_yield) * 100 if avg_yield else 0
                direction = "above" if trend_pct > 0 else "below"
                results.append(_stmt(
                    f"{crop_name} latest yield ({latest_yield:,.0f} bu/acre) is "
                    f"{abs(trend_pct):.1f}% {direction} the {len(values)}-year "
                    f"average of {avg_yield:,.0f} bu/acre.",
                    "FACT", "HIGH",
                    "Comparison of most recent year to historical mean.",
                    f"historical_yields.{crop_name}",
                ))
                if len(values) >= 3:
                    yield_std = statistics.stdev(values)
                    cv = (yield_std / avg_yield) * 100 if avg_yield else 0
                    stability = "stable" if cv < 10 else "moderate" if cv < 20 else "volatile"
                    results.append(_stmt(
                        f"{crop_name} yield variability is {stability} "
                        f"(CV = {cv:.1f}%, std = {yield_std:.0f} bu/acre).",
                        "INFERENCE", "MEDIUM",
                        "Coefficient of variation thresholds: <10% stable, 10-20% moderate, >20% volatile.",
                        f"stdev(historical_yields.{crop_name})",
                    ))

    if soil_quality:
        results.append(_stmt(
            f"Soil quality is rated '{soil_quality}'.",
            "FACT", "HIGH",
            "Reported soil quality classification.",
            f"soil_quality={soil_quality}",
        ))

    return results


def _analyze_exit_analysis(data: dict) -> list[dict]:
    """Generate FACT + INFERENCE statements for an exit_analysis section."""
    results: list[dict] = []

    hold_period = data.get("hold_period_years")
    projected_exit_value = data.get("projected_exit_value")
    purchase_price = data.get("purchase_price")
    market_liquidity = data.get("market_liquidity")
    buyer_pool = data.get("buyer_pool")
    appreciation_rate = data.get("annual_appreciation_pct")
    cap_rate_compression = data.get("cap_rate_compression_bps")
    total_noi_over_hold = data.get("total_noi_over_hold")

    if hold_period and purchase_price and appreciation_rate:
        projected = purchase_price * ((1 + appreciation_rate / 100) ** hold_period)
        total_return_pct = ((projected - purchase_price) / purchase_price) * 100
        results.append(_stmt(
            f"At {appreciation_rate}% annual appreciation over {hold_period} years, "
            f"projected exit value is ${projected:,.0f} "
            f"({total_return_pct:.1f}% total capital gain on ${purchase_price:,.0f}).",
            "INFERENCE", "MEDIUM",
            "Straight-line appreciation assumption; actual path may vary.",
            f"purchase_price={purchase_price}, appreciation={appreciation_rate}%, "
            f"hold={hold_period}yr",
        ))

    if projected_exit_value and purchase_price:
        gross_gain = projected_exit_value - purchase_price
        if total_noi_over_hold:
            total_return = gross_gain + total_noi_over_hold
            roi_pct = (total_return / purchase_price) * 100
            annual_roi = roi_pct / hold_period if hold_period else roi_pct
            results.append(_stmt(
                f"Total return including NOI: ${total_return:,.0f} "
                f"({roi_pct:.1f}% cumulative, ~{annual_roi:.1f}% annualized). "
                f"Capital gain ${gross_gain:,.0f} + cumulative NOI ${total_noi_over_hold:,.0f}.",
                "INFERENCE", "MEDIUM",
                "Combines projected appreciation with cumulative cash flow; "
                "does not account for time-value discounting.",
                "projected_exit_value + total_noi_over_hold - purchase_price",
            ))

    if market_liquidity:
        liquidity_map = {"high": "under 6 months", "medium": "6-18 months", "low": "18+ months"}
        est_time = liquidity_map.get(market_liquidity, "unknown")
        results.append(_stmt(
            f"Market liquidity is '{market_liquidity}' — estimated time to exit: {est_time}.",
            "FACT" if market_liquidity in liquidity_map else "INFERENCE",
            "MEDIUM",
            "Liquidity-to-timeline mapping based on typical ag-land transaction cycles.",
            f"market_liquidity={market_liquidity}",
        ))

    if buyer_pool:
        pool_desc = buyer_pool if isinstance(buyer_pool, str) else ", ".join(buyer_pool)
        depth = len(buyer_pool) if isinstance(buyer_pool, list) else 1
        results.append(_stmt(
            f"Potential buyer pool includes: {pool_desc}.",
            "FACT", "MEDIUM",
            "Buyer pool breadth is subjective and market-dependent.",
            f"buyer_pool={pool_desc}",
        ))
        if depth >= 3:
            results.append(_stmt(
                "Diverse buyer pool (3+ categories) supports exit optionality "
                "and competitive bidding at disposition.",
                "INFERENCE", "MEDIUM",
                "Multiple buyer types reduce dependency on single-market segment.",
                f"buyer_pool_depth={depth}",
            ))

    if cap_rate_compression is not None:
        direction = "compression" if cap_rate_compression > 0 else "expansion"
        value_impact = "increases" if cap_rate_compression > 0 else "decreases"
        results.append(_stmt(
            f"Projected cap-rate {direction} of {abs(cap_rate_compression)} bps "
            f"{value_impact} terminal value beyond NOI growth alone.",
            "INFERENCE", "LOW",
            "Cap-rate forecasts are inherently uncertain and depend on macro conditions.",
            f"cap_rate_compression_bps={cap_rate_compression}",
        ))

    return results


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_DETERMINISTIC_HANDLERS: dict[str, Any] = {
    "land_values": _analyze_land_values,
    "cap_rate": _analyze_cap_rate,
    "risk_assessment": _analyze_risk_assessment,
    "crop_production": _analyze_crop_production,
    "exit_analysis": _analyze_exit_analysis,
}


def _synthesize_deterministic(section_name: str, section_data: dict) -> list[dict]:
    """Rule-based fallback that generates structured statements from raw data.

    Produces FACT statements from direct data and simple INFERENCE statements
    from basic calculations and benchmark comparisons.

    Args:
        section_name: One of the supported section identifiers.
        section_data: The data dict for this section.

    Returns:
        A list of statement dicts conforming to the output schema.
    """
    handler = _DETERMINISTIC_HANDLERS.get(section_name)
    if handler is None:
        return [_stmt(
            f"No deterministic analyser available for section '{section_name}'.",
            "FACT", "LOW",
            "Unsupported section — no rules defined.",
            "system",
        )]
    return handler(section_data)


def analyze_section(
    section_name: str,
    section_data: dict,
    raw_data: dict | None = None,
    use_llm: bool = True,
) -> list[dict]:
    """Analyse a single underwriting section and return structured statements.

    Routing logic:
        1. If *use_llm* is True and an API key is available, call the
           appropriate LLM (Claude Opus for complex sections, Gemini for the
           rest).
        2. Always fall back to ``_synthesize_deterministic`` if the LLM call
           fails or no API key is present.

    Args:
        section_name: Identifier — must be in ``SUPPORTED_SECTIONS``.
        section_data: The data dict for this section.
        raw_data: Optional full underwriting dataset for cross-reference.
        use_llm: Whether to attempt LLM calls (set False to force deterministic).

    Returns:
        A list of statement dicts conforming to the output schema.

    Raises:
        ValueError: If *section_name* is not in ``SUPPORTED_SECTIONS``.
    """
    if section_name not in SUPPORTED_SECTIONS:
        raise ValueError(
            f"Unknown section '{section_name}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_SECTIONS))}"
        )

    # Attempt LLM route
    if use_llm:
        prompt = _build_analysis_prompt(section_name, section_data, raw_data)

        if section_name in COMPLEX_SECTIONS:
            llm_result = _call_claude(prompt)
        else:
            llm_result = _call_gemini(prompt)

        if llm_result is not None and isinstance(llm_result, list):
            return llm_result

    # Deterministic fallback
    return _synthesize_deterministic(section_name, section_data)


# ---------------------------------------------------------------------------
# Cross-section synthesis
# ---------------------------------------------------------------------------

def synthesize_report(all_sections: dict[str, list[dict]]) -> dict:
    """Produce a cross-section executive summary from per-section statements.

    Identifies key themes, risk factors, and opportunities by scanning
    all statement lists.

    Args:
        all_sections: Mapping of section_name -> list of statement dicts.

    Returns:
        A dict with keys: executive_summary, key_findings, risk_factors,
        opportunities.
    """
    key_findings: list[str] = []
    risk_factors: list[str] = []
    opportunities: list[str] = []

    # Collect high-confidence facts and inferences
    for section_name, statements in all_sections.items():
        for s in statements:
            text = s.get("statement", "")
            stype = s.get("type", "")
            confidence = s.get("confidence", "")

            # Classify into buckets
            lower = text.lower()
            is_risk = any(kw in lower for kw in [
                "risk", "decline", "volatile", "elevated", "not secured",
                "exceeds", "critical", "high risk", "single-crop",
                "compression",
            ])
            is_opportunity = any(kw in lower for kw in [
                "above", "premium", "diversification", "strong",
                "appreciation", "competitive bidding", "optionality",
                "stable", "hedging",
            ])

            if is_risk:
                risk_factors.append(f"[{section_name}] {text}")
            elif is_opportunity:
                opportunities.append(f"[{section_name}] {text}")

            if confidence == "HIGH" and stype == "FACT":
                key_findings.append(f"[{section_name}] {text}")
            elif confidence in ("HIGH", "MEDIUM") and stype == "INFERENCE":
                key_findings.append(f"[{section_name}] {text}")

    # Deduplicate while preserving order
    def _dedup(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    key_findings = _dedup(key_findings)
    risk_factors = _dedup(risk_factors)
    opportunities = _dedup(opportunities)

    # Build executive summary
    total_statements = sum(len(stmts) for stmts in all_sections.values())
    sections_covered = ", ".join(sorted(all_sections.keys()))

    summary_parts: list[str] = [
        f"This underwriting analysis covers {len(all_sections)} section(s) "
        f"({sections_covered}) with {total_statements} total analytical statements.",
    ]

    if risk_factors:
        summary_parts.append(
            f"  {len(risk_factors)} risk factor(s) were identified, "
            "requiring attention in due diligence."
        )
    if opportunities:
        summary_parts.append(
            f"  {len(opportunities)} potential opportunity/opportunities were identified "
            "that may enhance returns."
        )

    executive_summary = "\n".join(summary_parts)

    return {
        "executive_summary": executive_summary,
        "key_findings": key_findings,
        "risk_factors": risk_factors,
        "opportunities": opportunities,
    }


# ---------------------------------------------------------------------------
# Main — sample run in deterministic mode
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pprint

    # -----------------------------------------------------------------------
    # Realistic sample underwriting data: 640-acre irrigated farm in the
    # Texas Panhandle (Deaf Smith County)
    # -----------------------------------------------------------------------
    sample_data: dict[str, dict] = {
        "land_values": {
            "price_per_acre": 3_200,
            "total_acres": 640,
            "asking_price": 2_250_000,
            "improvements_value": 200_000,
            "comparable_sales": [
                {"parcel_id": "DS-2024-001", "price_per_acre": 3_050, "acres": 480, "date": "2024-11"},
                {"parcel_id": "DS-2024-007", "price_per_acre": 3_400, "acres": 320, "date": "2024-08"},
                {"parcel_id": "DS-2023-015", "price_per_acre": 2_900, "acres": 640, "date": "2023-12"},
                {"parcel_id": "DS-2024-022", "price_per_acre": 3_150, "acres": 512, "date": "2024-06"},
            ],
            "historical_prices": {
                "2018": 2_100,
                "2019": 2_250,
                "2020": 2_400,
                "2021": 2_550,
                "2022": 2_800,
                "2023": 3_000,
                "2024": 3_200,
            },
        },
        "cap_rate": {
            "noi": 72_000,
            "property_value": 2_250_000,
            "rental_income": 115_000,
            "operating_expenses": 43_000,
            "property_type": "farmland",
            "lease_terms": {
                "remaining_years": 7,
                "annual_escalation_pct": 2.5,
                "tenant": "Panhandle Grain Co-op",
            },
        },
        "risk_assessment": {
            "overall_risk_score": 6,
            "risk_factors": {
                "water": {
                    "score": 8,
                    "aquifer_decline_rate": 1.8,
                    "water_rights_secured": True,
                    "source": "Ogallala Aquifer",
                },
                "climate": {
                    "score": 6,
                    "drought_frequency": "moderate-high",
                    "flood_zone": "X",
                    "hail_risk": "elevated",
                },
                "market": {
                    "score": 4,
                    "commodity_price_volatility": "moderate",
                    "local_demand_trend": "stable",
                },
                "regulatory": {
                    "score": 3,
                    "groundwater_district_restrictions": True,
                    "conservation_easement": False,
                },
                "operational": {
                    "score": 5,
                    "equipment_condition": "good",
                    "irrigation_system_age_years": 12,
                },
                "financial": {
                    "score": 4,
                    "debt_service_coverage": 1.45,
                    "ltv": 0.65,
                },
            },
        },
        "crop_production": {
            "total_cultivable_acres": 600,
            "soil_quality": "Class II — good (moderate limitations)",
            "crops": [
                {"name": "Corn", "acres": 320, "yield_bu_per_acre": 190, "revenue": 245_000},
                {"name": "Winter Wheat", "acres": 180, "yield_bu_per_acre": 52, "revenue": 68_000},
                {"name": "Grain Sorghum", "acres": 100, "yield_bu_per_acre": 95, "revenue": 42_000},
            ],
            "historical_yields": {
                "Corn": {"2020": 175, "2021": 195, "2022": 180, "2023": 200, "2024": 190},
                "Winter Wheat": {"2020": 48, "2021": 55, "2022": 45, "2023": 58, "2024": 52},
            },
        },
        "exit_analysis": {
            "hold_period_years": 7,
            "purchase_price": 2_250_000,
            "annual_appreciation_pct": 4.5,
            "projected_exit_value": 3_050_000,
            "total_noi_over_hold": 540_000,
            "market_liquidity": "medium",
            "buyer_pool": [
                "institutional ag funds",
                "neighbouring operators",
                "1031 exchange buyers",
                "conservation trusts",
            ],
            "cap_rate_compression_bps": 25,
        },
    }

    # Run analysis for every section
    print("=" * 80)
    print("MMV LLM ANALYST — DETERMINISTIC MODE")
    print("Property: 640-acre irrigated farm, Deaf Smith County, Texas Panhandle")
    print("=" * 80)

    all_results: dict[str, list[dict]] = {}

    for section_name, section_data in sample_data.items():
        print(f"\n{'─' * 80}")
        print(f"SECTION: {section_name}")
        print(f"{'─' * 80}")
        statements = analyze_section(
            section_name=section_name,
            section_data=section_data,
            raw_data=sample_data,
            use_llm=True,  # Will fall back to deterministic — no API keys
        )
        all_results[section_name] = statements
        for i, stmt in enumerate(statements, 1):
            print(f"\n  [{i}] ({stmt['type']}, {stmt['confidence']})")
            print(f"      {stmt['statement']}")
            print(f"      Reason: {stmt['confidence_reason']}")
            print(f"      Source: {stmt['source_citation']}")

    # Synthesise cross-section report
    print(f"\n{'=' * 80}")
    print("EXECUTIVE SUMMARY")
    print(f"{'=' * 80}")
    report = synthesize_report(all_results)
    print(f"\n{report['executive_summary']}")

    print(f"\n--- Key Findings ({len(report['key_findings'])}) ---")
    for finding in report["key_findings"]:
        print(f"  • {finding}")

    print(f"\n--- Risk Factors ({len(report['risk_factors'])}) ---")
    for risk in report["risk_factors"]:
        print(f"  ⚠ {risk}")

    print(f"\n--- Opportunities ({len(report['opportunities'])}) ---")
    for opp in report["opportunities"]:
        print(f"  ✦ {opp}")

    print(f"\n{'=' * 80}")
    print("Analysis complete. All output generated in deterministic fallback mode.")
    print(f"{'=' * 80}")
