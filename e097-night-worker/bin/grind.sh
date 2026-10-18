#!/bin/bash
# GRINDER — benchmark transcript-tax n=10. Protocolo: /home/vuos/code/p4/e097-night-worker/PROTOCOL.md
# Salidas ultra-terras: solo fallos + resumen por celda a stdout/TERRA.
# Todo número al CSV. Retry 1x por run; 3 fallos en celda -> FAIL y sigue.
# No toca: e095-tps-monitor, p4 git, secretos (solo nombres de env vars en logs).
set -u
CSV=/home/vuos/code/p4/e097-night-worker/bench.csv
DETAIL=/home/vuos/code/p4/e097-night-worker/grind-detail.log
TERRA=/home/vuos/code/p4/e097-night-worker/grind-terra.log
COSTACC=/home/vuos/code/p4/e097-night-worker/cost.acc
FAIL_LIMIT=3
# Tarifas ESTIMADAS deepseek (USD por MTok) — solo para techo $15. Fuente: docs públicas deepseek.
IN_MISS=0.30
IN_HIT=0.075
OUT_R=1.20

[ -f "$CSV" ] || echo "harness,size,run,wall_s,llm_ms,total_ms,unacc_ms,in_tok,cache_tok,out_tok,notes" > "$CSV"
echo "0.0" > "$COSTACC"
: >> "$DETAIL"

terra(){ echo "$*" | tee -a "$TERRA"; }
log(){ echo "$*" >> "$DETAIL"; }

cost_add_pi(){ # in cache out -> añade costo, imprime acumulado
  python3 - "$1" "$2" "$3" <<'EOF'
import sys
inn, cache, out = (float(sys.argv[1] or 0), float(sys.argv[2] or 0), float(sys.argv[3] or 0))
c = max(inn-cache,0)*0.30/1e6 + cache*0.075/1e6 + out*1.20/1e6
acc = float(open('/home/vuos/code/p4/e097-night-worker/cost.acc').read().strip() or 0) + c
open('/home/vuos/code/p4/e097-night-worker/cost.acc','w').write(str(acc))
print(f"{acc:.4f}")
EOF
}

pi_row(){ # T0 DIR first|last -> "llm,total,unacc,in,cache,out,ncands" o "PARSEFAIL:..."
  python3 - "$1" "$2" "$3" <<'EOF'
import json
T0, d, which = __import__('sys').argv[1], __import__('sys').argv[2], __import__('sys').argv[3]
try:
    ts=[json.loads(l) for l in open(d+'/.pi-web/tps-turns.jsonl')]
    cands=[x for x in ts if x['ts']>=T0]
    assert cands, "no-turn-after-T0"
    t=cands[-1] if which=='last' else cands[0]
    idx=ts.index(t)
    hs=[json.loads(l) for l in open(d+'/.pi-web/tps-history.jsonl')]
    cache=hs[idx].get('cacheRead','') if idx<len(hs) else ''
    llm=t['llmDurationMs']; total=t['turnMsTotal']; toolms=t.get('toolMsTotal',0)
    print(f"{llm},{total},{total-llm-toolms},{t['input']},{cache},{t['output']},{len(cands)}")
except Exception as e:
    print(f"PARSEFAIL:{e}")
EOF
}

zero_usage(){ # logfile -> "prompt,cached,completion,finaltext" o "PARSEFAIL:..."
  python3 - "$1" <<'EOF'
import json,sys
u=None; final=None
try:
  for line in open(sys.argv[1]):
    s=line[line.find('{'):]
    if not s.strip(): continue
    try: o=json.loads(s)
    except Exception: continue
    if o.get('type')=='usage': u=o
    if o.get('type')=='final': final=o.get('text','')
  assert u, "no-usage-line"
  print(f"{u.get('promptTokens','')},{u.get('cachedInputTokens','')},{u.get('completionTokens','')},{(final or '').strip()}")
except Exception as e:
  print(f"PARSEFAIL:{e}")
EOF
}

check_cost(){ # aborta si >15
  acc=$(cat "$COSTACC")
  big=$(python3 -c "print(1 if float('$acc')>15 else 0)")
  if [ "$big" = "1" ]; then terra "COST-CEILING: acumulado \$$acc > \$15. Paro todo."; exit 42; fi
}

# ---- celda pi (pi-TS) ----
pi_cell(){ # harness size DIR FILE
  local H=$1 SZ=$2 DIR=$3 FILE=$4 fails=0
  log "=== cell $H $SZ ==="
  # ingest run=0 (sesión fresca: pi -p sin -c)
  local ok=0 att=0
  while [ $att -lt 2 ] && [ $ok -eq 0 ]; do
    att=$((att+1))
    T0=$(date -u +%FT%TZ); S=$(date +%s.%N)
    ( cd "$DIR" && timeout 300 pi -p --provider opencode-go --model deepseek-v4.1-flash "Read the entire $FILE and then reply with exactly the word DONE. Call no other tools." > /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r0-a$att.log 2>&1 )
    rc=$?; E=$(date +%s.%N); W=$(python3 -c "print(f'{$E-($S):.2f}')")
    if [ $rc -eq 0 ] && grep -q '^DONE$' /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r0-a$att.log; then
      row=$(pi_row "$T0" "$DIR" last); nc=$(echo "$row" | awk -F, '{print $NF}'); m=$(echo "$row" | cut -d, -f1-6)
      if [[ "$row" == PARSEFAIL* ]]; then log "FAIL $H $SZ r0 att$att parse: $row";
      else
        acc=$(cost_add_pi "$(echo $m|cut -d, -f4)" "$(echo $m|cut -d, -f5)" "$(echo $m|cut -d, -f6)")
        echo "$H,$SZ,0,$W,$m,ingest:last-of-$nc|attempt-$att|cost\$$acc" | awk -F, '{OFS=","; print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11"|"$12"|"$13}' >> "$CSV"
        log "OK $H $SZ r0 wall=$W row=[$m] turns=$nc acc=\$$acc"; ok=1
      fi
    else log "FAIL $H $SZ r0 att$att rc=$rc wall=$W (sin DONE)";
    fi
  done
  if [ $ok -eq 0 ]; then fails=$((fails+1)); echo "$H,$SZ,0,$W,,,,,,FAIL:ingest-sin-DONE" >> "$CSV"; terra "FAIL $H-$SZ run0 ingest sin DONE tras 2 intentos"; fi
  # pongs 1..10
  local r
  for r in $(seq 1 10); do
    ok=0; att=0
    while [ $att -lt 2 ] && [ $ok -eq 0 ]; do
      att=$((att+1))
      T0=$(date -u +%FT%TZ); S=$(date +%s.%N)
      ( cd "$DIR" && timeout 180 pi -p --provider opencode-go --model deepseek-v4.1-flash -c "Reply with exactly the word PONG. Call no tools." > /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r$r-a$att.log 2>&1 )
      rc=$?; E=$(date +%s.%N); W=$(python3 -c "print(f'{$E-($S):.2f}')")
      if [ $rc -eq 0 ] && grep -q '^PONG$' /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r$r-a$att.log; then
        row=$(pi_row "$T0" "$DIR" first); m=$(echo "$row" | cut -d, -f1-6)
        if [[ "$row" == PARSEFAIL* ]]; then log "FAIL $H $SZ r$r att$att parse: $row";
        else
          acc=$(cost_add_pi "$(echo $m|cut -d, -f4)" "$(echo $m|cut -d, -f5)" "$(echo $m|cut -d, -f6)")
          echo "$H,$SZ,$r,$W,$m,ok|attempt-$att" | awk -F, '{OFS=","; print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11}' >> "$CSV"
          log "OK $H $SZ r$r wall=$W row=[$m] acc=\$$acc"; ok=1
        fi
      else log "FAIL $H $SZ r$r att$att rc=$rc wall=$W (sin PONG)";
      fi
    done
    if [ $ok -eq 0 ]; then fails=$((fails+1)); echo "$H,$SZ,$r,$W,,,,,,FAIL:pong-sin-PONG" >> "$CSV"; terra "FAIL $H-$SZ run$r sin PONG tras 2 intentos ($fails fallos celda)";
      if [ $fails -ge $FAIL_LIMIT ]; then echo "$H,$SZ,CELL-FAIL,,,,,,,FAIL:3-fallos" >> "$CSV"; terra "CELL-FAIL $H-$SZ: 3 fallos, sigo a la siguiente"; return 1; fi
    fi
    check_cost
  done
  summarize "$H" "$SZ"
}

# ---- celda zero ----
zero_cell(){ # harness size DIR FRESH_ROUNDS("0 1..10" o "1..10")
  local H=$1 SZ=$2 DIR=$3 INGEST=$4 fails=0
  log "=== cell $H $SZ ingest=$INGEST ==="
  if [ "$INGEST" = "yes" ]; then
    ok=0; att=0
    while [ $att -lt 2 ] && [ $ok -eq 0 ]; do
      att=$((att+1))
      S=$(date +%s.%N)
      ( cd "$DIR" && timeout 300 zero exec --auto medium -o stream-json "Read the entire LARGE.txt and then reply with exactly the word DONE. Call no other tools." > /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r0-a$att.log 2>&1 )
      rc=$?; E=$(date +%s.%N); W=$(python3 -c "print(f'{$E-($S):.2f}')")
      u=$(zero_usage /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r0-a$att.log); fin=$(echo "$u"|cut -d, -f4)
      if [ $rc -eq 0 ] && [ "$fin" = "DONE" ]; then
        m=$(echo "$u"|cut -d, -f1-3); ms=$(python3 -c "print(round(float('$W')*1000))")
        acc=$(cost_add_pi "$(echo $m|cut -d, -f1)" "$(echo $m|cut -d, -f2)" "$(echo $m|cut -d, -f3)")
        echo "$H,$SZ,0,$W,,$ms,,$(echo $m|awk -F, '{print $1","$2","$3}'),ingest:fresh-session|attempt-$att|cost\$$acc" >> "$CSV"
        log "OK $H $SZ r0 wall=$W usage=[$m] acc=\$$acc"; ok=1
      else log "FAIL $H $SZ r0 att$att rc=$rc wall=$W fin=[$fin] u=[$u]";
      fi
    done
    if [ $ok -eq 0 ]; then fails=$((fails+1)); echo "$H,$SZ,0,$W,,,,,,FAIL:ingest" >> "$CSV"; terra "FAIL $H-$SZ run0 ingest tras 2 intentos"; fi
  fi
  local r first_extra=""
  for r in $(seq 1 10); do
    ok=0; att=0; RESUME="--resume"
    if [ "$r" = "1" ] && [ "$INGEST" = "no-anchor" ]; then RESUME=""; first_extra="fresh-anchor(no-resume)|"; fi
    while [ $att -lt 2 ] && [ $ok -eq 0 ]; do
      att=$((att+1))
      S=$(date +%s.%N)
      # shellcheck disable=SC2086
      ( cd "$DIR" && timeout 180 zero exec $RESUME --auto medium -o stream-json "Reply with exactly the word PONG. Call no tools." > /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r$r-a$att.log 2>&1 )
      rc=$?; E=$(date +%s.%N); W=$(python3 -c "print(f'{$E-($S):.2f}')")
      u=$(zero_usage /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r$r-a$att.log); fin=$(echo "$u"|cut -d, -f4)
      if [ $rc -eq 0 ] && [ "$fin" = "PONG" ]; then
        m=$(echo "$u"|cut -d, -f1-3); ms=$(python3 -c "print(round(float('$W')*1000))")
        acc=$(cost_add_pi "$(echo $m|cut -d, -f1)" "$(echo $m|cut -d, -f2)" "$(echo $m|cut -d, -f3)")
        echo "$H,$SZ,$r,$W,,$ms,,$(echo $m|awk -F, '{print $1","$2","$3}'),${first_extra}total=wall|attempt-$att" >> "$CSV"
        log "OK $H $SZ r$r wall=$W usage=[$m] acc=\$$acc"; ok=1
      else log "FAIL $H $SZ r$r att$att rc=$rc wall=$W fin=[$fin] u=[$u]";
      fi
    done
    first_extra=""
    if [ $ok -eq 0 ]; then fails=$((fails+1)); echo "$H,$SZ,$r,$W,,,,,,FAIL:pong" >> "$CSV"; terra "FAIL $H-$SZ run$r tras 2 intentos ($fails fallos celda)";
      if [ $fails -ge $FAIL_LIMIT ]; then echo "$H,$SZ,CELL-FAIL,,,,,,,FAIL:3-fallos" >> "$CSV"; terra "CELL-FAIL $H-$SZ: 3 fallos, sigo a la siguiente"; return 1; fi
    fi
    check_cost
  done
  summarize "$H" "$SZ"
}

# ---- celda pirust (wall-only) ----
pirust_cell(){ # harness size DIR FILE
  local H=$1 SZ=$2 DIR=$3 FILE=$4 fails=0
  log "=== cell $H $SZ ==="
  ok=0; att=0
  while [ $att -lt 2 ] && [ $ok -eq 0 ]; do
    att=$((att+1))
    S=$(date +%s.%N)
    ( cd "$DIR" && timeout 300 pi-rust -p --provider deepseek --model deepseek-chat --yolo "Read the entire $FILE and then reply with exactly the word DONE. Call no other tools." > /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r0-a$att.log 2>&1 )
    rc=$?; E=$(date +%s.%N); W=$(python3 -c "print(f'{$E-($S):.2f}')")
    if [ $rc -eq 0 ] && grep -q '^DONE$' /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r0-a$att.log; then
      echo "$H,$SZ,0,$W,,,,,,ingest:wall-only|attempt-$att" >> "$CSV"; log "OK $H $SZ r0 wall=$W"; ok=1
    else log "FAIL $H $SZ r0 att$att rc=$rc wall=$W";
    fi
  done
  if [ $ok -eq 0 ]; then fails=$((fails+1)); echo "$H,$SZ,0,$W,,,,,,FAIL:ingest" >> "$CSV"; terra "FAIL $H-$SZ run0 ingest tras 2 intentos"; fi
  local r
  for r in $(seq 1 10); do
    ok=0; att=0
    while [ $att -lt 2 ] && [ $ok -eq 0 ]; do
      att=$((att+1))
      S=$(date +%s.%N)
      ( cd "$DIR" && timeout 180 pi-rust -p --provider deepseek --model deepseek-chat --yolo -c "Reply with exactly the word PONG. Call no tools." > /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r$r-a$att.log 2>&1 )
      rc=$?; E=$(date +%s.%N); W=$(python3 -c "print(f'{$E-($S):.2f}')")
      if [ $rc -eq 0 ] && grep -q '^PONG$' /home/vuos/code/p4/e097-night-worker/run-$H-$SZ-r$r-a$att.log; then
        echo "$H,$SZ,$r,$W,,,,,,wall-only|attempt-$att" >> "$CSV"; log "OK $H $SZ r$r wall=$W"; ok=1
      else log "FAIL $H $SZ r$r att$att rc=$rc wall=$W";
      fi
    done
    if [ $ok -eq 0 ]; then fails=$((fails+1)); echo "$H,$SZ,$r,$W,,,,,,FAIL:pong" >> "$CSV"; terra "FAIL $H-$SZ run$r tras 2 intentos ($fails fallos celda)";
      if [ $fails -ge $FAIL_LIMIT ]; then echo "$H,$SZ,CELL-FAIL,,,,,,,FAIL:3-fallos" >> "$CSV"; terra "CELL-FAIL $H-$SZ: 3 fallos, sigo a la siguiente"; return 1; fi
    fi
  done
  summarize "$H" "$SZ"
}

summarize(){ # harness size -> medias al TERRA
  python3 - "$1" "$2" <<'EOF'
import csv,sys
H,SZ=sys.argv[1],sys.argv[2]
rows=[r for r in csv.DictReader(open('/home/vuos/code/p4/e097-night-worker/bench.csv')) if r['harness']==H and r['size']==SZ and r['run'] not in ('0','CELL-FAIL','FAIL')]
def avg(k):
  v=[float(r[k]) for r in rows if r[k]]
  return sum(v)/len(v) if v else float('nan')
n=len(rows)
print(f"CELL-DONE {H}-{SZ}: n={n} wall_avg={avg('wall_s'):.2f}s llm_avg={avg('llm_ms'):.0f}ms unacc_avg={avg('unacc_ms'):.0f}ms in_avg={avg('in_tok'):.0f} cache_avg={avg('cache_tok'):.0f} out_avg={avg('out_tok'):.0f}")
EOF
}

# ---- main ----
rm -rf /tmp/duel/piS/.pi-web   # estado limpio post-probes (sesión fresca para ingest)
terra "GRIND-START $(date -u +%FT%TZ) — 6 celdas, n=10"
pi_cell     pi     S /tmp/duel/piS SMALL.txt || true
pi_cell     pi     L /tmp/duel/piL LARGE.txt || true
zero_cell   zero   S /tmp/duel/zeroS no-anchor || true
zero_cell   zero   L /tmp/duel/zeroL yes || true
pirust_cell pirust S /tmp/duel/pirustS SMALL.txt || true
pirust_cell pirust L /tmp/duel/pirustL LARGE.txt || true
acc=$(cat "$COSTACC")
terra "GRIND-END $(date -u +%FT%TZ) filas=$(($(wc -l < "$CSV")-1)) costo-est=\$$acc CSV=$CSV"
