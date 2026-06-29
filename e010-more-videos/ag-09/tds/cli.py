"""tds — Text Delta Stream: captura todo automaticamente.

Uso:
  tds watch              # Vigila terminal + browser en tiempo real
  tds record <nombre>    # Graba video + TDS (Ctrl+C para terminar)
  tds replay <archivo>   # Reconstruye timeline en texto
"""

from __future__ import annotations

import argparse
import sys
import time
import threading

from .stream import format_event
from .terminal import TerminalWatcher
from .browser import BrowserWatcher


def auto_terminal():
    """Descubre la sesion de tmux actual."""
    import subprocess
    try:
        r = subprocess.run(["tmux", "display-message", "-p", "#S"],
                          capture_output=True, text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def auto_displays():
    """Descubre displays virtuales de sway."""
    import json, subprocess
    try:
        r = subprocess.run(["swaymsg", "-t", "get_outputs"],
                          capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            return [o["name"] for o in json.loads(r.stdout)
                   if "HEADLESS" in o.get("name", "")]
    except Exception:
        pass
    return []


def auto_browser():
    """Descubre puerto de Chrome DevTools."""
    import urllib.request
    for port in range(9222, 9230):
        try:
            r = urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1)
            if r.status == 200:
                return port
        except Exception:
            pass
    return None


def auto_browser_url(port):
    """Obtiene URL del primer tab con contenido real."""
    import json, urllib.request
    try:
        r = urllib.request.urlopen(f"http://localhost:{port}/json", timeout=2)
        tabs = json.loads(r.read())
        for t in tabs:
            url = t.get("url", "")
            if not url.startswith("chrome"):
                return url
    except Exception:
        pass
    return "about:blank"


def cmd_watch(args):
    """Vigila terminal + browser, emite stream TDS a stdout."""

    # Info: mostrar que hay disponible y salir
    terminal = auto_terminal()
    browser_port = auto_browser()
    displays = auto_displays()

    print(f"  Terminal:  {terminal or '(no tmux)'}", file=sys.stderr)
    print(f"  Browser:   {'puerto ' + str(browser_port) if browser_port else '(no Chrome)'}",
          file=sys.stderr)
    if displays:
        print(f"  Displays:  {', '.join(displays)}", file=sys.stderr)
    print(file=sys.stderr)

    if args.info:
        return

    if not terminal and not browser_port:
        print("Nada que vigilar.", file=sys.stderr)
        print("  • Abri una sesion de tmux", file=sys.stderr)
        print("  • Inicia Chrome con --remote-debugging-port=9222", file=sys.stderr)
        sys.exit(1)

    events = []
    lock = threading.Lock()
    threads = []
    start_time = time.time()

    def on_event(ev):
        with lock:
            events.append(ev)
            sys.stdout.write(format_event(ev))
            sys.stdout.flush()

    if terminal:
        print(f"  Terminal: {terminal}", file=sys.stderr)
        w = TerminalWatcher(pane=terminal, interval=0.2)
        t = threading.Thread(target=w.start, args=(on_event, start_time), daemon=True)
        t.start()
        threads.append(("term", w, t))

    if browser_port:
        print(f"  Browser:   puerto {browser_port}", file=sys.stderr)
        print(f"  URL:       {browser_url[:60] if browser_url else '(none)'}", file=sys.stderr)
        w = BrowserWatcher(cdp_port=browser_port, interval=0.5,
                          initial_url=browser_url or "about:blank")
        t = threading.Thread(target=w.start, args=(on_event, start_time), daemon=True)
        t.start()
        threads.append(("browser", w, t))

    print(f"  Vigilando. Ctrl+C para terminar.", file=sys.stderr)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n  Terminado. {len(events)} eventos.", file=sys.stderr)
        for kind, w, t in threads:
            w.stop()


def cmd_record(args):
    """Graba video + TDS simultaneamente. Auto-descubre todo."""
    from .recorder import CombinedRecorder

    name = args.name or f"tds-{int(time.time())}"

    # Auto-descubrir
    terminal = auto_terminal()
    browser_port = auto_browser()
    browser_url = auto_browser_url(browser_port) if browser_port else None
    displays = auto_displays()

    if not terminal and not browser_port:
        print("No hay nada que grabar (sin terminal ni browser).", file=sys.stderr)
        sys.exit(1)

    if not displays:
        print("No hay displays virtuales. Inicia sway primero.", file=sys.stderr)
        print("  pdw init", file=sys.stderr)
        sys.exit(1)

    # Elegir display
    if args.display:
        if args.display not in displays:
            print(f"Display {args.display} no encontrado. Disponibles: {', '.join(displays)}",
                  file=sys.stderr)
            sys.exit(1)
        display = args.display
    else:
        display = displays[0]
        if len(displays) > 1:
            print(f"  (usando {display}. Para cambiar: tds record -d <display>)",
                  file=sys.stderr)

    print(f"  Terminal:  {terminal or '(ninguno)'}", file=sys.stderr)
    print(f"  Browser:   {'puerto ' + str(browser_port) if browser_port else '(ninguno)'}",
          file=sys.stderr)
    print(f"  Display:   {display}", file=sys.stderr)
    if args.duration:
        print(f"  Duracion:  {args.duration}s", file=sys.stderr)
    else:
        print(f"  Duracion:  hasta Ctrl+C", file=sys.stderr)

    rec = CombinedRecorder(
        display=display,
        name=name,
        duration=args.duration,  # None = unlimited
        term_pane=terminal,
        browser_port=browser_port,
        browser_url=browser_url,
        output_dir=args.output,
    )
    rec.run()


def cmd_replay(args):
    """Reconstruye un archivo .tds como timeline de texto en stdout."""
    from .replay import reconstruct_timeline
    from .stream import read_stream
    events = read_stream(args.input)
    timeline = reconstruct_timeline(args.input, compact=args.compact)
    for line in timeline:
        print(line)
    print(f"\n({len(events)} eventos, {len(timeline)} lineas)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="tds — captura cambios en pantalla como texto"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # watch
    wp = subparsers.add_parser("watch", help="Vigilar cambios en tiempo real")
    wp.add_argument("-i", "--info", action="store_true",
                    help="Mostrar info del sistema y salir (sin vigilar)")
    wp.set_defaults(func=cmd_watch)

    # record
    rp = subparsers.add_parser("record", help="Grabar video + TDS")
    rp.add_argument("name", nargs="?", default=None,
                    help="Nombre/directorio de salida (default: tds-<timestamp>)")
    rp.add_argument("-d", "--display", default=None,
                    help="Display virtual (default: auto-detecta HEADLESS-1,2,...)")
    rp.add_argument("-D", type=float, default=None,
                    help="Duracion en segundos (default: ilimitado, Ctrl+C para terminar)")
    rp.add_argument("-o", default=None,
                    help="Directorio de salida (default: output/<name>/)")
    rp.set_defaults(func=cmd_record)

    # replay
    rlp = subparsers.add_parser("replay", help="Reconstruir .tds como texto")
    rlp.add_argument("input", help="Archivo .tds")
    rlp.add_argument("-c", "--compact", action="store_true",
                    help="Opcion compacta (agrupa deltas grandes)")
    rlp.set_defaults(func=cmd_replay)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
