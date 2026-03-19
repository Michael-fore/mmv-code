#!/usr/bin/env python3
"""
MMV System Map — Codebase ontology introspection.

Scans all 5 repos (mmv-agent, mmv-data, mmv-underwriting, mmv-reporting, mmv-infra)
and builds a complete map of:
  - Modules, functions, and classes
  - Cross-repo import dependencies
  - Database tables and which code reads/writes them
  - Data flow: External API → fetcher → cache → DB → analysis → report
  - Potential issues (orphaned modules, unused tables, broken dependencies)

Usage:
    python system_map.py                 # text report to stdout
    python system_map.py --json          # JSON output
    python system_map.py --html          # also generate interactive HTML visual
    python system_map.py --html --open   # generate and open in browser
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path


# ── Config ────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent.parent.parent.parent.parent  # MMV root
REPOS = ["mmv-agent", "mmv-data", "mmv-underwriting", "mmv-reporting", "mmv-infra"]

# Known external API sources mapped to fetcher modules
EXTERNAL_APIS = {
    "usda": "USDA NASS",
    "fred": "FRED API",
    "eia": "EIA API",
    "noaa": "NOAA NCEI",
    "drought": "US Drought Monitor",
    "census": "US Census Bureau",
    "ssurgo": "USDA NRCS SSURGO",
    "usda_fas": "USDA FAS",
    "usda_fsa": "USDA FSA CRP",
}


# ── Data Structures ──────────────────────────────────────────────

@dataclass
class FunctionInfo:
    name: str
    lineno: int
    is_public: bool
    docstring: str = ""
    args: list[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    path: str               # relative to MMV root
    repo: str               # which repo it belongs to
    package: str             # e.g. "tools", "tasks"
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    imports_from: list[str] = field(default_factory=list)  # module names imported
    raw_imports: list[str] = field(default_factory=list)  # raw import strings
    lines: int = 0


@dataclass
class TableInfo:
    name: str
    source: str             # DDL file or ClickHouse schema
    columns: list[str] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    referenced_by: list[str] = field(default_factory=list)  # modules that use this table


@dataclass
class DataFlow:
    source: str             # external API name
    fetcher: str            # module that fetches
    cache: str              # where data is cached
    table: str              # DB table name
    consumers: list[str] = field(default_factory=list)  # modules that consume


@dataclass
class Issue:
    severity: str           # WARNING, INFO
    category: str           # orphan, unused, mismatch
    message: str
    location: str = ""


# ── Scanner ──────────────────────────────────────────────────────

def scan_module(filepath: Path, repo: str) -> ModuleInfo:
    """Parse a Python file using AST to extract functions, classes, imports."""
    rel = str(filepath.relative_to(BASE))
    package = filepath.parent.name

    info = ModuleInfo(path=rel, repo=repo, package=package)

    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        info.lines = source.count("\n") + 1
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return info

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Only top-level and class-level functions
            fn = FunctionInfo(
                name=node.name,
                lineno=node.lineno,
                is_public=not node.name.startswith("_"),
                args=[a.arg for a in node.args.args if a.arg != "self"],
            )
            # Get docstring
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)):
                val = node.body[0].value
                doc = str(val.value) if val.value else ""
                fn.docstring = doc.strip().split("\n")[0][:120]
            info.functions.append(fn)

        elif isinstance(node, ast.ClassDef):
            info.classes.append(node.name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                info.imports_from.append(alias.name)
                info.raw_imports.append(f"import {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                info.imports_from.append(node.module)
                names = [a.name for a in node.names]
                info.raw_imports.append(f"from {node.module} import {', '.join(names)}")

    return info


def scan_all_modules() -> list[ModuleInfo]:
    """Scan all Python modules across all repos."""
    modules = []
    for repo in REPOS:
        repo_path = BASE / repo
        if not repo_path.is_dir():
            continue
        # Scan tools/ and tasks/ packages
        for subdir in ["tools", "tasks"]:
            pkg_path = repo_path / subdir
            if not pkg_path.is_dir():
                continue
            for py_file in sorted(pkg_path.glob("*.py")):
                if py_file.name == "__init__.py":
                    continue
                if py_file.name.startswith("__"):
                    continue
                modules.append(scan_module(py_file, repo))

        # Also scan top-level .py files in repo
        for py_file in sorted(repo_path.glob("*.py")):
            modules.append(scan_module(py_file, repo))

    return modules


def scan_sql_tables() -> list[TableInfo]:
    """Parse SQL DDL files for table definitions."""
    tables = []

    # PostgreSQL DDL
    pg_ddl = BASE / "mmv-infra" / "sql" / "create_tables.sql"
    if pg_ddl.exists():
        ddl = pg_ddl.read_text()
        # Match CREATE TABLE statements
        for match in re.finditer(
            r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\);",
            ddl,
            re.DOTALL,
        ):
            name = match.group(1)
            body = match.group(2)
            # Extract columns
            cols = []
            pks = []
            for line in body.split("\n"):
                line = line.strip().rstrip(",")
                if line.startswith("--") or not line:
                    continue
                if "PRIMARY KEY" in line.upper():
                    pk_match = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", line)
                    if pk_match:
                        pks = [c.strip() for c in pk_match.group(1).split(",")]
                else:
                    col_match = re.match(r"(\w+)\s+", line)
                    if col_match:
                        cols.append(col_match.group(1))
            tables.append(TableInfo(
                name=name,
                source="mmv-infra/sql/create_tables.sql",
                columns=cols,
                primary_key=pks,
            ))

    # ClickHouse schemas from load_to_clickhouse.py
    ch_loader = BASE / "mmv-data" / "tools" / "load_to_clickhouse.py"
    if ch_loader.exists():
        source = ch_loader.read_text()
        for match in re.finditer(r'"(\w+)":\s*\{[^}]*"columns":\s*\[([^\]]+)\]', source):
            name = match.group(1)
            cols_str = match.group(2)
            cols = [c.strip().strip('"').strip("'") for c in cols_str.split(",")]
            # Only add if not already found in PostgreSQL DDL
            existing = [t.name for t in tables]
            if name not in existing:
                tables.append(TableInfo(
                    name=name,
                    source="mmv-data/tools/load_to_clickhouse.py (ClickHouse)",
                    columns=cols,
                ))

    return tables


def find_table_references(modules: list[ModuleInfo], tables: list[TableInfo]):
    """Find which modules reference which tables."""
    table_names = {t.name for t in tables}

    for mod in modules:
        filepath = BASE / mod.path
        if not filepath.exists():
            continue
        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for table in tables:
            # Look for table name as string literal or identifier
            patterns = [
                f'"{table.name}"',
                f"'{table.name}'",
                f"`{table.name}`",
                f".{table.name}",
                f"INTO {table.name}",
                f"FROM {table.name}",
            ]
            for pat in patterns:
                if pat in source:
                    if mod.path not in table.referenced_by:
                        table.referenced_by.append(mod.path)
                    break


def build_data_flows(modules: list[ModuleInfo], tables: list[TableInfo]) -> list[DataFlow]:
    """Reconstruct data flow pipelines from API → fetcher → table → consumer."""
    flows = []
    fetcher_modules = [m for m in modules if m.repo == "mmv-data" and m.package == "tools"]

    for mod in fetcher_modules:
        basename = Path(mod.path).stem
        api_name = EXTERNAL_APIS.get(basename)
        if not api_name:
            continue

        # Find corresponding table(s)
        related_tables = []
        for table in tables:
            if mod.path in table.referenced_by:
                related_tables.append(table.name)

        # Look for JSON cache paths in the module
        cache_path = f"/tmp/mmv_initial_fetch/{basename}.json"

        # Find consumer modules (underwriting, reporting that use this data)
        # Check by: 1) direct import, 2) function name reference, 3) data keyword reference
        consumers = []
        # Get public function names from this fetcher
        fetcher_fn_names = [f.name for f in mod.functions if f.is_public]
        # Keywords that reference this data source in arg names / comments
        DATA_KEYWORDS = {
            "usda": ["usda_land", "usda_cash", "usda_crop", "land_values", "cash_rents"],
            "fred": ["fred_data", "fred", "FEDFUNDS", "CPIAUCSL", "FBDTLA", "DGS10"],
            "eia": ["eia_data", "eia", "solar_generation", "generation_mwh"],
            "noaa": ["noaa", "climate", "tavg_f", "precip_in"],
            "drought": ["drought", "d0_pct", "d1_pct"],
            "census": ["census", "county_population", "pop_2020"],
            "ssurgo": ["ssurgo", "soil", "drainage_class"],
            "usda_fas": ["usda_fas", "export_sales", "fas"],
            "usda_fsa": ["usda_fsa", "crp_enrollment", "fsa"],
        }
        keywords = DATA_KEYWORDS.get(basename, [])

        for other in modules:
            if other.repo in ("mmv-underwriting", "mmv-reporting", "mmv-agent"):
                found = False
                # Check direct imports
                for imp in other.imports_from:
                    if basename in imp:
                        found = True
                        break
                # Check source code for function names / data keywords
                if not found:
                    try:
                        other_source = (BASE / other.path).read_text(encoding="utf-8", errors="replace")
                        for fn_name in fetcher_fn_names:
                            if fn_name in other_source:
                                found = True
                                break
                        if not found:
                            for kw in keywords:
                                if kw in other_source:
                                    found = True
                                    break
                    except Exception:
                        pass
                if found:
                    consumers.append(other.path)

        for tbl in related_tables or [""]:
            flows.append(DataFlow(
                source=api_name,
                fetcher=mod.path,
                cache=cache_path,
                table=tbl,
                consumers=consumers,
            ))

    return flows


def detect_issues(
    modules: list[ModuleInfo],
    tables: list[TableInfo],
    flows: list[DataFlow],
) -> list[Issue]:
    """Detect potential issues in the codebase ontology."""
    issues = []

    # 1. Tables with no code references
    for table in tables:
        if not table.referenced_by:
            issues.append(Issue(
                severity="INFO",
                category="unused_table",
                message=f"Table '{table.name}' has no code references",
                location=table.source,
            ))

    # 2. Modules with no public functions
    for mod in modules:
        public_fns = [f for f in mod.functions if f.is_public]
        if not public_fns and not mod.classes and mod.package == "tools":
            issues.append(Issue(
                severity="INFO",
                category="no_public_api",
                message=f"Module '{mod.path}' has no public functions or classes",
                location=mod.path,
            ))

    # 3. Fetcher modules with no downstream consumer (use flow data)
    fetchers_with_consumers = set()
    for flow in flows:
        if flow.consumers:
            fetchers_with_consumers.add(Path(flow.fetcher).stem)

    for mod in modules:
        if mod.repo == "mmv-data" and mod.package == "tools":
            basename = Path(mod.path).stem
            if basename in EXTERNAL_APIS and basename not in fetchers_with_consumers:
                issues.append(Issue(
                    severity="WARNING",
                    category="no_consumer",
                    message=f"Fetcher '{basename}.py' has no downstream consumer in underwriting/reporting/agent",
                    location=f"mmv-data/tools/{basename}.py",
                ))

    # 4. Cross-repo import anomalies
    for mod in modules:
        for imp in mod.imports_from:
            # Flag if a module imports from a repo it shouldn't
            # (e.g. mmv-reporting importing directly from mmv-data internals)
            pass  # Could expand this with more rules

    # 5. Large modules (potential refactor candidates)
    for mod in modules:
        if mod.lines > 400:
            issues.append(Issue(
                severity="INFO",
                category="large_module",
                message=f"Module '{mod.path}' is {mod.lines} lines — consider refactoring",
                location=mod.path,
            ))

    return issues


# ── Cross-Repo Dependency Graph ──────────────────────────────────

def build_cross_repo_edges(modules: list[ModuleInfo]) -> list[dict]:
    """Build edges for cross-repo import dependencies."""
    # Map module basenames to their repo
    basename_to_repo = {}
    for mod in modules:
        bn = Path(mod.path).stem
        basename_to_repo[bn] = mod.repo

    edges = []
    for mod in modules:
        for imp in mod.imports_from:
            imp_basename = imp.split(".")[-1]
            imp_repo = basename_to_repo.get(imp_basename)
            if imp_repo and imp_repo != mod.repo:
                edges.append({
                    "from_module": mod.path,
                    "from_repo": mod.repo,
                    "to_module": imp_basename,
                    "to_repo": imp_repo,
                    "import_str": imp,
                })

    return edges


# ── Text Report ──────────────────────────────────────────────────

def print_report(
    modules: list[ModuleInfo],
    tables: list[TableInfo],
    flows: list[DataFlow],
    cross_edges: list[dict],
    issues: list[Issue],
):
    """Print a structured text report to stdout."""

    W = 70

    print("═" * W)
    print("  MMV System Ontology Map")
    print("═" * W)
    print()

    # ── Stats ─────────────────────────────────────
    total_fns = sum(len(m.functions) for m in modules)
    total_lines = sum(m.lines for m in modules)
    print(f"  📊 {len(modules)} modules │ {total_fns} functions │ {total_lines:,} lines")
    print(f"  📊 {len(tables)} tables │ {len(flows)} data flows │ {len(issues)} issues")
    print()

    # ── Repo Overview ─────────────────────────────
    print("─" * W)
    print("  📦 Repos")
    print("─" * W)
    for repo in REPOS:
        repo_mods = [m for m in modules if m.repo == repo]
        repo_fns = sum(len(m.functions) for m in repo_mods)
        repo_lines = sum(m.lines for m in repo_mods)
        print(f"\n  {repo}/")
        for mod in repo_mods:
            pub_fns = [f.name for f in mod.functions if f.is_public]
            fn_str = ", ".join(pub_fns[:5])
            if len(pub_fns) > 5:
                fn_str += f" +{len(pub_fns)-5} more"
            pkg = mod.package + "/" if mod.package != Path(mod.path).parent.name == repo else ""
            basename = Path(mod.path).name
            print(f"    ├── {basename:30s} {len(mod.functions):2d} fns │ {mod.lines:4d} lines")
            if pub_fns:
                print(f"    │   └── {fn_str}")
    print()

    # ── Database Tables ───────────────────────────
    print("─" * W)
    print("  🗄️  Database Tables")
    print("─" * W)
    for table in tables:
        refs = table.referenced_by
        ref_str = ", ".join(Path(r).name for r in refs[:4]) if refs else "(no references)"
        pk_str = ", ".join(table.primary_key) if table.primary_key else "—"
        print(f"\n  {table.name}")
        print(f"    PK: ({pk_str})")
        print(f"    Cols: {', '.join(table.columns[:6])}" + (f" +{len(table.columns)-6} more" if len(table.columns) > 6 else ""))
        print(f"    Referenced by: {ref_str}")
    print()

    # ── Data Flows ────────────────────────────────
    print("─" * W)
    print("  🔀 Data Flows")
    print("─" * W)
    for flow in flows:
        fetcher_name = Path(flow.fetcher).name
        consumer_names = [Path(c).name for c in flow.consumers] if flow.consumers else ["(none)"]
        table_str = flow.table if flow.table else "(no table)"
        print(f"\n  {flow.source}")
        print(f"    → {fetcher_name} → {table_str}")
        print(f"    → consumers: {', '.join(consumer_names)}")
    print()

    # ── Cross-Repo Dependencies ───────────────────
    if cross_edges:
        print("─" * W)
        print("  🔗 Cross-Repo Dependencies")
        print("─" * W)
        for edge in cross_edges:
            from_name = Path(edge["from_module"]).name
            print(f"  {from_name} ({edge['from_repo']}) → {edge['to_module']} ({edge['to_repo']})")
        print()

    # ── Issues ────────────────────────────────────
    if issues:
        print("─" * W)
        print("  ⚠️  Issues Detected")
        print("─" * W)
        for issue in sorted(issues, key=lambda i: (i.severity != "WARNING", i.category)):
            icon = "🔴" if issue.severity == "WARNING" else "🟡"
            print(f"  {icon} [{issue.category}] {issue.message}")
        print()

    print("═" * W)


# ── JSON Output ──────────────────────────────────────────────────

def to_json(modules, tables, flows, cross_edges, issues) -> str:
    """Serialize the full ontology to JSON."""
    return json.dumps({
        "modules": [asdict(m) for m in modules],
        "tables": [asdict(t) for t in tables],
        "data_flows": [asdict(f) for f in flows],
        "cross_repo_edges": cross_edges,
        "issues": [asdict(i) for i in issues],
        "stats": {
            "total_modules": len(modules),
            "total_functions": sum(len(m.functions) for m in modules),
            "total_lines": sum(m.lines for m in modules),
            "total_tables": len(tables),
            "total_flows": len(flows),
            "total_issues": len(issues),
        },
    }, indent=2, default=str)


# ── Main ─────────────────────────────────────────────────────────

def run() -> dict:
    """Run the full scan and return structured data."""
    modules = scan_all_modules()
    tables = scan_sql_tables()
    find_table_references(modules, tables)
    flows = build_data_flows(modules, tables)
    cross_edges = build_cross_repo_edges(modules)
    issues = detect_issues(modules, tables, flows)

    return {
        "modules": modules,
        "tables": tables,
        "flows": flows,
        "cross_edges": cross_edges,
        "issues": issues,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MMV System Map — Codebase ontology scanner")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--html", action="store_true", help="Generate interactive HTML visual")
    parser.add_argument("--open", action="store_true", help="Open HTML in browser after generation")
    parser.add_argument("--output", default="/tmp/mmv_system_map.html", help="HTML output path")
    args = parser.parse_args()

    data = run()

    if args.json:
        print(to_json(data["modules"], data["tables"], data["flows"],
                       data["cross_edges"], data["issues"]))
    else:
        print_report(data["modules"], data["tables"], data["flows"],
                     data["cross_edges"], data["issues"])

    if args.html:
        # Import and run visualizer
        vis_path = Path(__file__).parent / "visualize.py"
        if vis_path.exists():
            sys.path.insert(0, str(vis_path.parent))
            from visualize import generate_html
            html = generate_html(data)
            with open(args.output, "w") as f:
                f.write(html)
            print(f"\n✅ HTML visual saved to: {args.output}")

            if args.open:
                import webbrowser
                webbrowser.open(f"file://{args.output}")
        else:
            print(f"\n⚠ Visualizer not found at {vis_path}")
