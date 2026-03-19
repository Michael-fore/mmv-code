#!/usr/bin/env python3
"""
MMV System Map — Interactive HTML Visualizer.

Generates a self-contained HTML file with a D3.js force-directed graph
showing the full MMV system ontology.

Not meant to be called directly — use system_map.py --html instead.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path


def generate_html(data: dict) -> str:
    """Generate a standalone HTML file with D3 force-directed graph."""

    # Build graph data
    nodes = []
    links = []
    node_ids = set()

    # Color palette
    REPO_COLORS = {
        "mmv-agent": "#a78bfa",       # purple
        "mmv-data": "#60a5fa",        # blue
        "mmv-underwriting": "#34d399", # green
        "mmv-reporting": "#fbbf24",    # amber
        "mmv-infra": "#f87171",        # red
    }

    # 1. Add repo nodes
    for repo in ["mmv-agent", "mmv-data", "mmv-underwriting", "mmv-reporting", "mmv-infra"]:
        nid = f"repo:{repo}"
        if nid not in node_ids:
            nodes.append({
                "id": nid,
                "label": repo,
                "type": "repo",
                "color": REPO_COLORS.get(repo, "#6b7280"),
                "radius": 28,
                "group": repo,
            })
            node_ids.add(nid)

    # 2. Add module nodes
    for mod in data["modules"]:
        path = mod.path if hasattr(mod, 'path') else mod['path']
        repo = mod.repo if hasattr(mod, 'repo') else mod['repo']
        lines = mod.lines if hasattr(mod, 'lines') else mod.get('lines', 0)
        fns = mod.functions if hasattr(mod, 'functions') else mod.get('functions', [])
        basename = Path(path).stem
        nid = f"mod:{basename}"
        if nid in node_ids:
            nid = f"mod:{path}"
        pub_fns = []
        for f in fns:
            fname = f.name if hasattr(f, 'name') else f.get('name', '')
            fpub = f.is_public if hasattr(f, 'is_public') else f.get('is_public', True)
            if fpub:
                pub_fns.append(fname)
        tooltip_lines = [f"📄 {path}", f"📦 {repo}", f"📏 {lines} lines"]
        if pub_fns:
            tooltip_lines.append(f"⚡ {', '.join(pub_fns[:6])}")

        nodes.append({
            "id": nid,
            "label": basename,
            "type": "module",
            "color": REPO_COLORS.get(repo, "#6b7280"),
            "radius": max(10, min(22, lines // 30)),
            "group": repo,
            "tooltip": "\n".join(tooltip_lines),
            "functions": len(fns),
            "lines": lines,
        })
        node_ids.add(nid)

        # Link module to repo
        links.append({
            "source": f"repo:{repo}",
            "target": nid,
            "type": "belongs_to",
            "color": REPO_COLORS.get(repo, "#6b7280") + "40",
        })

    # 3. Add external API nodes
    from system_map import EXTERNAL_APIS
    for key, name in EXTERNAL_APIS.items():
        nid = f"api:{key}"
        nodes.append({
            "id": nid,
            "label": name,
            "type": "api",
            "color": "#fb923c",
            "radius": 16,
            "group": "external",
            "tooltip": f"🌐 {name}\nExternal data source",
        })
        node_ids.add(nid)

    # 4. Add table nodes
    for table in data["tables"]:
        tname = table.name if hasattr(table, 'name') else table['name']
        tpk = table.primary_key if hasattr(table, 'primary_key') else table.get('primary_key', [])
        tcols = table.columns if hasattr(table, 'columns') else table.get('columns', [])
        trefs = table.referenced_by if hasattr(table, 'referenced_by') else table.get('referenced_by', [])
        nid = f"table:{tname}"
        pk_str = ", ".join(tpk) if tpk else "—"
        nodes.append({
            "id": nid,
            "label": tname,
            "type": "table",
            "color": "#2dd4bf",
            "radius": 14,
            "group": "database",
            "tooltip": f"🗄️ {tname}\nPK: ({pk_str})\nCols: {len(tcols)}",
        })
        node_ids.add(nid)

        # Link referenced modules to table
        for ref in trefs:
            ref_basename = Path(ref).stem
            ref_nid = f"mod:{ref_basename}"
            if ref_nid not in node_ids:
                ref_nid = f"mod:{ref}"
            if ref_nid in node_ids:
                links.append({
                    "source": ref_nid,
                    "target": nid,
                    "type": "table_access",
                    "color": "#2dd4bf80",
                })

    # 5. Add data flow edges
    for flow in data["flows"]:
        ffetcher = flow.fetcher if hasattr(flow, 'fetcher') else flow['fetcher']
        ftable = flow.table if hasattr(flow, 'table') else flow.get('table', '')
        fconsumers = flow.consumers if hasattr(flow, 'consumers') else flow.get('consumers', [])
        fetcher_basename = Path(ffetcher).stem
        api_key = fetcher_basename
        # Match API → fetcher
        if f"api:{api_key}" in node_ids and f"mod:{fetcher_basename}" in node_ids:
            links.append({
                "source": f"api:{api_key}",
                "target": f"mod:{fetcher_basename}",
                "type": "data_flow",
                "color": "#fb923c80",
            })

        # Fetcher → table
        if ftable and f"table:{ftable}" in node_ids:
            links.append({
                "source": f"mod:{fetcher_basename}",
                "target": f"table:{ftable}",
                "type": "data_flow",
                "color": "#2dd4bf60",
            })

        # Fetcher → consumers
        for consumer in fconsumers:
            consumer_basename = Path(consumer).stem
            consumer_nid = f"mod:{consumer_basename}"
            if consumer_nid in node_ids:
                links.append({
                    "source": f"mod:{fetcher_basename}",
                    "target": consumer_nid,
                    "type": "data_flow",
                    "color": "#60a5fa60",
                })

    # 6. Cross-repo import edges
    for edge in data["cross_edges"]:
        from_basename = Path(edge["from_module"]).stem
        from_nid = f"mod:{from_basename}"
        to_nid = f"mod:{edge['to_module']}"
        if from_nid in node_ids and to_nid in node_ids:
            links.append({
                "source": from_nid,
                "target": to_nid,
                "type": "import",
                "color": "#e879f980",
            })

    # Serialize for embedding
    graph_json = json.dumps({"nodes": nodes, "links": links}, default=str)

    # Stats for the panel
    def _get(obj, attr, default=0):
        return getattr(obj, attr, default) if hasattr(obj, attr) else obj.get(attr, default)

    stats = {
        "modules": len(data["modules"]),
        "functions": sum(len(_get(m, 'functions', [])) for m in data["modules"]),
        "lines": sum(_get(m, 'lines', 0) for m in data["modules"]),
        "tables": len(data["tables"]),
        "flows": len(data["flows"]),
        "issues": len(data["issues"]),
    }

    issues_json = json.dumps(
        [asdict(i) if hasattr(i, '__dataclass_fields__') else i for i in data["issues"]],
        default=str
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MMV System Ontology Map</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: #0f0f1a;
    color: #e2e8f0;
    overflow: hidden;
    height: 100vh;
    width: 100vw;
  }}

  /* Canvas background */
  svg {{
    width: 100vw;
    height: 100vh;
    display: block;
  }}

  /* Glassmorphism panels */
  .panel {{
    position: fixed;
    background: rgba(15, 15, 30, 0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    z-index: 10;
  }}

  /* Title panel */
  .title-panel {{
    top: 20px;
    left: 20px;
    max-width: 320px;
  }}

  .title-panel h1 {{
    font-size: 1.3rem;
    font-weight: 700;
    background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }}

  .title-panel .subtitle {{
    font-size: 0.75rem;
    color: #94a3b8;
    margin-bottom: 12px;
  }}

  /* Stats grid */
  .stats {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
  }}

  .stat {{
    background: rgba(255, 255, 255, 0.04);
    border-radius: 8px;
    padding: 8px;
    text-align: center;
  }}

  .stat-value {{
    font-size: 1.2rem;
    font-weight: 700;
    color: #f8fafc;
  }}

  .stat-label {{
    font-size: 0.6rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  /* Legend panel */
  .legend-panel {{
    bottom: 20px;
    left: 20px;
    max-width: 280px;
  }}

  .legend-panel h3 {{
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 10px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  .legend-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 0.75rem;
  }}

  .legend-dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
  }}

  .legend-line {{
    width: 20px;
    height: 2px;
    flex-shrink: 0;
  }}

  /* Search panel */
  .search-panel {{
    top: 20px;
    right: 20px;
    min-width: 250px;
  }}

  .search-input {{
    width: 100%;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.8rem;
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
    outline: none;
    transition: border-color 0.2s;
  }}

  .search-input:focus {{
    border-color: rgba(167, 139, 250, 0.5);
  }}

  .search-input::placeholder {{
    color: #475569;
  }}

  /* Issues panel */
  .issues-panel {{
    bottom: 20px;
    right: 20px;
    max-width: 360px;
    max-height: 280px;
    overflow-y: auto;
  }}

  .issues-panel h3 {{
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 10px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  .issue {{
    font-size: 0.7rem;
    padding: 6px 8px;
    margin-bottom: 4px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.03);
    border-left: 3px solid;
  }}

  .issue-warning {{ border-color: #f87171; }}
  .issue-info {{ border-color: #fbbf24; }}

  /* Tooltip */
  .tooltip {{
    position: fixed;
    background: rgba(15, 15, 30, 0.95);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 0.75rem;
    line-height: 1.5;
    pointer-events: none;
    z-index: 100;
    max-width: 320px;
    white-space: pre-line;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    opacity: 0;
    transition: opacity 0.15s;
  }}

  /* Scrollbar */
  ::-webkit-scrollbar {{ width: 4px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 2px; }}

  /* Node labels */
  .node-label {{
    font-family: 'Inter', sans-serif;
    font-size: 9px;
    fill: #e2e8f0;
    text-anchor: middle;
    pointer-events: none;
    user-select: none;
    text-shadow: 0 1px 4px rgba(0,0,0,0.8);
  }}
</style>
</head>
<body>

<!-- Title Panel -->
<div class="panel title-panel">
  <h1>MMV System Ontology</h1>
  <div class="subtitle">Interactive map of modules, data flows, and dependencies</div>
  <div class="stats">
    <div class="stat">
      <div class="stat-value">{stats['modules']}</div>
      <div class="stat-label">Modules</div>
    </div>
    <div class="stat">
      <div class="stat-value">{stats['functions']}</div>
      <div class="stat-label">Functions</div>
    </div>
    <div class="stat">
      <div class="stat-value">{stats['lines']:,}</div>
      <div class="stat-label">Lines</div>
    </div>
    <div class="stat">
      <div class="stat-value">{stats['tables']}</div>
      <div class="stat-label">Tables</div>
    </div>
    <div class="stat">
      <div class="stat-value">{stats['flows']}</div>
      <div class="stat-label">Data Flows</div>
    </div>
    <div class="stat">
      <div class="stat-value">{stats['issues']}</div>
      <div class="stat-label">Issues</div>
    </div>
  </div>
</div>

<!-- Search Panel -->
<div class="panel search-panel">
  <input type="text" class="search-input" id="search" placeholder="🔍 Search modules, tables..." autocomplete="off">
</div>

<!-- Legend Panel -->
<div class="panel legend-panel">
  <h3>Legend</h3>
  <div class="legend-item"><div class="legend-dot" style="background:#a78bfa"></div> mmv-agent</div>
  <div class="legend-item"><div class="legend-dot" style="background:#60a5fa"></div> mmv-data</div>
  <div class="legend-item"><div class="legend-dot" style="background:#34d399"></div> mmv-underwriting</div>
  <div class="legend-item"><div class="legend-dot" style="background:#fbbf24"></div> mmv-reporting</div>
  <div class="legend-item"><div class="legend-dot" style="background:#f87171"></div> mmv-infra</div>
  <div class="legend-item"><div class="legend-dot" style="background:#fb923c"></div> External API</div>
  <div class="legend-item"><div class="legend-dot" style="background:#2dd4bf"></div> Database Table</div>
  <div style="margin-top: 10px">
    <div class="legend-item"><div class="legend-line" style="background:#e879f9"></div> Cross-repo import</div>
    <div class="legend-item"><div class="legend-line" style="background:#fb923c"></div> Data flow</div>
    <div class="legend-item"><div class="legend-line" style="background:#2dd4bf; border-top: 2px dotted #2dd4bf; height:0"></div> Table access</div>
  </div>
</div>

<!-- Issues Panel -->
<div class="panel issues-panel" id="issues-panel"></div>

<!-- Tooltip -->
<div class="tooltip" id="tooltip"></div>

<svg id="graph"></svg>

<script>
const graphData = {graph_json};
const issuesData = {issues_json};

// Render issues panel
const issuesPanel = document.getElementById('issues-panel');
if (issuesData.length > 0) {{
  issuesPanel.innerHTML = '<h3>⚠ Issues (' + issuesData.length + ')</h3>' +
    issuesData.map(i => {{
      const cls = i.severity === 'WARNING' ? 'issue-warning' : 'issue-info';
      const icon = i.severity === 'WARNING' ? '🔴' : '🟡';
      return `<div class="issue ${{cls}}">${{icon}} ${{i.message}}</div>`;
    }}).join('');
}} else {{
  issuesPanel.innerHTML = '<h3>✅ No issues</h3>';
}}

// D3 Force Graph
const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select('#graph')
  .attr('width', width)
  .attr('height', height);

// Background gradient
const defs = svg.append('defs');
const bgGrad = defs.append('radialGradient')
  .attr('id', 'bg-gradient')
  .attr('cx', '50%').attr('cy', '50%').attr('r', '60%');
bgGrad.append('stop').attr('offset', '0%').attr('stop-color', '#1a1a2e');
bgGrad.append('stop').attr('offset', '100%').attr('stop-color', '#0f0f1a');

svg.append('rect')
  .attr('width', width)
  .attr('height', height)
  .attr('fill', 'url(#bg-gradient)');

// Add glow filter
const filter = defs.append('filter').attr('id', 'glow');
filter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur');
const feMerge = filter.append('feMerge');
feMerge.append('feMergeNode').attr('in', 'coloredBlur');
feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

// Arrow marker
defs.append('marker')
  .attr('id', 'arrow')
  .attr('viewBox', '0 -5 10 10')
  .attr('refX', 20)
  .attr('refY', 0)
  .attr('markerWidth', 6)
  .attr('markerHeight', 6)
  .attr('orient', 'auto')
  .append('path')
  .attr('d', 'M0,-5L10,0L0,5')
  .attr('fill', '#475569');

const g = svg.append('g');

// Zoom
const zoom = d3.zoom()
  .scaleExtent([0.2, 4])
  .on('zoom', (event) => g.attr('transform', event.transform));
svg.call(zoom);

// Initial zoom to fit
svg.call(zoom.transform, d3.zoomIdentity.translate(width/2, height/2).scale(0.7).translate(-width/2, -height/2));

// Force simulation
const simulation = d3.forceSimulation(graphData.nodes)
  .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(d => {{
    if (d.type === 'belongs_to') return 80;
    if (d.type === 'data_flow') return 160;
    return 120;
  }}))
  .force('charge', d3.forceManyBody().strength(d => {{
    if (d.type === 'repo') return -800;
    return -300;
  }}))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide().radius(d => d.radius + 8))
  .force('x', d3.forceX(width / 2).strength(0.03))
  .force('y', d3.forceY(height / 2).strength(0.03));

// Links
const link = g.append('g')
  .selectAll('line')
  .data(graphData.links)
  .join('line')
  .attr('stroke', d => d.color || '#334155')
  .attr('stroke-width', d => d.type === 'data_flow' ? 2 : 1)
  .attr('stroke-dasharray', d => {{
    if (d.type === 'import') return '6,3';
    if (d.type === 'table_access') return '2,4';
    if (d.type === 'belongs_to') return '1,3';
    return null;
  }})
  .attr('marker-end', d => d.type === 'data_flow' ? 'url(#arrow)' : null)
  .attr('opacity', 0.5);

// Nodes
const node = g.append('g')
  .selectAll('g')
  .data(graphData.nodes)
  .join('g')
  .call(d3.drag()
    .on('start', dragstarted)
    .on('drag', dragged)
    .on('end', dragended));

// Node circles
node.append('circle')
  .attr('r', d => d.radius)
  .attr('fill', d => d.color)
  .attr('opacity', d => d.type === 'repo' ? 0.3 : 0.8)
  .attr('stroke', d => d.color)
  .attr('stroke-width', d => d.type === 'repo' ? 2 : 1)
  .attr('stroke-opacity', 0.6)
  .style('filter', d => d.type === 'repo' ? 'url(#glow)' : null)
  .style('cursor', 'pointer');

// Node labels
node.append('text')
  .attr('class', 'node-label')
  .attr('dy', d => d.radius + 14)
  .attr('font-size', d => d.type === 'repo' ? '11px' : '9px')
  .attr('font-weight', d => d.type === 'repo' ? '600' : '400')
  .text(d => d.label);

// Tooltip
const tooltip = document.getElementById('tooltip');

node.on('mouseover', function(event, d) {{
  // Highlight connected
  const connected = new Set();
  connected.add(d.id);
  graphData.links.forEach(l => {{
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    if (sid === d.id) connected.add(tid);
    if (tid === d.id) connected.add(sid);
  }});

  node.select('circle')
    .attr('opacity', n => connected.has(n.id) ? 1 : 0.1);
  node.select('text')
    .attr('opacity', n => connected.has(n.id) ? 1 : 0.15);
  link.attr('opacity', l => {{
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === d.id || tid === d.id) ? 0.9 : 0.05;
  }});

  // Show tooltip
  if (d.tooltip) {{
    tooltip.textContent = d.tooltip;
    tooltip.style.opacity = 1;
    tooltip.style.left = (event.clientX + 16) + 'px';
    tooltip.style.top = (event.clientY - 10) + 'px';
  }}
}})
.on('mousemove', function(event) {{
  tooltip.style.left = (event.clientX + 16) + 'px';
  tooltip.style.top = (event.clientY - 10) + 'px';
}})
.on('mouseout', function() {{
  node.select('circle').attr('opacity', d => d.type === 'repo' ? 0.3 : 0.8);
  node.select('text').attr('opacity', 1);
  link.attr('opacity', 0.5);
  tooltip.style.opacity = 0;
}});

// Simulation tick
simulation.on('tick', () => {{
  link
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);

  node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
}});

// Drag handlers
function dragstarted(event, d) {{
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}}

function dragged(event, d) {{
  d.fx = event.x;
  d.fy = event.y;
}}

function dragended(event, d) {{
  if (!event.active) simulation.alphaTarget(0);
  // Keep pinned if was dragged
  // d.fx = null; d.fy = null;
}}

// Search
document.getElementById('search').addEventListener('input', function(e) {{
  const q = e.target.value.toLowerCase();
  if (!q) {{
    node.select('circle').attr('opacity', d => d.type === 'repo' ? 0.3 : 0.8);
    node.select('text').attr('opacity', 1);
    link.attr('opacity', 0.5);
    return;
  }}

  const matches = new Set();
  graphData.nodes.forEach(n => {{
    if (n.label.toLowerCase().includes(q) || (n.tooltip && n.tooltip.toLowerCase().includes(q))) {{
      matches.add(n.id);
    }}
  }});

  // Also highlight connected nodes
  const extended = new Set(matches);
  graphData.links.forEach(l => {{
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    if (matches.has(sid)) extended.add(tid);
    if (matches.has(tid)) extended.add(sid);
  }});

  node.select('circle').attr('opacity', d => extended.has(d.id) ? 1 : 0.08);
  node.select('text').attr('opacity', d => extended.has(d.id) ? 1 : 0.1);
  link.attr('opacity', l => {{
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (extended.has(sid) && extended.has(tid)) ? 0.8 : 0.03;
  }});
}});

// Keyboard shortcut: Escape to clear search
document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') {{
    document.getElementById('search').value = '';
    document.getElementById('search').dispatchEvent(new Event('input'));
  }}
}});
</script>
</body>
</html>"""

    return html
