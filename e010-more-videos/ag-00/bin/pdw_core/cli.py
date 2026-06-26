#!/usr/bin/env python3
"""pdw-core CLI."""
import sys
from .db import DB
from . import sync


def main():
    if len(sys.argv) < 2:
        print("Usage: pdw-core <command> [args]")
        print("Commands: db, sync, displays, windows")
        return
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    with DB() as db:
        if cmd == "db":
            if not args:
                print("Usage: pdw-core db <query|metrics|analytics>")
                return
            subcmd = args[0]
            if subcmd == "query" and len(args) > 1:
                for row in db.q(args[1]):
                    print("\t".join(str(v) for v in row.values()))
            elif subcmd == "metrics":
                for row in db.q("SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 10"):
                    print(row)
            elif subcmd == "analytics":
                for row in db.q("SELECT binario, COUNT(*) as count, AVG(duracion_ms) as avg_ms FROM commands GROUP BY binario"):
                    print(row)
            else:
                print("Usage: pdw-core db <query|metrics|analytics>")
        
        elif cmd == "sync":
            subcmd = args[0] if args else "pull"
            if subcmd == "pull":
                result = sync.pull(db)
                print(f"Synced: {result['displays']} displays, {result['windows']} windows")
            elif subcmd == "status":
                print("Displays:", db.q("SELECT name, status FROM displays"))
                print("Windows:", db.q("SELECT app_id, pid, display FROM windows"))
            else:
                print("Usage: pdw-core sync <pull|status>")
        
        elif cmd == "displays":
            for d in db.q("SELECT * FROM displays WHERE status='active'"):
                print(f"{d['name']}\t{d.get('resolution', '?')}\t{d.get('owner', 'free')}")
        
        elif cmd == "windows":
            for w in db.q("SELECT * FROM windows"):
                print(f"{w['app_id']}\t{w['pid']}\t{w['display']}")
        
        else:
            print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
