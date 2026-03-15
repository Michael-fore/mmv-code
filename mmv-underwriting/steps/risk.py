"""Risk scoring steps.

Each risk scorer adds a 0-100 score (0 = no risk, 100 = extreme risk)
and a categorical label. All scores are independent and can run in any order.
aggregate_risk combines them into a weighted composite.
"""


def score_drought_risk(deal: dict) -> dict:
    """Score drought exposure based on historical drought frequency.

    Needs: drought_history
    Adds: drought_risk_score, drought_risk_label

    drought_history should have: {"pct_weeks_in_drought": float, "max_severity": str}
    """
    pct = deal["drought_history"]["pct_weeks_in_drought"]
    severity_map = {"D0": 10, "D1": 25, "D2": 50, "D3": 75, "D4": 100}
    max_sev = severity_map.get(deal["drought_history"]["max_severity"], 0)

    # Weighted: 60% frequency, 40% max severity
    score = min(100, round(pct * 0.6 + max_sev * 0.4))

    if score < 20:
        label = "low"
    elif score < 50:
        label = "moderate"
    elif score < 75:
        label = "high"
    else:
        label = "extreme"

    deal["drought_risk_score"] = score
    deal["drought_risk_label"] = label
    return deal


def score_soil_risk(deal: dict) -> dict:
    """Score soil quality risk based on CSR2/NCCPI ratings.

    Needs: soil_data
    Adds: soil_risk_score, soil_risk_label

    soil_data should have: {"avg_csr2": float} (0-100 scale, higher = better)
    """
    csr2 = deal["soil_data"]["avg_csr2"]

    # Invert: high CSR2 = low risk
    score = max(0, min(100, round(100 - csr2)))

    if score < 20:
        label = "low"
    elif score < 40:
        label = "moderate"
    elif score < 65:
        label = "high"
    else:
        label = "extreme"

    deal["soil_risk_score"] = score
    deal["soil_risk_label"] = label
    return deal


def score_commodity_risk(deal: dict) -> dict:
    """Score commodity price volatility risk.

    Needs: commodity_data
    Adds: commodity_risk_score, commodity_risk_label

    commodity_data should have: {"price_volatility_pct": float, "trend": str}
    trend is one of: "rising", "stable", "declining"
    """
    vol = deal["commodity_data"]["price_volatility_pct"]
    trend = deal["commodity_data"]["trend"]

    trend_adj = {"rising": -10, "stable": 0, "declining": 15}
    score = max(0, min(100, round(vol * 2 + trend_adj.get(trend, 0))))

    if score < 20:
        label = "low"
    elif score < 50:
        label = "moderate"
    elif score < 75:
        label = "high"
    else:
        label = "extreme"

    deal["commodity_risk_score"] = score
    deal["commodity_risk_label"] = label
    return deal


def aggregate_risk(deal: dict) -> dict:
    """Combine individual risk scores into a weighted composite.

    Needs: drought_risk_score, soil_risk_score, commodity_risk_score
    Adds: composite_risk_score, composite_risk_label

    Default weights: drought 35%, soil 35%, commodity 30%.
    Override with risk_weights dict if present.
    """
    weights = deal.get("risk_weights", {
        "drought": 0.35,
        "soil": 0.35,
        "commodity": 0.30,
    })

    composite = (
        deal["drought_risk_score"] * weights["drought"]
        + deal["soil_risk_score"] * weights["soil"]
        + deal["commodity_risk_score"] * weights["commodity"]
    )
    score = round(composite)

    if score < 20:
        label = "low"
    elif score < 50:
        label = "moderate"
    elif score < 75:
        label = "high"
    else:
        label = "extreme"

    deal["composite_risk_score"] = score
    deal["composite_risk_label"] = label
    return deal
