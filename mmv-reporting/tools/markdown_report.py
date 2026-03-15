"""Trust-aware Markdown report generator for MMV underwriting output.

Accepts the structured dict produced by ``underwrite_deal()`` and renders a
publication-ready Markdown document with:

* Tabular-first layout (readable by real estate professionals)
* Source footnotes per data point (numbered references)
* FACT vs INFERENCE labels on every metric
* Confidence badges (HIGH / MEDIUM / LOW)
* Data-freshness stamps per section
* Data-gaps & caveats summary
* Reproducibility footer (timestamp, sources, tool versions)

Usage
-----
    from mmv_reporting.tools.markdown_report import generate_report

    md_text = generate_report(underwriting_data)
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VERSION = "0.1.0"

CONFIDENCE_BADGE: dict[str, str] = {
    "HIGH": "\U0001f7e2 HIGH",      # 🟢
    "MEDIUM": "\U0001f7e1 MEDIUM",  # 🟡
    "LOW": "\U0001f534 LOW",        # 🔴
}

TRUST_LABEL: dict[str, str] = {
    "FACT": "**FACT**",
    "INFERENCE": "**INFERENCE**",
}

# ---------------------------------------------------------------------------
# Type aliases (lightweight — no runtime dependency on TypedDict)
# ---------------------------------------------------------------------------

DataPoint = dict[str, Any]
"""
Expected shape of a single data point:

    {
        "label": str,
        "value": Any,
        "unit": str | None,
        "trust": "FACT" | "INFERENCE",
        "confidence": "HIGH" | "MEDIUM" | "LOW",
        "source": str,          # human-readable source description
        "source_url": str | None,
        "as_of": str | None,    # e.g. "2024-Q3"
    }
"""

Section = dict[str, Any]
"""
Expected shape of a report section:

    {
        "title": str,
        "data_freshness": str,          # e.g. "2024 Q3"
        "data_points": list[DataPoint],
        "narrative": str | None,        # optional prose summary
    }
"""

UnderwritingData = dict[str, Any]
"""
Top-level dict returned by ``underwrite_deal()``.  Required keys:

    - state: str
    - region: str | None
    - analysis_timestamp: str  (ISO-8601)
    - sections: dict mapping section_key -> Section
        section keys: land_values, cap_rate, risk_assessment,
                      crop_production, exit_analysis, executive_summary
    - data_gaps: list[str]
    - caveats: list[str]
    - sources_used: list[str]
    - tool_versions: dict[str, str]
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _FootnoteCollector:
    """Accumulates unique source references and returns footnote indices."""

    def __init__(self) -> None:
        self._sources: list[tuple[str, str | None]] = []  # (desc, url)
        self._index: dict[str, int] = {}  # source_desc -> 1-based index

    def add(self, source: str, url: str | None = None) -> int:
        """Register a source and return its footnote number (1-based)."""
        if source in self._index:
            return self._index[source]
        idx = len(self._sources) + 1
        self._sources.append((source, url))
        self._index[source] = idx
        return idx

    def render(self) -> str:
        """Render the full footnotes block."""
        if not self._sources:
            return ""
        lines = ["## References", ""]
        for i, (desc, url) in enumerate(self._sources, start=1):
            if url:
                lines.append(f"[^{i}]: [{desc}]({url})")
            else:
                lines.append(f"[^{i}]: {desc}")
        return "\n".join(lines)


def _fmt_value(value: Any, unit: str | None) -> str:
    """Format a numeric or string value with its optional unit."""
    if isinstance(value, float):
        # Currency-like large numbers
        if unit and unit.startswith("$"):
            if abs(value) >= 1_000_000:
                formatted = f"${value / 1_000_000:,.1f}M"
            elif abs(value) >= 1_000:
                formatted = f"${value:,.0f}"
            else:
                formatted = f"${value:,.2f}"
            # Append per-unit suffix if present (e.g. "$/acre")
            suffix = unit.replace("$", "", 1).strip()
            return f"{formatted}{suffix}" if suffix else formatted
        if unit == "%":
            return f"{value:.2f}%"
        return f"{value:,.2f} {unit}" if unit else f"{value:,.2f}"
    if isinstance(value, int):
        if unit and unit.startswith("$"):
            suffix = unit.replace("$", "", 1).strip()
            formatted = f"${value:,}"
            return f"{formatted}{suffix}" if suffix else formatted
        return f"{value:,} {unit}" if unit else f"{value:,}"
    return f"{value} {unit}" if unit else str(value)


def _render_section_table(
    section: Section,
    footnotes: _FootnoteCollector,
) -> str:
    """Render one section as a Markdown table with trust metadata."""
    rows: list[str] = []
    title: str = section.get("title", "Untitled")
    freshness: str = section.get("data_freshness", "N/A")
    narrative: str | None = section.get("narrative")

    rows.append(f"### {title}")
    rows.append(f"*Data as of: {freshness}*")
    rows.append("")

    if narrative:
        rows.append(f"> {narrative}")
        rows.append("")

    data_points: list[DataPoint] = section.get("data_points", [])
    if not data_points:
        rows.append("*No data points available for this section.*")
        rows.append("")
        return "\n".join(rows)

    # Table header
    rows.append("| Metric | Value | Trust | Confidence | Source |")
    rows.append("|--------|-------|-------|------------|--------|")

    for dp in data_points:
        label = dp.get("label", "—")
        value_str = _fmt_value(dp.get("value"), dp.get("unit"))
        trust = TRUST_LABEL.get(dp.get("trust", "INFERENCE"), "**INFERENCE**")
        confidence = CONFIDENCE_BADGE.get(
            dp.get("confidence", "LOW"), CONFIDENCE_BADGE["LOW"]
        )
        source_desc = dp.get("source", "Unknown")
        source_url = dp.get("source_url")
        fn_idx = footnotes.add(source_desc, source_url)
        source_ref = f"[^{fn_idx}]"
        rows.append(
            f"| {label} | {value_str} | {trust} | {confidence} | {source_ref} |"
        )

    rows.append("")
    return "\n".join(rows)


def _render_data_gaps(gaps: list[str], caveats: list[str]) -> str:
    """Render the Data Gaps & Caveats section."""
    lines: list[str] = ["## Data Gaps & Caveats", ""]
    if not gaps and not caveats:
        lines.append("*No significant data gaps or caveats identified.*")
        lines.append("")
        return "\n".join(lines)

    if gaps:
        lines.append("### Data Gaps")
        lines.append("")
        for gap in gaps:
            lines.append(f"- {gap}")
        lines.append("")

    if caveats:
        lines.append("### Caveats")
        lines.append("")
        for caveat in caveats:
            lines.append(f"- {caveat}")
        lines.append("")

    return "\n".join(lines)


def _render_reproducibility_footer(data: UnderwritingData) -> str:
    """Render the reproducibility footer block."""
    ts = data.get("analysis_timestamp", datetime.now(timezone.utc).isoformat())
    sources = data.get("sources_used", [])
    tool_versions = data.get("tool_versions", {})

    lines = [
        "---",
        "## Reproducibility",
        "",
        f"| Item | Detail |",
        f"|------|--------|",
        f"| Analysis timestamp | `{ts}` |",
        f"| Report generator | `markdown_report v{_VERSION}` |",
    ]

    for tool_name, version in tool_versions.items():
        lines.append(f"| {tool_name} | `{version}` |")

    lines.append("")

    if sources:
        lines.append("**Data sources used:**")
        lines.append("")
        for src in sources:
            lines.append(f"1. {src}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Canonical ordering of sections in the rendered report.
_SECTION_ORDER: list[str] = [
    "executive_summary",
    "land_values",
    "cap_rate",
    "crop_production",
    "risk_assessment",
    "exit_analysis",
]


def generate_report(underwriting_data: dict[str, Any]) -> str:
    """Generate a trust-aware Markdown report from underwriting output.

    Parameters
    ----------
    underwriting_data:
        The dict produced by ``underwrite_deal()`` — see module-level
        ``UnderwritingData`` docstring for the expected schema.

    Returns
    -------
    str
        A complete Markdown document ready for rendering or file export.
    """
    footnotes = _FootnoteCollector()
    parts: list[str] = []

    state = underwriting_data.get("state", "Unknown")
    region = underwriting_data.get("region")
    location = f"{region}, {state}" if region else state

    # Title block
    parts.append(f"# MMV Underwriting Report — {location}")
    parts.append("")
    parts.append(
        f"*Generated: "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*"
    )
    parts.append("")
    parts.append("---")
    parts.append("")

    # Sections — honour canonical order, then append any extras.
    sections: dict[str, Section] = underwriting_data.get("sections", {})
    rendered_keys: set[str] = set()

    for key in _SECTION_ORDER:
        if key in sections:
            parts.append(_render_section_table(sections[key], footnotes))
            rendered_keys.add(key)

    for key, section in sections.items():
        if key not in rendered_keys:
            parts.append(_render_section_table(section, footnotes))

    # Data gaps & caveats
    parts.append(
        _render_data_gaps(
            underwriting_data.get("data_gaps", []),
            underwriting_data.get("caveats", []),
        )
    )

    # Footnotes
    fn_block = footnotes.render()
    if fn_block:
        parts.append(fn_block)
        parts.append("")

    # Reproducibility footer
    parts.append(_render_reproducibility_footer(underwriting_data))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Sample data & CLI entry point
# ---------------------------------------------------------------------------

def _build_sample_tx_data() -> dict[str, Any]:
    """Return a realistic sample underwriting dict for Texas farmland."""
    return {
        "state": "TX",
        "region": "Texas Blackland Prairie",
        "analysis_timestamp": "2026-03-15T14:30:00Z",
        "sections": {
            "executive_summary": {
                "title": "Executive Summary",
                "data_freshness": "2025 Q4",
                "narrative": (
                    "The subject property is a 640-acre dryland and irrigated "
                    "farm in the Texas Blackland Prairie, one of the state's "
                    "most productive agricultural regions. Current market "
                    "conditions support a purchase price of $5,800/acre with "
                    "a projected hold-period IRR of 7.2%. Key risks include "
                    "water-rights uncertainty and rising input costs."
                ),
                "data_points": [
                    {
                        "label": "Recommended Purchase Price",
                        "value": 5800,
                        "unit": "$/acre",
                        "trust": "INFERENCE",
                        "confidence": "HIGH",
                        "source": "MMV Valuation Engine v2.1",
                        "source_url": None,
                        "as_of": "2025-Q4",
                    },
                    {
                        "label": "Projected Hold-Period IRR",
                        "value": 7.2,
                        "unit": "%",
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "MMV DCF Model — 10yr horizon",
                        "source_url": None,
                        "as_of": "2025-Q4",
                    },
                    {
                        "label": "Total Acreage",
                        "value": 640,
                        "unit": "acres",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "Williamson County Appraisal District",
                        "source_url": "https://www.wcad.org",
                        "as_of": "2025-Q4",
                    },
                    {
                        "label": "Overall Risk Rating",
                        "value": "Moderate",
                        "unit": None,
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "MMV Risk Scoring Engine v1.4",
                        "source_url": None,
                        "as_of": "2025-Q4",
                    },
                ],
            },
            "land_values": {
                "title": "Land Values & Comparable Sales",
                "data_freshness": "2025 Q4",
                "narrative": None,
                "data_points": [
                    {
                        "label": "Median Sale Price (Blackland Prairie)",
                        "value": 6200.0,
                        "unit": "$/acre",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "Texas Real Estate Research Center — Rural Land Values",
                        "source_url": "https://www.recenter.tamu.edu/data/rural-land",
                        "as_of": "2025-Q3",
                    },
                    {
                        "label": "5-Year CAGR (Cropland)",
                        "value": 8.4,
                        "unit": "%",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "Texas Real Estate Research Center — Rural Land Values",
                        "source_url": "https://www.recenter.tamu.edu/data/rural-land",
                        "as_of": "2025-Q3",
                    },
                    {
                        "label": "Assessed Value (Tax Roll)",
                        "value": 4350.0,
                        "unit": "$/acre",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "Williamson County Appraisal District",
                        "source_url": "https://www.wcad.org",
                        "as_of": "2025",
                    },
                    {
                        "label": "Implied Discount to Market",
                        "value": -6.45,
                        "unit": "%",
                        "trust": "INFERENCE",
                        "confidence": "HIGH",
                        "source": "MMV Valuation Engine v2.1",
                        "source_url": None,
                        "as_of": "2025-Q4",
                    },
                    {
                        "label": "Comparable Sale #1 — 520 ac, Bell County",
                        "value": 6050.0,
                        "unit": "$/acre",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "CoStar Land Comps",
                        "source_url": "https://www.costar.com",
                        "as_of": "2025-06",
                    },
                    {
                        "label": "Comparable Sale #2 — 480 ac, Milam County",
                        "value": 5725.0,
                        "unit": "$/acre",
                        "trust": "FACT",
                        "confidence": "MEDIUM",
                        "source": "Lands of Texas MLS",
                        "source_url": "https://www.landsoftexas.com",
                        "as_of": "2025-08",
                    },
                ],
            },
            "cap_rate": {
                "title": "Capitalization Rate Analysis",
                "data_freshness": "2025 Q3",
                "narrative": None,
                "data_points": [
                    {
                        "label": "Net Operating Income (NOI)",
                        "value": 185.0,
                        "unit": "$/acre",
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "MMV Cash-Flow Model (3-yr avg)",
                        "source_url": None,
                        "as_of": "2025-Q3",
                    },
                    {
                        "label": "Implied Cap Rate",
                        "value": 3.19,
                        "unit": "%",
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "MMV Valuation Engine v2.1",
                        "source_url": None,
                        "as_of": "2025-Q3",
                    },
                    {
                        "label": "Regional Benchmark Cap Rate",
                        "value": 3.0,
                        "unit": "%",
                        "trust": "FACT",
                        "confidence": "MEDIUM",
                        "source": "USDA ERS — Farm Real Estate Value Survey",
                        "source_url": "https://www.ers.usda.gov/data-products/farm-real-estate",
                        "as_of": "2024",
                    },
                    {
                        "label": "Cash Rent (Dryland)",
                        "value": 55.0,
                        "unit": "$/acre",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "USDA NASS — Cash Rents Survey",
                        "source_url": "https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Cash_Rents",
                        "as_of": "2025",
                    },
                    {
                        "label": "Cash Rent (Irrigated)",
                        "value": 130.0,
                        "unit": "$/acre",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "USDA NASS — Cash Rents Survey",
                        "source_url": "https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Cash_Rents",
                        "as_of": "2025",
                    },
                ],
            },
            "crop_production": {
                "title": "Crop Production & Revenue",
                "data_freshness": "2025 Q3",
                "narrative": None,
                "data_points": [
                    {
                        "label": "Primary Crop",
                        "value": "Corn (grain)",
                        "unit": None,
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "USDA NASS — Crop Production Annual Summary",
                        "source_url": "https://usda.library.cornell.edu/concern/publications/k3569432s",
                        "as_of": "2025",
                    },
                    {
                        "label": "County Average Yield (Corn)",
                        "value": 155.0,
                        "unit": "bu/acre",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "USDA NASS — County Estimates",
                        "source_url": "https://www.nass.usda.gov/Statistics_by_State/Texas",
                        "as_of": "2025",
                    },
                    {
                        "label": "Corn Futures Price (Dec-26)",
                        "value": 4.85,
                        "unit": "$/bu",
                        "trust": "FACT",
                        "confidence": "MEDIUM",
                        "source": "CME Group — CBOT Corn Futures",
                        "source_url": "https://www.cmegroup.com/markets/agriculture/grains/corn.html",
                        "as_of": "2026-03-14",
                    },
                    {
                        "label": "Estimated Gross Revenue (Corn)",
                        "value": 751.75,
                        "unit": "$/acre",
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "MMV Revenue Model (yield x price)",
                        "source_url": None,
                        "as_of": "2025-Q3",
                    },
                    {
                        "label": "Estimated Total Production Cost",
                        "value": 580.0,
                        "unit": "$/acre",
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "Texas A&M AgriLife Extension — Crop Budgets",
                        "source_url": "https://agecoext.tamu.edu/resources/crop-livestock-budgets",
                        "as_of": "2025",
                    },
                    {
                        "label": "Crop Insurance Coverage (APH)",
                        "value": 75,
                        "unit": "%",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "USDA RMA — Actuarial Information Browser",
                        "source_url": "https://webapp.rma.usda.gov/apps/actuarialinformationbrowser",
                        "as_of": "2025",
                    },
                ],
            },
            "risk_assessment": {
                "title": "Risk Assessment",
                "data_freshness": "2025 Q4",
                "narrative": (
                    "Primary risk drivers are water-rights regulatory changes "
                    "under the Texas Water Development Board and above-average "
                    "drought probability in the 2026-2028 forecast window."
                ),
                "data_points": [
                    {
                        "label": "Drought Risk (next 3 yr)",
                        "value": "Elevated",
                        "unit": None,
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "NOAA CPC — Seasonal Drought Outlook",
                        "source_url": "https://www.cpc.ncep.noaa.gov/products/expert_assessment/sdo_summary.php",
                        "as_of": "2026-03",
                    },
                    {
                        "label": "Groundwater Availability",
                        "value": "Adequate (Carrizo-Wilcox Aquifer)",
                        "unit": None,
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "Texas Water Development Board — GAM Run 10-077",
                        "source_url": "https://www.twdb.texas.gov/groundwater/models",
                        "as_of": "2024",
                    },
                    {
                        "label": "Water-Rights Regulatory Risk",
                        "value": "Moderate",
                        "unit": None,
                        "trust": "INFERENCE",
                        "confidence": "LOW",
                        "source": "MMV Regulatory Risk Model v0.9 (experimental)",
                        "source_url": None,
                        "as_of": "2025-Q4",
                    },
                    {
                        "label": "Soil Productivity Index (SPI)",
                        "value": 82,
                        "unit": "/ 100",
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "USDA NRCS — Web Soil Survey",
                        "source_url": "https://websoilsurvey.nrcs.usda.gov",
                        "as_of": "2023",
                    },
                    {
                        "label": "Flood Zone Designation",
                        "value": "Zone X (minimal risk)",
                        "unit": None,
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "FEMA NFIP — Flood Map Service Center",
                        "source_url": "https://msc.fema.gov",
                        "as_of": "2022",
                    },
                ],
            },
            "exit_analysis": {
                "title": "Exit Analysis",
                "data_freshness": "2025 Q4",
                "narrative": None,
                "data_points": [
                    {
                        "label": "Projected Exit Price (Yr 10)",
                        "value": 9450.0,
                        "unit": "$/acre",
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "MMV DCF Model — 10yr horizon",
                        "source_url": None,
                        "as_of": "2025-Q4",
                    },
                    {
                        "label": "Assumed Annual Appreciation",
                        "value": 5.0,
                        "unit": "%",
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "MMV DCF Model — 10yr horizon",
                        "source_url": None,
                        "as_of": "2025-Q4",
                    },
                    {
                        "label": "Estimated Disposition Costs",
                        "value": 5.0,
                        "unit": "%",
                        "trust": "INFERENCE",
                        "confidence": "HIGH",
                        "source": "Industry standard (broker commission + closing)",
                        "source_url": None,
                        "as_of": "2025-Q4",
                    },
                    {
                        "label": "Net Exit Proceeds (total)",
                        "value": 5747200.0,
                        "unit": "$",
                        "trust": "INFERENCE",
                        "confidence": "MEDIUM",
                        "source": "MMV DCF Model — 10yr horizon",
                        "source_url": None,
                        "as_of": "2025-Q4",
                    },
                    {
                        "label": "1031 Exchange Eligible",
                        "value": "Yes",
                        "unit": None,
                        "trust": "FACT",
                        "confidence": "HIGH",
                        "source": "IRS Publication 544 — Sales and Other Dispositions of Assets",
                        "source_url": "https://www.irs.gov/pub/irs-pdf/p544.pdf",
                        "as_of": "2025",
                    },
                ],
            },
        },
        "data_gaps": [
            "No recent (< 6 mo) soil-test lab results available for the subject parcel.",
            "Irrigation infrastructure condition report not obtained — assumed functional.",
            "USDA NRCS Soil Productivity Index data last updated in 2023; newer survey pending.",
            "FEMA flood-map panel dates from 2022; Williamson County remap expected 2026.",
        ],
        "caveats": [
            "Projected IRR and exit values assume stable macroeconomic conditions and no major policy changes.",
            "Water-rights regulatory risk model (v0.9) is experimental — treat LOW-confidence outputs with caution.",
            "Crop insurance availability and premium rates may change with the next Farm Bill reauthorisation.",
            "Comparable sales data for parcels > 500 acres is thin in this micro-market; sample size = 2.",
        ],
        "sources_used": [
            "Texas Real Estate Research Center — Rural Land Values",
            "Williamson County Appraisal District",
            "CoStar Land Comps",
            "Lands of Texas MLS",
            "USDA NASS — Cash Rents Survey",
            "USDA NASS — Crop Production Annual Summary",
            "USDA NASS — County Estimates",
            "CME Group — CBOT Corn Futures",
            "Texas A&M AgriLife Extension — Crop Budgets",
            "USDA RMA — Actuarial Information Browser",
            "USDA ERS — Farm Real Estate Value Survey",
            "NOAA CPC — Seasonal Drought Outlook",
            "Texas Water Development Board — GAM Run 10-077",
            "USDA NRCS — Web Soil Survey",
            "FEMA NFIP — Flood Map Service Center",
            "IRS Publication 544",
        ],
        "tool_versions": {
            "mmv-underwriting": "0.4.0",
            "mmv-data": "0.3.2",
            "mmv-valuation-engine": "2.1.0",
            "mmv-risk-scoring": "1.4.0",
            "mmv-dcf-model": "1.0.0",
        },
    }


def main() -> None:
    """Generate sample report, save to disk, and print a preview."""
    sample_data = _build_sample_tx_data()

    # Write sample JSON
    json_path = Path("/tmp/mmv_initial_fetch/underwriting_TX.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(sample_data, indent=2), encoding="utf-8")
    print(f"[INFO] Wrote sample underwriting JSON → {json_path}")

    # Generate report
    report = generate_report(sample_data)

    # Save markdown
    md_path = Path("/tmp/mmv_report_TX.md")
    md_path.write_text(report, encoding="utf-8")
    print(f"[INFO] Wrote Markdown report → {md_path}")

    # Preview (first 80 lines)
    print()
    print("=" * 72)
    print("  REPORT PREVIEW (first 80 lines)")
    print("=" * 72)
    preview_lines = report.splitlines()[:80]
    for line in preview_lines:
        print(line)
    if len(report.splitlines()) > 80:
        print(f"\n  ... ({len(report.splitlines()) - 80} more lines)")
    print("=" * 72)


if __name__ == "__main__":
    main()
