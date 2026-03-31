#!/usr/bin/env python3
"""
visualize_interactive.py - Interactive Telemetry Dashboard

Generates a self-contained HTML dashboard with signal selection,
overlay support, and configurable layout. No server required.

ブラウザ上で信号選択・重ね描き・レイアウト変更が可能な
自己完結型 HTML ダッシュボードを生成。サーバー不要。

Usage:
    python visualize_interactive.py <csv_file> [options]
    sf log viz <csv_file> -i [options]

Features:
    - Select signals from sidebar checkboxes
    - Overlay multiple signals on the same plot
    - Add/remove subplots dynamically
    - Zoom, pan, hover on all axes
    - Configurable grid layout
"""

import argparse
import csv
import json
import math
import sys
import tempfile
import webbrowser
from pathlib import Path

import numpy as np


# =============================================================================
# Signal definitions with categories
# =============================================================================

SIGNAL_CATEGORIES = {
    'IMU - Gyro': [
        ('gyro_x', 'Gyro X [rad/s]'),
        ('gyro_y', 'Gyro Y [rad/s]'),
        ('gyro_z', 'Gyro Z [rad/s]'),
    ],
    'IMU - Accel': [
        ('accel_x', 'Accel X [m/s²]'),
        ('accel_y', 'Accel Y [m/s²]'),
        ('accel_z', 'Accel Z [m/s²]'),
    ],
    'IMU - Corrected Gyro': [
        ('gyro_corrected_x', 'Gyro Corr X [rad/s]'),
        ('gyro_corrected_y', 'Gyro Corr Y [rad/s]'),
        ('gyro_corrected_z', 'Gyro Corr Z [rad/s]'),
    ],
    'ESKF - Attitude': [
        ('roll_deg', 'Roll [deg]'),
        ('pitch_deg', 'Pitch [deg]'),
        ('yaw_deg', 'Yaw [deg]'),
    ],
    'ESKF - Position': [
        ('pos_x', 'Pos North [m]'),
        ('pos_y', 'Pos East [m]'),
        ('pos_z', 'Pos Down [m]'),
    ],
    'ESKF - Velocity': [
        ('vel_x', 'Vel North [m/s]'),
        ('vel_y', 'Vel East [m/s]'),
        ('vel_z', 'Vel Down [m/s]'),
    ],
    'ESKF - Gyro Bias': [
        ('gyro_bias_x', 'Gyro Bias X [rad/s]'),
        ('gyro_bias_y', 'Gyro Bias Y [rad/s]'),
        ('gyro_bias_z', 'Gyro Bias Z [rad/s]'),
    ],
    'ESKF - Accel Bias': [
        ('accel_bias_x', 'Accel Bias X [m/s²]'),
        ('accel_bias_y', 'Accel Bias Y [m/s²]'),
        ('accel_bias_z', 'Accel Bias Z [m/s²]'),
    ],
    'Control': [
        ('ctrl_throttle', 'Throttle'),
        ('ctrl_roll', 'Roll Cmd'),
        ('ctrl_pitch', 'Pitch Cmd'),
        ('ctrl_yaw', 'Yaw Cmd'),
    ],
    'Sensors - Height': [
        ('baro_altitude', 'Baro Alt [m]'),
        ('tof_bottom', 'ToF Bottom [m]'),
        ('tof_front', 'ToF Front [m]'),
    ],
    'Sensors - Flow': [
        ('flow_x', 'Flow X [counts]'),
        ('flow_y', 'Flow Y [counts]'),
        ('flow_quality', 'Flow Quality'),
    ],
}

COLORS = [
    '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
    '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990',
    '#dcbeff', '#9A6324', '#800000', '#aaffc3', '#808000',
    '#000075', '#a9a9a9',
]


def load_csv(filepath: str) -> dict:
    """Load CSV and return dict of lists (JSON-serializable)"""
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        rows = list(reader)

    data = {}
    for col in columns:
        try:
            vals = [float(r[col]) for r in rows]
            data[col] = vals
        except (ValueError, KeyError):
            pass

    # Compute time in seconds
    if 'timestamp_us' in data:
        t0 = data['timestamp_us'][0]
        data['time_s'] = [(t - t0) / 1e6 for t in data['timestamp_us']]
    elif 'timestamp_ms' in data:
        t0 = data['timestamp_ms'][0]
        data['time_s'] = [(t - t0) / 1e3 for t in data['timestamp_ms']]

    # Compute attitude from quaternion
    if all(k in data for k in ['quat_w', 'quat_x', 'quat_y', 'quat_z']):
        n = len(data['quat_w'])
        data['roll_deg'] = [0.0] * n
        data['pitch_deg'] = [0.0] * n
        data['yaw_deg'] = [0.0] * n
        for i in range(n):
            w, x, y, z = data['quat_w'][i], data['quat_x'][i], data['quat_y'][i], data['quat_z'][i]
            data['roll_deg'][i] = math.degrees(math.atan2(2*(w*x + y*z), 1 - 2*(x*x + y*y)))
            data['pitch_deg'][i] = math.degrees(math.asin(max(-1, min(1, 2*(w*y - z*x)))))
            data['yaw_deg'][i] = math.degrees(math.atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z)))

    return data


def generate_html(data: dict, title: str) -> str:
    """Generate self-contained HTML dashboard"""

    # Filter categories to only include signals present in data
    categories = {}
    for cat, signals in SIGNAL_CATEGORIES.items():
        available = [(key, label) for key, label in signals if key in data]
        if available:
            categories[cat] = available

    # Serialize data to JSON (only signals that exist + time)
    all_keys = set()
    for sigs in categories.values():
        for key, _ in sigs:
            all_keys.add(key)
    all_keys.add('time_s')

    export_data = {k: data[k] for k in all_keys if k in data}

    data_json = json.dumps(export_data, separators=(',', ':'))
    categories_json = json.dumps(categories, ensure_ascii=False)
    colors_json = json.dumps(COLORS)

    n_samples = len(data.get('time_s', []))
    duration = data['time_s'][-1] if 'time_s' in data and n_samples > 0 else 0
    rate = n_samples / duration if duration > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; display: flex; height: 100vh; background: #f5f5f5; }}

/* Sidebar */
#sidebar {{
    width: 260px; min-width: 260px; background: #fff; border-right: 1px solid #ddd;
    overflow-y: auto; padding: 12px; font-size: 13px;
}}
#sidebar h2 {{ font-size: 15px; margin-bottom: 8px; color: #333; }}
.info {{ font-size: 11px; color: #888; margin-bottom: 12px; }}
.cat-title {{
    font-weight: 600; font-size: 12px; color: #555; margin: 10px 0 4px 0;
    cursor: pointer; user-select: none;
}}
.cat-title:hover {{ color: #000; }}
.signal-item {{
    display: flex; align-items: center; padding: 2px 0 2px 12px;
    cursor: pointer; border-radius: 3px;
}}
.signal-item:hover {{ background: #f0f0f0; }}
.signal-item input {{ margin-right: 6px; cursor: pointer; }}
.signal-item label {{ cursor: pointer; font-size: 12px; white-space: nowrap; }}

/* Plot controls */
#controls {{
    padding: 10px 0; border-top: 1px solid #eee; margin-top: 10px;
}}
#controls label {{ font-size: 12px; color: #555; }}
#controls select, #controls input {{ font-size: 12px; margin: 2px 0; }}
button {{
    padding: 6px 12px; font-size: 12px; cursor: pointer; border: 1px solid #ccc;
    border-radius: 4px; background: #fff; margin: 2px;
}}
button:hover {{ background: #e8e8e8; }}
button.primary {{ background: #4363d8; color: #fff; border-color: #4363d8; }}
button.primary:hover {{ background: #3252b5; }}
button.danger {{ color: #e6194b; border-color: #e6194b; }}

/* Main area */
#main {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}
#toolbar {{
    background: #fff; border-bottom: 1px solid #ddd; padding: 8px 16px;
    display: flex; align-items: center; gap: 12px; font-size: 13px;
}}
#plot-area {{ flex: 1; overflow-y: auto; padding: 8px; }}
.plot-container {{
    background: #fff; border: 1px solid #ddd; border-radius: 6px;
    margin-bottom: 8px; position: relative;
}}
.plot-header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 10px; border-bottom: 1px solid #eee; font-size: 12px;
    color: #555; background: #fafafa; border-radius: 6px 6px 0 0;
    cursor: pointer;
}}
.plot-header span {{ font-weight: 600; }}
.plot-container.active {{ border: 2px solid #4363d8; }}
.plot-container.active .plot-header {{ background: #e8ecf8; }}
.plot-div {{ width: 100%; }}
</style>
</head>
<body>

<div id="sidebar">
    <h2>StampFly Telemetry</h2>
    <div class="info">{n_samples} samples, {duration:.1f}s, {rate:.0f} Hz</div>

    <div id="signal-list"></div>

    <div id="controls">
        <button class="primary" onclick="addPlot()">+ Add Plot</button>
        <button onclick="addPreset('imu')">IMU Preset</button>
        <button onclick="addPreset('eskf')">ESKF Preset</button>
        <button onclick="addPreset('bias')">Bias Preset</button>
        <button onclick="clearAll()">Clear All</button>
        <div style="margin-top:6px">
            <label><input type="checkbox" id="sync-x" checked> Sync time axis</label>
        </div>
        <div style="margin-top:8px">
            <label>Target plot:</label>
            <select id="target-plot" style="width:100%" onchange="selectPlot(this.value)"></select>
        </div>
    </div>
</div>

<div id="main">
    <div id="toolbar">
        <span style="font-weight:600">{title}</span>
        <span style="color:#888; font-size:12px">
            Check signals → click "Add to Plot" or double-click signal.
            Zoom: drag | Pan: shift+drag | Reset: double-click plot
        </span>
    </div>
    <div id="plot-area"></div>
</div>

<script>
const DATA = {data_json};
const CATEGORIES = {categories_json};
const COLORS = {colors_json};

let plots = [];  // [{{ id, div, traces: [{{key, label}}] }}]
let plotCounter = 0;
let colorIndex = 0;
let _syncBusy = false;  // Guard against recursive relayout sync

function syncXRange(sourceId, eventData) {{
    if (_syncBusy) return;
    if (!document.getElementById('sync-x').checked) return;

    // Extract x range from relayout event
    let xr = null;
    let autorange = false;
    if ('xaxis.range[0]' in eventData && 'xaxis.range[1]' in eventData) {{
        xr = [eventData['xaxis.range[0]'], eventData['xaxis.range[1]']];
    }} else if ('xaxis.range' in eventData) {{
        xr = eventData['xaxis.range'];
    }} else if ('xaxis.autorange' in eventData) {{
        autorange = true;
    }} else {{
        return;  // Not an x-axis change
    }}

    _syncBusy = true;
    try {{
        plots.forEach(p => {{
            if (p.id === sourceId) return;
            if (autorange) {{
                Plotly.relayout(p.id, {{'xaxis.autorange': true}});
            }} else {{
                Plotly.relayout(p.id, {{'xaxis.range': xr}});
            }}
        }});
    }} finally {{
        _syncBusy = false;
    }}
}}

function nextColor() {{
    const c = COLORS[colorIndex % COLORS.length];
    colorIndex++;
    return c;
}}

// Build signal list sidebar
function buildSidebar() {{
    const container = document.getElementById('signal-list');
    let html = '';
    for (const [cat, signals] of Object.entries(CATEGORIES)) {{
        html += `<div class="cat-title" onclick="toggleCat(this)">▸ ${{cat}}</div>`;
        html += `<div class="cat-signals" style="display:none">`;
        for (const [key, label] of signals) {{
            html += `<div class="signal-item" ondblclick="quickAdd('${{key}}','${{label}}')">`;
            html += `<input type="checkbox" id="cb_${{key}}" value="${{key}}" data-label="${{label}}">`;
            html += `<label for="cb_${{key}}">${{label}}</label>`;
            html += `</div>`;
        }}
        html += `<div style="padding:2px 12px"><button onclick="addCheckedFromCat(this)" style="font-size:11px">Add checked to plot</button></div>`;
        html += `</div>`;
    }}
    container.innerHTML = html;
}}

function toggleCat(el) {{
    const sigs = el.nextElementSibling;
    if (sigs.style.display === 'none') {{
        sigs.style.display = 'block';
        el.textContent = el.textContent.replace('▸', '▾');
    }} else {{
        sigs.style.display = 'none';
        el.textContent = el.textContent.replace('▾', '▸');
    }}
}}

function addCheckedFromCat(btn) {{
    const catDiv = btn.parentElement.parentElement;
    const checkboxes = catDiv.querySelectorAll('input[type=checkbox]:checked');
    if (checkboxes.length === 0) return;

    let plot = getTargetPlot();
    if (!plot) plot = addPlot();

    checkboxes.forEach(cb => {{
        addSignalToPlot(plot, cb.value, cb.dataset.label);
        cb.checked = false;
    }});
}}

function quickAdd(key, label) {{
    let plot = getTargetPlot();
    if (!plot) plot = addPlot();
    addSignalToPlot(plot, key, label);
}}

function getTargetPlot() {{
    const sel = document.getElementById('target-plot');
    if (!sel.value) return null;
    return plots.find(p => p.id === sel.value);
}}

function updateTargetSelect() {{
    const sel = document.getElementById('target-plot');
    const current = sel.value;
    sel.innerHTML = '';
    plots.forEach(p => {{
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.title;
        sel.appendChild(opt);
    }});
    if (current && plots.find(p => p.id === current)) {{
        sel.value = current;
    }} else if (plots.length > 0) {{
        sel.value = plots[plots.length - 1].id;
    }}
}}

function selectPlot(id) {{
    // Set target plot and highlight
    // ターゲットプロットを設定してハイライト
    const sel = document.getElementById('target-plot');
    sel.value = id;
    // Update visual highlight
    document.querySelectorAll('.plot-container').forEach(el => el.classList.remove('active'));
    const container = document.getElementById(`container_${{id}}`);
    if (container) container.classList.add('active');
}}

function addPlot() {{
    plotCounter++;
    const id = `plot_${{plotCounter}}`;
    const title = `Plot ${{plotCounter}}`;

    const area = document.getElementById('plot-area');
    const container = document.createElement('div');
    container.className = 'plot-container';
    container.id = `container_${{id}}`;
    container.innerHTML = `
        <div class="plot-header" onclick="selectPlot('${{id}}')">
            <span style="color:#4363d8;font-size:11px;margin-right:6px">[${{plotCounter}}]</span>
            <span id="title_${{id}}">${{title}}</span>
            <span id="cursor_${{id}}" style="font-family:monospace;font-size:11px;color:#888;margin-left:auto;margin-right:12px"></span>
            <button class="danger" onclick="event.stopPropagation();removePlot('${{id}}')" style="font-size:11px;padding:2px 8px">✕ Remove</button>
        </div>
        <div id="${{id}}" class="plot-div"></div>
    `;
    area.appendChild(container);

    // Click anywhere on plot area to select as target
    // プロットエリアのクリックでターゲットに選択
    container.addEventListener('click', function(e) {{
        // Don't select if clicking remove button
        if (e.target.tagName === 'BUTTON') return;
        selectPlot(id);
    }});

    const layout = {{
        height: 280,
        margin: {{ l: 60, r: 20, t: 10, b: 40 }},
        xaxis: {{
            title: 'Time [s]',
            showspikes: true,
            spikemode: 'across',
            spikesnap: 'cursor',
            spikethickness: 1,
            spikecolor: '#999',
            spikedash: 'dot',
        }},
        yaxis: {{
            title: '',
            showspikes: true,
            spikemode: 'across',
            spikesnap: 'cursor',
            spikethickness: 1,
            spikecolor: '#999',
            spikedash: 'dot',
        }},
        hovermode: 'x unified',
        template: 'plotly_white',
        legend: {{ orientation: 'h', y: 1.12 }},
    }};

    Plotly.newPlot(id, [], layout, {{
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    }});

    // Show cursor position (t, y_axis) in plot header using mouse events
    // マウスイベントでカーソルの軸上の座標 (t, y) をヘッダーに表示
    // plotly_hover returns data values, not cursor position on axis.
    // Use mousemove + Plotly axis mapping to get the actual cursor y-coordinate.
    const plotDiv = document.getElementById(id);

    // Sync X axis on zoom/pan
    // ズーム・パン時に X 軸を同期
    plotDiv.on('plotly_relayout', function(ed) {{ syncXRange(id, ed); }});

    plotDiv.addEventListener('mousemove', function(evt) {{
        const cursorEl = document.getElementById(`cursor_${{id}}`);
        if (!cursorEl) return;
        const bb = plotDiv.getBoundingClientRect();
        const layout = plotDiv._fullLayout;
        if (!layout || !layout.xaxis || !layout.yaxis) return;
        const xa = layout.xaxis;
        const ya = layout.yaxis;
        // Mouse position relative to plot area
        const mouseX = evt.clientX - bb.left;
        const mouseY = evt.clientY - bb.top;
        // Check if inside plot area
        if (mouseX < xa._offset || mouseX > xa._offset + xa._length ||
            mouseY < ya._offset || mouseY > ya._offset + ya._length) {{
            cursorEl.textContent = '';
            return;
        }}
        // Convert pixel to data coordinates
        const tVal = xa.p2d(mouseX - xa._offset);
        const yVal = ya.p2d(mouseY - ya._offset);
        cursorEl.textContent = `t=${{tVal.toFixed(3)}}s  y=${{yVal.toFixed(5)}}`;
    }});
    plotDiv.addEventListener('mouseleave', function() {{
        const cursorEl = document.getElementById(`cursor_${{id}}`);
        if (cursorEl) cursorEl.textContent = '';
    }});

    const plot = {{ id, title, div: plotDiv, traces: [] }};
    plots.push(plot);
    updateTargetSelect();
    selectPlot(id);  // Auto-select new plot as target
    return plot;
}}

function removePlot(id) {{
    const idx = plots.findIndex(p => p.id === id);
    if (idx === -1) return;
    plots.splice(idx, 1);
    const container = document.getElementById(`container_${{id}}`);
    if (container) container.remove();
    updateTargetSelect();
}}

function addSignalToPlot(plot, key, label) {{
    if (!DATA[key] || !DATA.time_s) return;
    // Check if already added
    if (plot.traces.find(t => t.key === key)) return;

    const color = nextColor();
    const trace = {{
        x: DATA.time_s,
        y: DATA[key],
        name: label,
        type: 'scattergl',
        mode: 'lines',
        line: {{ color: color, width: 1 }},
        hovertemplate: `${{label}}: %{{y:.5f}}<extra></extra>`,
    }};

    Plotly.addTraces(plot.id, trace);
    plot.traces.push({{ key, label }});

    // Update title
    const titleEl = document.getElementById(`title_${{plot.id}}`);
    titleEl.textContent = plot.traces.map(t => t.label).join(', ');
}}

function addPreset(name) {{
    if (name === 'imu') {{
        const p1 = addPlot();
        ['gyro_x', 'gyro_y', 'gyro_z'].forEach(k => addSignalToPlot(p1, k, k));
        const p2 = addPlot();
        ['accel_x', 'accel_y', 'accel_z'].forEach(k => addSignalToPlot(p2, k, k));
        const p3 = addPlot();
        ['gyro_corrected_x', 'gyro_corrected_y', 'gyro_corrected_z'].forEach(k => addSignalToPlot(p3, k, k));
    }} else if (name === 'eskf') {{
        const p1 = addPlot();
        ['roll_deg', 'pitch_deg', 'yaw_deg'].forEach(k => addSignalToPlot(p1, k, k));
        const p2 = addPlot();
        ['pos_x', 'pos_y', 'pos_z'].forEach(k => addSignalToPlot(p2, k, k));
        const p3 = addPlot();
        ['vel_x', 'vel_y', 'vel_z'].forEach(k => addSignalToPlot(p3, k, k));
    }} else if (name === 'bias') {{
        const p1 = addPlot();
        ['gyro_bias_x', 'gyro_bias_y', 'gyro_bias_z'].forEach(k => addSignalToPlot(p1, k, k));
        const p2 = addPlot();
        ['accel_bias_x', 'accel_bias_y', 'accel_bias_z'].forEach(k => addSignalToPlot(p2, k, k));
    }}
}}

function clearAll() {{
    plots.forEach(p => {{
        const container = document.getElementById(`container_${{p.id}}`);
        if (container) container.remove();
    }});
    plots = [];
    colorIndex = 0;
    updateTargetSelect();
}}

// Initialize
buildSidebar();
</script>
</body>
</html>"""

    return html


def visualize(filepath: str, groups=None, layout=None, output=None, title=None):
    """Main entry point"""
    print(f"Loading: {filepath}")
    data = load_csv(filepath)

    n = len(data.get('time_s', []))
    dur = data['time_s'][-1] if 'time_s' in data and n > 0 else 0
    rate = n / dur if dur > 0 else 0
    print(f"Samples: {n}, Duration: {dur:.1f}s, Rate: {rate:.0f} Hz")

    if title is None:
        title = f"StampFly — {Path(filepath).name}"

    html = generate_html(data, title)

    if output:
        with open(output, 'w') as f:
            f.write(html)
        print(f"Saved: {output}")
    else:
        tmp = tempfile.NamedTemporaryFile(suffix='.html', delete=False, prefix='stampfly_viz_')
        tmp.write(html.encode('utf-8'))
        tmp.close()
        print(f"Opening in browser: {tmp.name}")
        webbrowser.open(f'file://{tmp.name}')


def main():
    parser = argparse.ArgumentParser(description="Interactive telemetry dashboard")
    parser.add_argument('file', help="CSV telemetry file")
    parser.add_argument('-o', '--output', help="Save HTML to file")
    # These args are accepted for CLI compatibility but the browser UI handles selection
    parser.add_argument('--layout', help="(ignored, use browser UI)")
    parser.add_argument('--groups', nargs='+', help="(ignored, use browser UI)")
    args = parser.parse_args()
    visualize(args.file, output=args.output)
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
