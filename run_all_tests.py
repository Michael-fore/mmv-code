"""
Comprehensive validation suite for all 6 MMV tasks.
Runs everything that doesn't require external credentials.
"""

import sys, os, json, traceback, importlib
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))

# Each repo's root contains a tools/ package. We add each root to sys.path
# but also add the tools dir directly as a fallback since modules do
# `from provenance import tag_provenance` within the same package.
for repo in ["mmv-data", "mmv-agent", "mmv-reporting"]:
    repo_path = os.path.join(BASE, repo)
    tools_path = os.path.join(repo_path, "tools")
    for p in [repo_path, tools_path]:
        if p not in sys.path:
            sys.path.insert(0, p)

PASS = 0
FAIL = 0
RESULTS = []

def test(name, fn):
    global PASS, FAIL
    try:
        result = fn()
        if result is True or result is None:
            PASS += 1
            RESULTS.append(("✅", name, "PASS"))
            print(f"  ✅ {name}")
        elif isinstance(result, str) and result.startswith("SKIP"):
            PASS += 1
            RESULTS.append(("⏭️", name, result))
            print(f"  ⏭️  {name}: {result}")
        else:
            FAIL += 1
            RESULTS.append(("❌", name, f"FAIL: {result}"))
            print(f"  ❌ {name}: {result}")
    except Exception as e:
        FAIL += 1
        tb = traceback.format_exc().split('\n')[-3].strip()
        RESULTS.append(("❌", name, f"ERROR: {e}"))
        print(f"  ❌ {name}: {e}")


# ════════════════════════════════════════════════════════════════
# TASK 1: Provenance Layer
# ════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  TASK 1: Provenance Layer")
print("═"*60)

def test_provenance_import():
    from provenance import tag_provenance, compute_freshness, unwrap, get_provenance
    return True

def test_provenance_structure():
    from provenance import tag_provenance
    result = tag_provenance(
        [{"val": 42}],
        source="Test",
        source_url="http://test.com",
        query_params={"key": "val"},
    )
    assert "value" in result, "Missing 'value' key"
    assert "provenance" in result, "Missing 'provenance' key"
    p = result["provenance"]
    for key in ["source", "source_url", "query_params", "fetched_at", "freshness", "is_mock"]:
        assert key in p, f"Missing provenance key: {key}"
    assert p["source"] == "Test"
    assert p["is_mock"] == False
    assert p["freshness"] == "current"
    assert result["value"] == [{"val": 42}]
    return True

def test_provenance_mock_flag():
    from provenance import tag_provenance
    result = tag_provenance([], source="X", source_url="", is_mock=True)
    assert result["provenance"]["is_mock"] == True
    return True

def test_provenance_freshness_categories():
    from provenance import compute_freshness
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert compute_freshness(now) == "current"
    assert compute_freshness("2020-01-01T00:00:00Z") == "very_stale"
    assert compute_freshness("invalid") == "unknown"
    return True

def test_provenance_unwrap():
    from provenance import tag_provenance, unwrap, get_provenance
    tagged = tag_provenance({"x": 1}, source="S", source_url="U")
    assert unwrap(tagged) == {"x": 1}
    assert get_provenance(tagged)["source"] == "S"
    assert unwrap({"plain": "data"}) == {"plain": "data"}
    assert get_provenance({"no": "provenance"}) is None
    return True

def test_provenance_empty_data():
    from provenance import tag_provenance
    result = tag_provenance([], source="Empty", source_url="")
    assert result["value"] == []
    assert result["provenance"]["source"] == "Empty"
    return True

def _test_fetcher_import(module_name, func_names):
    """Generic test: import a fetcher module and verify functions exist."""
    mod = importlib.import_module(module_name)
    for fn in func_names:
        assert hasattr(mod, fn), f"Missing function: {fn}"
    return True

def test_fred_import():     return _test_fetcher_import("fred", ["fetch_series", "fetch_all"])
def test_usda_import():     return _test_fetcher_import("usda", ["fetch_land_values", "fetch_cash_rents", "fetch_crop_production", "fetch_crop_production_api"])
def test_eia_import():      return _test_fetcher_import("eia", ["fetch_solar_generation", "fetch_all_generation_by_fuel"])
def test_noaa_import():     return _test_fetcher_import("noaa", ["fetch_monthly_climate"])
def test_drought_import():  return _test_fetcher_import("drought", ["fetch_drought_by_state"])
def test_census_import():   return _test_fetcher_import("census", ["fetch_county_population"])
def test_ssurgo_import():   return _test_fetcher_import("ssurgo", ["fetch_soil_summary"])
def test_usdafas_import():  return _test_fetcher_import("usda_fas", ["fetch_export_sales_report"])
def test_usdafsa_import():  return _test_fetcher_import("usda_fsa", ["fetch_crp_enrollment"])

test("Provenance module imports", test_provenance_import)
test("Provenance output structure", test_provenance_structure)
test("Provenance is_mock flag", test_provenance_mock_flag)
test("Freshness categories (current/very_stale/unknown)", test_provenance_freshness_categories)
test("Unwrap and get_provenance helpers", test_provenance_unwrap)
test("Provenance wraps empty data cleanly", test_provenance_empty_data)
test("fred.py imports with provenance", test_fred_import)
test("usda.py imports with provenance + API", test_usda_import)
test("eia.py imports with provenance", test_eia_import)
test("noaa.py imports with provenance", test_noaa_import)
test("drought.py imports with provenance", test_drought_import)
test("census.py imports with provenance", test_census_import)
test("ssurgo.py imports with provenance", test_ssurgo_import)
test("usda_fas.py imports with provenance", test_usdafas_import)
test("usda_fsa.py imports with provenance", test_usdafsa_import)


# ════════════════════════════════════════════════════════════════
# TASK 2: Report Generation
# ════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  TASK 2: Report Generation")
print("═"*60)

SAMPLE_UNDERWRITING = {
    "state": "TX",
    "summary": {
        "thesis": "FAVORABLE",
        "thesis_detail": "Strong signals",
        "signals": {"bullish": ["Growth +5%"], "bearish": [], "neutral": ["Moderate"]},
    },
    "sections": {
        "land_values": {
            "nominal_cagr_pct": 5.2, "real_cagr_pct": 2.1,
            "annual_volatility_pct": 3.8,
            "first_year": 2018, "last_year": 2023,
            "first_value": 2500, "last_value": 3400,
            "yoy_changes": [{"year": 2023, "change_pct": 6.3}],
        },
        "cap_rate": {
            "latest": {"year": 2023, "cap_rate_pct": 4.18},
            "benchmark_comparison": {"vs_10y": {"label": "vs 10Y Treasury", "spread_bps": -7}},
            "time_series": [{"year": 2023, "cap_rate_pct": 4.18}],
        },
        "risk": {
            "composite_score": 28, "risk_tier": "LOW",
            "factors": {"rates": {"label": "Interest Rates", "score": 45, "weight": 0.25, "data_gap": False}},
        },
        "crop_economics": {
            "diversification_hhi": 0.32,
            "crop_stability": {"CORN": {"cv": 0.08}, "COTTON": {"cv": 0.35}},
            "rent_trend": "+2.3% annual growth",
        },
        "exit_optionality": {
            "exit_tier": "STRONG", "composite_score": 78,
            "components": {"solar": {"score": 85, "detail": "TX solar 600%+ growth"}},
        },
    },
    "data_gaps": ["Risk: Farm Debt data gap"],
    "data_completeness": "5/5",
}

def test_report_import():
    from markdown_report import generate_report
    return True

def test_report_generates_markdown():
    from markdown_report import generate_report
    md = generate_report(SAMPLE_UNDERWRITING)
    assert isinstance(md, str)
    assert len(md) > 500, f"Report too short: {len(md)} chars"
    return True

def test_report_has_title():
    from markdown_report import generate_report
    md = generate_report(SAMPLE_UNDERWRITING)
    assert "# Farmland Investment Analysis — TX" in md
    return True

def test_report_has_fact_labels():
    from markdown_report import generate_report
    md = generate_report(SAMPLE_UNDERWRITING)
    fact_count = md.count("`FACT`")
    assert fact_count >= 5, f"Expected >=5 FACT labels, got {fact_count}"
    return True

def test_report_has_inference_labels():
    from markdown_report import generate_report
    md = generate_report(SAMPLE_UNDERWRITING)
    assert "`INFERENCE`" in md
    return True

def test_report_has_confidence_badges():
    from markdown_report import generate_report
    md = generate_report(SAMPLE_UNDERWRITING)
    badge_count = md.count("🟢") + md.count("🟡") + md.count("🔴")
    assert badge_count >= 3, f"Expected >=3 badges, got {badge_count}"
    return True

def test_report_has_source_footnotes():
    from markdown_report import generate_report
    md = generate_report(SAMPLE_UNDERWRITING)
    assert "[^" in md, "Missing source footnotes"
    assert "## Sources" in md, "Missing Sources section"
    return True

def test_report_has_data_gaps():
    from markdown_report import generate_report
    md = generate_report(SAMPLE_UNDERWRITING)
    assert "Data Gaps" in md
    assert "Farm Debt" in md
    return True

def test_report_has_reproducibility():
    from markdown_report import generate_report
    md = generate_report(SAMPLE_UNDERWRITING)
    assert "Reproducibility Footer" in md
    assert "mmv-data → mmv-underwriting → mmv-reporting" in md
    return True

def test_report_all_sections():
    from markdown_report import generate_report
    md = generate_report(SAMPLE_UNDERWRITING)
    for section in ["Land Values", "Cap Rate", "Risk Scoring", "Crop Economics", "Exit Optionality"]:
        assert section in md, f"Missing section: {section}"
    return True

def test_report_empty_input():
    from markdown_report import generate_report
    md = generate_report({"state": "XX", "summary": {}, "sections": {}, "data_gaps": [], "data_completeness": "0/5"})
    assert isinstance(md, str)
    assert "XX" in md
    return True

test("Report module imports", test_report_import)
test("Generates non-trivial markdown", test_report_generates_markdown)
test("Report has correct title", test_report_has_title)
test("Report has FACT labels (>=5)", test_report_has_fact_labels)
test("Report has INFERENCE labels", test_report_has_inference_labels)
test("Report has confidence badges (>=3)", test_report_has_confidence_badges)
test("Report has source footnotes", test_report_has_source_footnotes)
test("Report has data gaps section", test_report_has_data_gaps)
test("Report has reproducibility footer", test_report_has_reproducibility)
test("Report has all 5 sections", test_report_all_sections)
test("Report handles empty input gracefully", test_report_empty_input)


# ════════════════════════════════════════════════════════════════
# TASK 3: GCS Upload
# ════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  TASK 3: GCS Upload")
print("═"*60)

def test_gcs_content_hash():
    from gcs import content_hash
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"test": true}')
        path = f.name
    h = content_hash(path)
    assert len(h) == 64, f"SHA-256 should be 64 hex chars, got {len(h)}"
    h2 = content_hash(path)
    assert h == h2, "Same file should produce same hash"
    os.unlink(path)
    return True

def test_gcs_hash_different_content():
    from gcs import content_hash
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"a": 1}')
        path1 = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"b": 2}')
        path2 = f.name
    h1 = content_hash(path1)
    h2 = content_hash(path2)
    assert h1 != h2, "Different content should produce different hashes"
    os.unlink(path1)
    os.unlink(path2)
    return True

def test_gcs_upload_missing_file():
    from gcs import upload_to_gcs
    result = upload_to_gcs("/nonexistent/file.json", "test-bucket")
    assert result["status"] == "error"
    return True

test("content_hash produces SHA-256", test_gcs_content_hash)
test("Different files produce different hashes", test_gcs_hash_different_content)
test("upload_to_gcs handles missing file", test_gcs_upload_missing_file)


# ════════════════════════════════════════════════════════════════
# TASK 4: Cloud SQL Tables
# ════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  TASK 4: Cloud SQL Tables")
print("═"*60)

def test_ddl_file_exists():
    path = os.path.join(BASE, "mmv-infra", "sql", "create_tables.sql")
    assert os.path.exists(path), f"DDL file not found: {path}"
    with open(path) as f:
        ddl = f.read()
    assert len(ddl) > 2000, f"DDL too short: {len(ddl)} chars"
    return True

def test_ddl_has_all_tables():
    path = os.path.join(BASE, "mmv-infra", "sql", "create_tables.sql")
    with open(path) as f:
        ddl = f.read()
    tables = ["land_values", "cash_rents", "fred_series", "eia_generation",
              "noaa_climate", "drought_monitor", "usda_exports", "crp_enrollment",
              "ssurgo_soils", "census_population", "crop_production"]
    for t in tables:
        assert f"CREATE TABLE IF NOT EXISTS {t}" in ddl, f"Missing table: {t}"
    return True

def test_ddl_has_primary_keys():
    path = os.path.join(BASE, "mmv-infra", "sql", "create_tables.sql")
    with open(path) as f:
        ddl = f.read()
    pk_count = ddl.count("PRIMARY KEY")
    assert pk_count >= 11, f"Expected >=11 primary keys, got {pk_count}"
    return True

def test_loader_import():
    from load_to_postgres import TABLE_MAP, FILE_TO_TABLE
    assert len(TABLE_MAP) >= 11, f"Expected >=11 table mappings, got {len(TABLE_MAP)}"
    assert len(FILE_TO_TABLE) >= 10, f"Expected >=10 file mappings, got {len(FILE_TO_TABLE)}"
    return True

def test_loader_table_map_completeness():
    from load_to_postgres import TABLE_MAP
    for key, config in TABLE_MAP.items():
        assert "table" in config, f"Missing 'table' in {key}"
        assert "columns" in config, f"Missing 'columns' in {key}"
        assert "pk" in config, f"Missing 'pk' in {key}"
        assert len(config["columns"]) > 0, f"Empty columns for {key}"
        for pk_col in config["pk"]:
            assert pk_col in config["columns"], f"PK col '{pk_col}' not in columns for {key}"
    return True

test("DDL file exists and is non-trivial", test_ddl_file_exists)
test("DDL has all 11 tables", test_ddl_has_all_tables)
test("DDL has primary keys for all tables", test_ddl_has_primary_keys)
test("Loader module imports", test_loader_import)
test("TABLE_MAP has valid structure (PK ⊂ columns)", test_loader_table_map_completeness)


# ════════════════════════════════════════════════════════════════
# TASK 5: Crop Production API
# ════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  TASK 5: Crop Production API")
print("═"*60)

def test_crop_api_function_exists():
    import usda
    assert hasattr(usda, "fetch_crop_production_api")
    assert hasattr(usda, "NASS_API_URL")
    assert usda.NASS_API_URL == "https://quickstats.nass.usda.gov/api/api_GET/"
    return True

def test_crop_api_no_key_returns_none():
    old = os.environ.pop("NASS_API_KEY", "")
    try:
        # Reimport to pick up missing key
        import usda
        importlib.reload(usda)
        result = usda.fetch_crop_production_api("TX")
    finally:
        if old:
            os.environ["NASS_API_KEY"] = old
    assert result is None, f"Should return None when no API key, got {type(result)}"
    return True

def test_crop_production_has_fallback():
    import inspect, usda
    source = inspect.getsource(usda.fetch_crop_production)
    assert "fetch_crop_production_api" in source, "Should call API function"
    assert "Falling back" in source or "qs.crops" in source, "Should have bulk TSV fallback"
    return True

test("fetch_crop_production_api() exists", test_crop_api_function_exists)
test("API returns None without key (graceful)", test_crop_api_no_key_returns_none)
test("fetch_crop_production() has API-first + fallback", test_crop_production_has_fallback)


# ════════════════════════════════════════════════════════════════
# TASK 6: LLM Reasoning Layer
# ════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  TASK 6: LLM Reasoning Layer")
print("═"*60)

def test_llm_import():
    from llm_analyst import analyze_section, synthesize_report, SECTION_SCHEMA
    return True

def test_llm_deterministic_land_values():
    from llm_analyst import analyze_section
    result = analyze_section("land_values", {
        "nominal_cagr_pct": 5.2, "real_cagr_pct": 2.1,
        "annual_volatility_pct": 3.8,
        "first_value": 2500, "last_value": 3400,
    }, force_deterministic=True)
    assert result["analysis_method"] == "deterministic"
    assert len(result["findings"]) >= 3, f"Expected >=3 findings, got {len(result['findings'])}"
    types = [f["type"] for f in result["findings"]]
    assert "FACT" in types, "Should have FACT findings"
    assert "INFERENCE" in types, "Should have INFERENCE findings"
    return True

def test_llm_deterministic_cap_rate():
    from llm_analyst import analyze_section
    result = analyze_section("cap_rate", {
        "latest": {"cap_rate_pct": 2.5},
        "benchmark_comparison": {"vs_10y": {"label": "vs 10Y", "spread_bps": -50}},
    }, force_deterministic=True)
    assert len(result["findings"]) >= 2
    return True

def test_llm_deterministic_risk():
    from llm_analyst import analyze_section
    result = analyze_section("risk", {
        "composite_score": 72, "risk_tier": "HIGH",
        "factors": {
            "rates": {"label": "Interest Rates", "score": 80, "weight": 0.25, "data_gap": False},
            "debt": {"label": "Farm Debt", "score": 65, "weight": 0.20, "data_gap": True},
        },
    }, force_deterministic=True)
    assert len(result["data_gaps"]) >= 1, "Should flag data gap for debt"
    assert len(result["risk_flags"]) >= 1, "Should flag elevated rates"
    return True

def test_llm_deterministic_crops():
    from llm_analyst import analyze_section
    result = analyze_section("crop_economics", {
        "diversification_hhi": 0.18,
        "crop_stability": {"CORN": {"cv": 0.08}, "WHEAT": {"cv": 0.12}},
    }, force_deterministic=True)
    assert len(result["findings"]) >= 3
    return True

def test_llm_deterministic_exit():
    from llm_analyst import analyze_section
    result = analyze_section("exit_optionality", {
        "exit_tier": "STRONG", "composite_score": 78,
        "components": {"solar": {"score": 85, "detail": "Growth 600%+"}},
    }, force_deterministic=True)
    assert len(result["findings"]) >= 1
    return True

def test_llm_finding_schema():
    from llm_analyst import analyze_section
    result = analyze_section("land_values", {
        "nominal_cagr_pct": 5.2, "annual_volatility_pct": 3.8,
        "first_value": 2500, "last_value": 3400,
    }, force_deterministic=True)
    required = {"statement", "type", "confidence", "confidence_reason", "source_citation", "data_reference"}
    for finding in result["findings"]:
        missing = required - set(finding.keys())
        assert not missing, f"Finding missing keys: {missing}"
        assert finding["type"] in ("FACT", "INFERENCE"), f"Invalid type: {finding['type']}"
        assert finding["confidence"] in ("HIGH", "MEDIUM", "LOW"), f"Invalid confidence: {finding['confidence']}"
    return True

def test_llm_synthesis():
    from llm_analyst import analyze_section, synthesize_report
    sections = {}
    for name, data in [
        ("land_values", {"nominal_cagr_pct": 5.2, "annual_volatility_pct": 3.8, "first_value": 2500, "last_value": 3400}),
        ("risk", {"composite_score": 28, "risk_tier": "LOW", "factors": {}}),
        ("exit_optionality", {"exit_tier": "STRONG", "composite_score": 78, "components": {}}),
    ]:
        sections[name] = analyze_section(name, data, force_deterministic=True)
    
    synthesis = synthesize_report(sections)
    assert "recommendation" in synthesis
    assert synthesis["recommendation"] in ("FAVORABLE", "MIXED", "UNFAVORABLE")
    assert "key_themes" in synthesis
    assert "synthesis_method" in synthesis
    return True

def test_llm_unknown_section():
    from llm_analyst import analyze_section
    result = analyze_section("unknown_section", {"error": "no data"}, force_deterministic=True)
    assert result["analysis_method"] == "deterministic"
    assert len(result["data_gaps"]) >= 1
    return True

def test_llm_none_values():
    """Regression: land_values with None first_value/last_value should not crash."""
    from llm_analyst import analyze_section
    result = analyze_section("land_values", {
        "nominal_cagr_pct": 3.5,
        "first_value": None,
        "last_value": None,
    }, force_deterministic=True)
    assert result["analysis_method"] == "deterministic"
    assert len(result["findings"]) >= 1
    return True

test("LLM analyst module imports", test_llm_import)
test("Land values: deterministic (>=3 findings, FACT+INFERENCE)", test_llm_deterministic_land_values)
test("Cap rate: deterministic (>=2 findings)", test_llm_deterministic_cap_rate)
test("Risk: flags data gaps and elevated scores", test_llm_deterministic_risk)
test("Crop economics: HHI + crop stability", test_llm_deterministic_crops)
test("Exit optionality: tier + components", test_llm_deterministic_exit)
test("All findings match SECTION_SCHEMA", test_llm_finding_schema)
test("Cross-section synthesis produces recommendation", test_llm_synthesis)
test("Unknown section handled gracefully", test_llm_unknown_section)
test("Regression: None values in land_values", test_llm_none_values)


# ════════════════════════════════════════════════════════════════
# INTEGRATION: FRED live fetch with provenance
# ════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  INTEGRATION: FRED live fetch with provenance")
print("═"*60)

def test_fred_live_fetch():
    from fred import fetch_series
    result = fetch_series("FEDFUNDS", start_date="2024-01-01")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "value" in result, "Missing 'value' key"
    assert "provenance" in result, "Missing 'provenance' key"
    records = result["value"]
    assert len(records) > 0, "No records returned"
    assert records[0].get("series_id") == "FEDFUNDS"
    p = result["provenance"]
    assert p["source"].startswith("FRED")
    assert "fetched_at" in p
    assert p["freshness"] == "current"
    assert p["is_mock"] == False
    return True

test("FRED: live fetch returns provenance-wrapped data", test_fred_live_fetch)


# ════════════════════════════════════════════════════════════════
# INTEGRATION: Report + LLM from real underwriting data
# ════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  INTEGRATION: Report + LLM from real underwriting data")
print("═"*60)

def test_report_from_real_data():
    real_path = "/tmp/mmv_initial_fetch/underwriting_TX.json"
    if not os.path.exists(real_path):
        return "SKIP: no underwriting_TX.json found"
    with open(real_path) as f:
        data = json.load(f)
    from markdown_report import generate_report
    md = generate_report(data)
    assert len(md) > 200
    assert "TX" in md
    with open("/tmp/mmv_report_TX_test.md", "w") as f:
        f.write(md)
    return True

def test_llm_from_real_data():
    real_path = "/tmp/mmv_initial_fetch/underwriting_TX.json"
    if not os.path.exists(real_path):
        return "SKIP: no underwriting_TX.json found"
    with open(real_path) as f:
        data = json.load(f)
    from llm_analyst import analyze_section, synthesize_report
    sections = data.get("sections", {})
    analyzed = {}
    for name, sdata in sections.items():
        analyzed[name] = analyze_section(name, sdata, force_deterministic=True)
    synthesis = synthesize_report(analyzed)
    assert synthesis["recommendation"] in ("FAVORABLE", "MIXED", "UNFAVORABLE")
    total = sum(len(a.get("findings", [])) for a in analyzed.values())
    assert total > 0, "Expected some findings"
    return True

test("Report from real underwriting_TX.json", test_report_from_real_data)
test("LLM analyst from real underwriting_TX.json", test_llm_from_real_data)


# ════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print(f"  RESULTS: {PASS} passed, {FAIL} failed ({PASS+FAIL} total)")
print("═"*60)

if FAIL > 0:
    print("\n  FAILURES:")
    for icon, name, detail in RESULTS:
        if icon == "❌":
            print(f"    {icon} {name}: {detail}")

print()
sys.exit(1 if FAIL > 0 else 0)
