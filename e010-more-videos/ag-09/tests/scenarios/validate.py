#!/usr/bin/env python3
"""validate.py — Validacion visual de TDS: screenshot + TDS lado a lado.

Genera un reporte HTML que muestra, para cada instante de tiempo:
  [Timestamp] | [Lo que se veia en pantalla] | [Lo que capturo TDS]

Uso:
  python3 tests/scenarios/validate.py
  # Genera tests/output/validate/report.html
"""

import os
import subprocess
import sys
import time
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tds.terminal import TerminalWatcher
from tds.browser import BrowserWatcher
from tds.diff import diff_snapshots, snapshot_key
from tds.stream import StreamEvent, write_stream


OUTDIR = os.path.join(os.path.dirname(__file__), "..", "..", "output", "validate")
os.makedirs(OUTDIR, exist_ok=True)

SESSION = f"tds-val-{os.getpid()}"


def log(msg):
    print(f"  {msg}", file=sys.stderr)


def capture_visual(pane: str, path: str) -> list:
    """Capture tmux pane content as 'visual evidence'."""
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", pane, "-p"],
        capture_output=True, text=True, timeout=5
    )
    lines = result.stdout.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return lines


def generate_report(steps: list, output_path: str):
    """Generate HTML report with visual vs TDS side by side."""
    html = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        "<title>TDS Validation Report</title>",
        "<style>",
        "body { font-family: monospace; background: #0d1117; color: #c9d1d9; margin: 20px; }",
        "h1 { color: #58a6ff; }",
        "h2 { color: #8b949e; margin-top: 30px; }",
        ".step { background: #161b22; border: 1px solid #30363d; border-radius: 6px; margin: 15px 0; padding: 15px; }",
        ".step-header { color: #58a6ff; font-weight: bold; margin-bottom: 10px; }",
        ".side-by-side { display: flex; gap: 20px; }",
        ".panel { flex: 1; }",
        ".panel-title { color: #8b949e; margin-bottom: 5px; }",
        ".panel-visual { background: #0d1117; border: 1px solid #21262d; padding: 10px; white-space: pre; font-size: 12px; overflow-x: auto; }",
        ".tds-text { background: #0d1117; border: 1px solid #21262d; padding: 10px; white-space: pre; font-size: 12px; overflow-x: auto; }",
        ".tds-op-add { color: #3fb950; }",
        ".tds-op-del { color: #f85149; }",
        ".tds-op-mod { color: #d29922; }",
        ".verdict { margin-top: 10px; padding: 8px; border-radius: 4px; }",
        ".pass { background: #1b3624; color: #7ee787; }",
        ".fail { background: #3d1f1f; color: #ff7b72; }",
        ".summary { background: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 6px; }",
        ".stat { display: inline-block; margin-right: 20px; }",
        ".stat-value { font-size: 24px; font-weight: bold; }",
        ".stat-label { font-size: 12px; color: #8b949e; }",
        "</style></head><body>",
        f"<h1>🖼️ TDS Validation Report</h1>",
        f"<p>Generated: {datetime.now().isoformat()}</p>",
        "<p>Cada paso muestra: lo que se veia en pantalla (izquierda) vs lo que TDS capturo (derecha).</p>",
        "<hr>",
    ]

    total = len(steps)
    passed = sum(1 for s in steps if s["match"])
    failed = total - passed

    html.append(f"""
    <div class="summary">
      <h2>Summary</h2>
      <div class="stat"><span class="stat-value">{total}</span><br><span class="stat-label">Total Steps</span></div>
      <div class="stat"><span class="stat-value" style="color:#3fb950">{passed}</span><br><span class="stat-label">Matched</span></div>
      <div class="stat"><span class="stat-value" style="color:#f85149">{failed}</span><br><span class="stat-label">Mismatched</span></div>
    </div>
    """)

    for i, step in enumerate(steps):
        t = step["timestamp"]
        cmd = step["command"]
        visual_text = "\n".join(step["visual"])
        tds_text = "\n".join(step["tds_ops"])
        match = step["match"]

        verdict = "✅ Matched" if match else "❌ Mismatch"
        verdict_class = "pass" if match else "fail"

        html.append(f"""
        <div class="step">
          <div class="step-header">Step {i+1}: t={t:.1f}s — Cmd: <code>{cmd}</code></div>
          <div class="side-by-side">
            <div class="panel">
              <div class="panel-title">📺 Screen (tmux capture-pane)</div>
              <div class="panel-visual">{visual_text}</div>
            </div>
            <div class="panel">
              <div class="panel-title">📝 TDS Text Delta</div>
              <div class="tds-text">{tds_text}</div>
            </div>
          </div>
          <div class="verdict {verdict_class}">{verdict}</div>
        </div>
        """)

    html.append("</body></html>")
    with open(output_path, "w") as f:
        f.write("\n".join(html))

    return passed, failed


def show_side_by_side(steps: list):
    """Display a terminal-friendly side-by-side report of visual vs TDS."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║  TDS VALIDACION — Visual ↔ Texto Delta                           ║")
    print("╚" + "═" * 68 + "╝")

    for i, s in enumerate(steps):
        visual = s["visual"][-6:]  # Last 6 lines
        tds = s["tds_ops"][-6:]    # Last 6 ops

        print(f"\n┌─ Paso {i+1}: {s['command'][:50]} ──┐")
        print(f"│ {'📺 PANTALLA':<30s} │ {'📝 TDS DELTA':<30s} │")
        print("├" + "─" * 31 + "┼" + "─" * 31 + "┤")

        max_rows = max(len(visual), len(tds), 3)
        for j in range(max_rows):
            vis = visual[j] if j < len(visual) else ""
            t = tds[j] if j < len(tds) else ""
            print(f"│ {vis[:30]:30s} │ {t[:30]:30s} │")

        print("└" + "─" * 31 + "┴" + "─" * 31 + "┘")
        print(f"  {'✅ Match' if s['match'] else '❌ Mismatch'}")


def run_terminal_validation():
    """Core test: ejecutar comandos reales y comparar visual vs TDS."""
    log("=" * 60)
    log("VALIDACION TERMINAL: Visual ↔ TDS")
    log("=" * 60)

    # Create tmux session
    subprocess.run(["tmux", "new-session", "-d", "-s", SESSION, "-x", "80", "-y", "24"],
                   check=True)
    time.sleep(0.3)

    # Clear initial prompt
    subprocess.run(["tmux", "send-keys", "-t", SESSION, "clear", "Enter"], check=True)
    time.sleep(0.5)

    watcher = TerminalWatcher(pane=SESSION, interval=0.05)
    steps = []
    last_snapshot = watcher.capture()

    # Comandos de prueba — variados y con contenido visible
    test_commands = [
        ("date", "Mostrar fecha actual"),
        ("echo 'Hola Mundo desde TDS'", "Texto simple"),
        ("ls -la /home/vuos/code/p4/e010-more-videos/ | head -8", "Listado de directorio"),
        ("cat /proc/meminfo | head -4", "Info del sistema"),
        ("for i in A B C D E; do echo \"Item $i\"; done", "Loop con Items"),
        ("echo '{\"key\": \"value\", \"num\": 42}' | python3 -m json.tool", "JSON formateado"),
        ("echo -e 'Linea 1\\nLinea 2\\nLinea 3'", "Multiples lineas"),
        ("df -h / | tail -1", "Disco duro"),
        ("echo 'FIN DE VALIDACION: OK_2026'", "Marca de finalizacion"),
    ]

    for cmd, desc in test_commands:
        log(f"\n  Comando: {cmd}")
        log(f"  Desc:    {desc}")

        # Visual: capturar pantalla ANTES del comando
        visual_before = capture_visual(SESSION,
            os.path.join(OUTDIR, f"vis_{len(steps)}_before.txt"))

        # Ejecutar comando
        subprocess.run(["tmux", "send-keys", "-t", SESSION, cmd, "Enter"], check=True)
        time.sleep(0.5)

        # Visual: capturar pantalla DESPUES del comando
        visual_after = capture_visual(SESSION,
            os.path.join(OUTDIR, f"vis_{len(steps)}_after.txt"))

        # TDS: capturar con watcher y hacer diff
        current = watcher.capture()
        ops = diff_snapshots(last_snapshot, current)

        # Formatear ops para mostrar
        formatted_ops = []
        for op, line in ops:
            prefix = {"+": "+|", "-": "-|", "~": "~|"}.get(op, " |")
            formatted_ops.append(f"{prefix} {line}")

        # Verificar: lo que se ve en pantalla despues del comando
        # deberia contener el comando mismo o su output
        cmd_short = cmd[:40]
        found_in_visual = any(cmd_short in line for line in visual_after)
        found_in_tds = any(cmd_short in op for op in formatted_ops)

        # Match ideal: el comando aparece TANTO en la visual como en TDS
        match = found_in_visual == found_in_tds or (found_in_visual and found_in_tds)

        steps.append({
            "timestamp": len(steps) * 2.0,
            "command": cmd,
            "description": desc,
            "visual": visual_after[-15:],  # ultimas 15 lineas
            "tds_ops": formatted_ops[-10:],  # ultimos 10 ops
            "match": match,
        })

        last_snapshot = current
        log(f"  Visual tiene comando: {found_in_visual}")
        log(f"  TDS    tiene comando: {found_in_tds}")
        log(f"  Match: {'✅' if match else '❌'}")

    # Cleanup
    subprocess.run(["tmux", "kill-session", "-t", SESSION], check=False)

    return steps


def main():
    log("=" * 60)
    log("TDS VALIDATION — Prueba real visual vs TDS")
    log("=" * 60)
    log(f"Output: {OUTDIR}")

    steps = run_terminal_validation()

    # Mostrar side-by-side en terminal
    show_side_by_side(steps)

    passed = sum(1 for s in steps if s["match"])
    failed = len(steps) - passed

    log("")
    log("=" * 60)
    log(f"RESULTADOS: {passed} pasaron, {failed} fallaron")
    log("=" * 60)

    # Also generate HTML
    report_path = os.path.join(OUTDIR, "report.html")
    generate_report(steps, report_path)
    log(f"Reporte HTML: {report_path} (abrir en browser si es posible)")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
