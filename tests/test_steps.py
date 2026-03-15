"""Tests for every underwriting step — revenue through exit analysis."""

import pytest

from mmv_underwriting.steps.revenue import project_revenue
from mmv_underwriting.steps.expenses import project_expenses
from mmv_underwriting.steps.noi import project_noi
from mmv_underwriting.steps.valuation import apply_cap_rate, value_by_comps
from mmv_underwriting.steps.risk import (
    score_drought_risk,
    score_soil_risk,
    score_commodity_risk,
    aggregate_risk,
)
from mmv_underwriting.steps.returns import (
    compute_irr,
    compute_cash_on_cash,
    compute_equity_multiple,
    compute_dscr,
)
from mmv_underwriting.steps.exit_analysis import compute_exit


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def base_deal():
    """Minimal deal dict with all keys needed by revenue + expenses."""
    return {
        "acres": 160,
        "tillable_acres": 152,
        "cash_rent_per_acre": 250.0,
        "vacancy_rate": 0.05,
        "hold_years": 5,
        "revenue_growth_rate": 0.02,
        "tax_per_acre": 15.0,
        "insurance_per_acre": 8.0,
        "management_rate": 0.08,
        "maintenance_per_acre": 5.0,
        "expense_growth_rate": 0.025,
        "cap_rate": 0.03,
        "purchase_price": 1_600_000,
        "equity_invested": 800_000,
        "annual_debt_service": 0,
        "exit_cap_rate": 0.035,
        "selling_cost_rate": 0.04,
    }


# ── Revenue ──────────────────────────────────────────────────────────

class TestRevenue:
    def test_gross_revenue_year1(self, base_deal):
        result = project_revenue(base_deal)
        expected_gross = 152 * 250.0  # tillable * rent
        assert result["gross_revenue"] == expected_gross

    def test_effective_gross_income_applies_vacancy(self, base_deal):
        result = project_revenue(base_deal)
        expected_egi = 152 * 250.0 * (1 - 0.05)
        assert result["effective_gross_income"] == expected_egi

    def test_revenue_schedule_length(self, base_deal):
        result = project_revenue(base_deal)
        assert len(result["revenue_schedule"]) == 5

    def test_revenue_grows_over_time(self, base_deal):
        result = project_revenue(base_deal)
        sched = result["revenue_schedule"]
        for i in range(1, len(sched)):
            assert sched[i]["gross_revenue"] > sched[i - 1]["gross_revenue"]

    def test_zero_vacancy_means_gross_equals_egi(self, base_deal):
        base_deal["vacancy_rate"] = 0.0
        result = project_revenue(base_deal)
        assert result["gross_revenue"] == result["effective_gross_income"]


# ── Expenses ─────────────────────────────────────────────────────────

class TestExpenses:
    def test_expense_schedule_length(self, base_deal):
        project_revenue(base_deal)
        result = project_expenses(base_deal)
        assert len(result["expense_schedule"]) == 5

    def test_expenses_grow_over_time(self, base_deal):
        project_revenue(base_deal)
        result = project_expenses(base_deal)
        sched = result["expense_schedule"]
        for i in range(1, len(sched)):
            assert sched[i]["total_expenses"] > sched[i - 1]["total_expenses"]

    def test_year1_taxes(self, base_deal):
        project_revenue(base_deal)
        result = project_expenses(base_deal)
        year1 = result["expense_schedule"][0]
        assert year1["taxes"] == 160 * 15.0  # acres * tax_per_acre


# ── NOI ──────────────────────────────────────────────────────────────

class TestNOI:
    def test_noi_equals_egi_minus_expenses(self, base_deal):
        project_revenue(base_deal)
        project_expenses(base_deal)
        result = project_noi(base_deal)
        sched = result["noi_schedule"]
        for entry in sched:
            assert abs(entry["noi"] - (entry["effective_gross_income"] - entry["total_expenses"])) < 0.01

    def test_noi_year1_matches_top_level(self, base_deal):
        project_revenue(base_deal)
        project_expenses(base_deal)
        result = project_noi(base_deal)
        assert result["noi"] == result["noi_schedule"][0]["noi"]

    def test_noi_is_positive_for_typical_inputs(self, base_deal):
        project_revenue(base_deal)
        project_expenses(base_deal)
        result = project_noi(base_deal)
        assert result["noi"] > 0


# ── Valuation ────────────────────────────────────────────────────────

class TestCapRate:
    def test_cap_rate_value(self):
        deal = {"noi": 30_000, "cap_rate": 0.03, "acres": 100}
        result = apply_cap_rate(deal)
        assert result["cap_rate_value"] == 1_000_000.0
        assert result["price_per_acre_cap"] == 10_000.0

    def test_lower_cap_rate_means_higher_value(self):
        deal_low = apply_cap_rate({"noi": 30_000, "cap_rate": 0.02, "acres": 100})
        deal_high = apply_cap_rate({"noi": 30_000, "cap_rate": 0.05, "acres": 100})
        assert deal_low["cap_rate_value"] > deal_high["cap_rate_value"]


class TestComps:
    def test_comp_value_with_sales(self):
        comps = [
            {"price_per_acre": 10_000, "acres": 80, "csr2": 85},
            {"price_per_acre": 12_000, "acres": 120, "csr2": 90},
        ]
        deal = {"acres": 160, "comp_sales": comps}
        result = value_by_comps(deal)
        assert result["comp_price_per_acre"] == 11_000.0
        assert result["comp_value"] == 160 * 11_000.0
        assert result["comp_spread"] == 2_000.0

    def test_empty_comps_returns_none(self):
        deal = {"acres": 160, "comp_sales": []}
        result = value_by_comps(deal)
        assert result["comp_value"] is None
        assert result["comp_price_per_acre"] is None


# ── Risk Scoring ─────────────────────────────────────────────────────

class TestDroughtRisk:
    def test_low_drought(self):
        deal = {"drought_history": {"pct_weeks_in_drought": 5, "max_severity": "D0"}}
        result = score_drought_risk(deal)
        assert result["drought_risk_score"] < 20
        assert result["drought_risk_label"] == "low"

    def test_extreme_drought(self):
        deal = {"drought_history": {"pct_weeks_in_drought": 80, "max_severity": "D4"}}
        result = score_drought_risk(deal)
        assert result["drought_risk_score"] >= 75
        assert result["drought_risk_label"] == "extreme"

    def test_score_is_bounded(self):
        deal = {"drought_history": {"pct_weeks_in_drought": 200, "max_severity": "D4"}}
        result = score_drought_risk(deal)
        assert result["drought_risk_score"] <= 100


class TestSoilRisk:
    def test_high_csr2_is_low_risk(self):
        deal = {"soil_data": {"avg_csr2": 90}}
        result = score_soil_risk(deal)
        assert result["soil_risk_score"] <= 20
        assert result["soil_risk_label"] == "low"

    def test_low_csr2_is_high_risk(self):
        deal = {"soil_data": {"avg_csr2": 25}}
        result = score_soil_risk(deal)
        assert result["soil_risk_score"] >= 65
        assert result["soil_risk_label"] == "extreme"


class TestCommodityRisk:
    def test_low_volatility_stable(self):
        deal = {"commodity_data": {"price_volatility_pct": 5, "trend": "stable"}}
        result = score_commodity_risk(deal)
        assert result["commodity_risk_score"] < 20
        assert result["commodity_risk_label"] == "low"

    def test_declining_trend_increases_risk(self):
        base = {"price_volatility_pct": 20, "trend": "stable"}
        declining = {"price_volatility_pct": 20, "trend": "declining"}
        r1 = score_commodity_risk({"commodity_data": base})
        r2 = score_commodity_risk({"commodity_data": declining})
        assert r2["commodity_risk_score"] > r1["commodity_risk_score"]


class TestAggregateRisk:
    def test_aggregate_is_weighted_average(self):
        deal = {
            "drought_risk_score": 50,
            "soil_risk_score": 50,
            "commodity_risk_score": 50,
        }
        result = aggregate_risk(deal)
        assert result["composite_risk_score"] == 50

    def test_custom_weights(self):
        deal = {
            "drought_risk_score": 100,
            "soil_risk_score": 0,
            "commodity_risk_score": 0,
            "risk_weights": {"drought": 1.0, "soil": 0.0, "commodity": 0.0},
        }
        result = aggregate_risk(deal)
        assert result["composite_risk_score"] == 100

    def test_labels_assigned(self):
        for score, expected_label in [(10, "low"), (30, "moderate"), (60, "high"), (80, "extreme")]:
            deal = {
                "drought_risk_score": score,
                "soil_risk_score": score,
                "commodity_risk_score": score,
            }
            result = aggregate_risk(deal)
            assert result["composite_risk_label"] == expected_label


# ── Exit Analysis ────────────────────────────────────────────────────

class TestExit:
    def test_exit_value_computation(self):
        deal = {
            "noi_schedule": [{"noi": 30_000}, {"noi": 31_000}, {"noi": 32_000}],
            "exit_cap_rate": 0.04,
            "selling_cost_rate": 0.05,
            "purchase_price": 500_000,
        }
        result = compute_exit(deal)
        # terminal NOI = 32,000 (last year)
        assert result["terminal_noi"] == 32_000
        # gross exit = 32000 / 0.04 = 800,000
        assert result["gross_exit_value"] == 800_000.0
        # selling costs = 800000 * 0.05 = 40,000
        assert result["selling_costs"] == 40_000.0
        # net exit = 760,000
        assert result["exit_value"] == 760_000.0

    def test_appreciation_positive_when_value_exceeds_purchase(self):
        deal = {
            "noi_schedule": [{"noi": 50_000}] * 5,
            "exit_cap_rate": 0.03,
            "selling_cost_rate": 0.02,
            "purchase_price": 1_000_000,
        }
        result = compute_exit(deal)
        # gross exit = 50000/0.03 = 1,666,666.67 -> net ≈ 1,633,333
        assert result["total_appreciation"] > 0


# ── Returns ──────────────────────────────────────────────────────────

class TestCashOnCash:
    def test_all_cash_deal(self):
        deal = {"noi": 30_000, "equity_invested": 1_000_000, "annual_debt_service": 0}
        result = compute_cash_on_cash(deal)
        assert result["cash_on_cash"] == 0.03

    def test_leveraged_deal(self):
        deal = {"noi": 30_000, "equity_invested": 500_000, "annual_debt_service": 10_000}
        result = compute_cash_on_cash(deal)
        assert result["cash_on_cash"] == 0.04  # (30k - 10k) / 500k


class TestEquityMultiple:
    def test_equity_multiple(self):
        deal = {
            "equity_invested": 500_000,
            "noi_schedule": [{"noi": 30_000}] * 5,
            "exit_value": 600_000,
            "annual_debt_service": 0,
        }
        result = compute_equity_multiple(deal)
        # total = 5*30000 + 600000 = 750000; multiple = 750000/500000 = 1.5
        assert result["equity_multiple"] == 1.5


class TestDSCR:
    def test_dscr_with_debt(self):
        deal = {"noi": 50_000, "annual_debt_service": 25_000}
        result = compute_dscr(deal)
        assert result["dscr"] == 2.0

    def test_dscr_no_debt(self):
        deal = {"noi": 50_000, "annual_debt_service": 0}
        result = compute_dscr(deal)
        assert result["dscr"] is None


class TestIRR:
    def test_irr_known_case(self):
        """A deal that doubles money in ~5 years should have IRR near 15%."""
        deal = {
            "purchase_price": 100_000,
            "noi_schedule": [{"noi": 5_000}] * 5,
            "exit_value": 130_000,
        }
        result = compute_irr(deal)
        # Expected: ~10-11% IRR
        assert 0.05 < result["irr"] < 0.20

    def test_irr_break_even(self):
        """If you get back exactly what you paid, IRR ≈ 0."""
        deal = {
            "purchase_price": 100_000,
            "noi_schedule": [{"noi": 0}] * 3,
            "exit_value": 100_000,
        }
        result = compute_irr(deal)
        assert abs(result["irr"]) < 0.01

    def test_irr_negative_when_losing_money(self):
        deal = {
            "purchase_price": 100_000,
            "noi_schedule": [{"noi": 1_000}] * 5,
            "exit_value": 50_000,
        }
        result = compute_irr(deal)
        assert result["irr"] < 0


# ── Full Chain Integration ───────────────────────────────────────────

class TestFullChain:
    def test_farmland_underwrite_end_to_end(self, base_deal):
        """Run the full 14-step chain and verify all outputs exist."""
        from mmv_underwriting.engine import run_chain, validate_chain
        from mmv_underwriting.chains import farmland_underwrite

        # Add risk and comp inputs
        base_deal["drought_history"] = {"pct_weeks_in_drought": 30, "max_severity": "D2"}
        base_deal["soil_data"] = {"avg_csr2": 80}
        base_deal["commodity_data"] = {"price_volatility_pct": 15, "trend": "stable"}
        base_deal["comp_sales"] = [
            {"price_per_acre": 10_000, "acres": 80, "csr2": 85},
            {"price_per_acre": 11_000, "acres": 120, "csr2": 82},
        ]

        # Validate before running
        errors = validate_chain(base_deal, farmland_underwrite)
        assert errors == [], f"Chain validation failed: {errors}"

        result = run_chain(base_deal, farmland_underwrite)

        # Check all key outputs exist
        expected_keys = [
            "noi", "noi_schedule", "revenue_schedule", "expense_schedule",
            "cap_rate_value", "comp_value",
            "drought_risk_score", "soil_risk_score", "commodity_risk_score",
            "composite_risk_score", "composite_risk_label",
            "exit_value", "irr", "cash_on_cash", "equity_multiple", "dscr",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

        # Sanity checks on values
        assert result["noi"] > 0
        assert result["cap_rate_value"] > 0
        assert 0 <= result["composite_risk_score"] <= 100
        assert result["composite_risk_label"] in ("low", "moderate", "high", "extreme")

    def test_quick_valuation_chain(self, base_deal):
        from mmv_underwriting.engine import run_chain
        from mmv_underwriting.chains import quick_valuation

        base_deal["comp_sales"] = []
        result = run_chain(base_deal, quick_valuation)
        assert "noi" in result
        assert "cap_rate_value" in result
