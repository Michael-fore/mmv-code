"""Pre-built analysis chains.

Each chain is a list of steps that can be passed to run_chain().
These are starting points — LLMs and users can assemble custom chains
by picking steps from mmv_underwriting.steps.
"""

from mmv_underwriting.steps import (
    project_revenue,
    project_expenses,
    project_noi,
    apply_cap_rate,
    value_by_comps,
    score_drought_risk,
    score_soil_risk,
    score_commodity_risk,
    aggregate_risk,
    compute_exit,
    compute_irr,
    compute_cash_on_cash,
    compute_equity_multiple,
    compute_dscr,
)

# Full farmland underwriting — the canonical chain
farmland_underwrite = [
    project_revenue,
    project_expenses,
    project_noi,
    apply_cap_rate,
    value_by_comps,
    score_drought_risk,
    score_soil_risk,
    score_commodity_risk,
    aggregate_risk,
    compute_exit,
    compute_irr,
    compute_cash_on_cash,
    compute_equity_multiple,
    compute_dscr,
]

# Quick valuation only — skip risk and returns
quick_valuation = [
    project_revenue,
    project_expenses,
    project_noi,
    apply_cap_rate,
    value_by_comps,
]

# Risk assessment only — just the risk scores
risk_assessment = [
    score_drought_risk,
    score_soil_risk,
    score_commodity_risk,
    aggregate_risk,
]
