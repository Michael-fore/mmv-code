"""Tests for mmv_data.assembler — deal assembly and data transforms."""

import pytest

from mmv_data.assembler import (
    assemble_deal,
    _unwrap,
    _cash_rent_from_usda,
    _cap_rate_from_usda,
    _drought_history_from_monitor,
    _soil_data_from_ssurgo,
    _commodity_data_from_production,
    DEFAULTS,
)


# ── _unwrap ──────────────────────────────────────────────────────────

def test_unwrap_extracts_value():
    result = {"value": {"foo": 1}, "provenance": {"source": "test"}}
    assert _unwrap(result) == {"foo": 1}


# ── Transform helpers (use mock data from fetchers) ──────────────────

class TestCashRentFromUSDA:
    def test_returns_float(self):
        rent = _cash_rent_from_usda("IA")
        assert isinstance(rent, (int, float))
        assert rent > 0

    def test_different_states_can_differ(self):
        # Mock data is deterministic but may vary by state
        ia = _cash_rent_from_usda("IA")
        tx = _cash_rent_from_usda("TX")
        # Both should be valid positive numbers
        assert ia > 0
        assert tx > 0


class TestCapRateFromUSDA:
    def test_returns_positive_rate(self):
        rate = _cap_rate_from_usda("IA", 200.0)
        assert 0 < rate < 1  # should be a reasonable percentage

    def test_higher_rent_means_higher_cap_rate(self):
        low = _cap_rate_from_usda("IA", 100.0)
        high = _cap_rate_from_usda("IA", 300.0)
        assert high > low


class TestDroughtTransform:
    def test_returns_expected_shape(self):
        result = _drought_history_from_monitor("TX", "48")
        assert "pct_weeks_in_drought" in result
        assert "max_severity" in result
        assert result["max_severity"] in ("D0", "D1", "D2", "D3", "D4")

    def test_pct_is_numeric(self):
        result = _drought_history_from_monitor("TX", "48")
        assert isinstance(result["pct_weeks_in_drought"], (int, float))


class TestSoilTransform:
    def test_returns_expected_shape(self):
        result = _soil_data_from_ssurgo("IA", "19169")
        assert "avg_csr2" in result
        assert isinstance(result["avg_csr2"], (int, float))

    def test_csr2_in_valid_range(self):
        result = _soil_data_from_ssurgo("IA", "19169")
        assert 0 <= result["avg_csr2"] <= 100


class TestCommodityTransform:
    def test_returns_expected_shape(self):
        result = _commodity_data_from_production("IA")
        assert "price_volatility_pct" in result
        assert "trend" in result
        assert result["trend"] in ("rising", "stable", "declining")

    def test_volatility_is_positive(self):
        result = _commodity_data_from_production("IA")
        assert result["price_volatility_pct"] > 0


# ── assemble_deal ────────────────────────────────────────────────────

class TestAssembleDeal:
    def test_returns_all_required_keys(self):
        deal = assemble_deal(
            lat=41.88, lon=-93.63,
            acres=160, tillable_acres=152,
            purchase_price=1_600_000,
            equity_invested=800_000,
            state="IA", county_fips="19169",
        )
        required = [
            "acres", "tillable_acres", "cash_rent_per_acre", "vacancy_rate",
            "hold_years", "revenue_growth_rate", "tax_per_acre",
            "insurance_per_acre", "management_rate", "maintenance_per_acre",
            "expense_growth_rate", "cap_rate", "purchase_price",
            "equity_invested", "exit_cap_rate", "selling_cost_rate",
            "drought_history", "soil_data", "commodity_data", "comp_sales",
        ]
        for key in required:
            assert key in deal, f"Missing key: {key}"

    def test_defaults_applied(self):
        deal = assemble_deal(
            lat=41.88, lon=-93.63,
            acres=160, tillable_acres=152,
            purchase_price=1_600_000,
            equity_invested=800_000,
            state="IA", county_fips="19169",
        )
        for key, default in DEFAULTS.items():
            assert key in deal

    def test_overrides_win(self):
        deal = assemble_deal(
            lat=41.88, lon=-93.63,
            acres=160, tillable_acres=152,
            purchase_price=1_600_000,
            equity_invested=800_000,
            state="IA", county_fips="19169",
            overrides={"hold_years": 7, "vacancy_rate": 0.10},
        )
        assert deal["hold_years"] == 7
        assert deal["vacancy_rate"] == 0.10

    def test_cash_rent_override(self):
        deal = assemble_deal(
            lat=41.88, lon=-93.63,
            acres=160, tillable_acres=152,
            purchase_price=1_600_000,
            equity_invested=800_000,
            state="IA", county_fips="19169",
            overrides={"cash_rent_per_acre": 300.0},
        )
        assert deal["cash_rent_per_acre"] == 300.0

    def test_cap_rate_override(self):
        deal = assemble_deal(
            lat=41.88, lon=-93.63,
            acres=160, tillable_acres=152,
            purchase_price=1_600_000,
            equity_invested=800_000,
            state="IA", county_fips="19169",
            overrides={"cap_rate": 0.05},
        )
        assert deal["cap_rate"] == 0.05

    def test_comp_sales_passed_through(self):
        comps = [{"price_per_acre": 10_000, "acres": 80, "csr2": 85}]
        deal = assemble_deal(
            lat=41.88, lon=-93.63,
            acres=160, tillable_acres=152,
            purchase_price=1_600_000,
            equity_invested=800_000,
            state="IA", county_fips="19169",
            comp_sales=comps,
        )
        assert deal["comp_sales"] == comps

    def test_state_fips_derived_from_county(self):
        deal = assemble_deal(
            lat=41.88, lon=-93.63,
            acres=160, tillable_acres=152,
            purchase_price=1_600_000,
            equity_invested=800_000,
            state="IA", county_fips="19169",
        )
        # Should work without specifying state_fips
        assert "drought_history" in deal

    def test_end_to_end_with_underwriting(self):
        """Assembled deal runs through the full underwriting chain."""
        from mmv_underwriting.engine import run_chain, validate_chain
        from mmv_underwriting.chains import farmland_underwrite

        deal = assemble_deal(
            lat=41.88, lon=-93.63,
            acres=160, tillable_acres=152,
            purchase_price=1_600_000,
            equity_invested=800_000,
            state="IA", county_fips="19169",
            comp_sales=[
                {"price_per_acre": 10_000, "acres": 80, "csr2": 85},
            ],
        )

        errors = validate_chain(deal, farmland_underwrite)
        assert errors == [], f"Validation failed: {errors}"

        result = run_chain(deal, farmland_underwrite)
        assert "irr" in result
        assert "composite_risk_score" in result
        assert isinstance(result["irr"], float)
