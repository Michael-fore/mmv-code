"""Tests for mmv_underwriting.engine — chain runner, validation, and introspection."""

from mmv_underwriting.engine import run_chain, describe_step, describe_chain, validate_chain


# ── Helpers: tiny steps for testing the engine itself ────────────────

def step_add_ten(deal):
    """Add ten to value.

    Needs: value
    Adds: plus_ten
    """
    deal["plus_ten"] = deal["value"] + 10
    return deal


def step_double(deal):
    """Double the plus_ten result.

    Needs: plus_ten
    Adds: doubled
    """
    deal["doubled"] = deal["plus_ten"] * 2
    return deal


def step_needs_missing(deal):
    """Step that needs something nobody provides.

    Needs: nonexistent_key
    Adds: result
    """
    deal["result"] = deal["nonexistent_key"]
    return deal


# ── run_chain ────────────────────────────────────────────────────────

def test_run_chain_single_step():
    deal = {"value": 5}
    result = run_chain(deal, [step_add_ten])
    assert result["plus_ten"] == 15


def test_run_chain_multiple_steps():
    deal = {"value": 5}
    result = run_chain(deal, [step_add_ten, step_double])
    assert result["plus_ten"] == 15
    assert result["doubled"] == 30


def test_run_chain_empty_steps():
    deal = {"value": 5}
    result = run_chain(deal, [])
    assert result == {"value": 5}


def test_run_chain_preserves_existing_keys():
    deal = {"value": 5, "extra": "keep_me"}
    result = run_chain(deal, [step_add_ten])
    assert result["extra"] == "keep_me"


# ── describe_step ────────────────────────────────────────────────────

def test_describe_step_extracts_needs_and_adds():
    info = describe_step(step_add_ten)
    assert info["name"] == "step_add_ten"
    assert "value" in info["needs"]
    assert "plus_ten" in info["adds"]


def test_describe_step_no_docstring():
    def bare_step(deal):
        return deal

    info = describe_step(bare_step)
    assert info["needs"] == []
    assert info["adds"] == []


# ── describe_chain ───────────────────────────────────────────────────

def test_describe_chain_returns_list():
    chain = [step_add_ten, step_double]
    descriptions = describe_chain(chain)
    assert len(descriptions) == 2
    assert descriptions[0]["name"] == "step_add_ten"
    assert descriptions[1]["name"] == "step_double"


# ── validate_chain ───────────────────────────────────────────────────

def test_validate_chain_valid():
    deal = {"value": 5}
    errors = validate_chain(deal, [step_add_ten, step_double])
    assert errors == []


def test_validate_chain_missing_initial_key():
    deal = {}  # missing "value"
    errors = validate_chain(deal, [step_add_ten])
    assert len(errors) == 1
    assert "step_add_ten" in errors[0]


def test_validate_chain_missing_intermediate_key():
    deal = {"value": 5}
    # step_double needs plus_ten, but we skip step_add_ten
    errors = validate_chain(deal, [step_double])
    assert len(errors) == 1
    assert "step_double" in errors[0]


def test_validate_chain_detects_multiple_errors():
    deal = {}
    errors = validate_chain(deal, [step_add_ten, step_needs_missing])
    assert len(errors) == 2
