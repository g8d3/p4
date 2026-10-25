#!/usr/bin/env python3
"""FiloEterno builder: full task pipeline. Stdlib + forge + gateway model.

Usage: build.py 02-lottery-coin
Steps (bounded): gen contract -> build (fix<=2) -> gen tests -> test (fix<=2)
-> audit -> fix critical/high (<=1) -> retest -> red-first probe -> anvil
deploy receipt -> LESSONS entry. Stops loudly at first unfixable step.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from loop import call_model, extract_json  # noqa: E402

NEEDS = json.load(open(os.path.join(ROOT, "needs.json")))
DATA = os.path.join(ROOT, "data")
ENV = dict(os.environ, PATH=os.path.expanduser("~/.foundry/bin") + ":" +
           os.environ.get("PATH", ""))


def spec(task):
    raw = open(os.path.join(ROOT, "tasks", task, "SPEC.md")).read()
    out = {}
    for k in ("contract_file", "contract_name", "probe_pattern", "probe_replacement"):
        m = re.search(rf"^{k}:\s*(.+)$", raw, re.M)
        out[k] = m.group(1).strip() if m else ""
    missing = [k for k in ("contract_file", "contract_name", "probe_pattern") if not out[k]]
    assert not missing, f"SPEC.md missing fields: {missing} — fix the SPEC, never guess"
    parts = re.split(r"^##\s+", raw, flags=re.M)
    for p in parts:
        if p.startswith("CONTRACT"):
            out["contract"] = p[len("CONTRACT"):].strip()
        elif p.startswith("TESTS"):
            out["tests"] = p[len("TESTS"):].strip()
    return out


def forge(args, cwd, timeout=300):
    return subprocess.run(["forge"] + args, cwd=cwd, capture_output=True,
                          text=True, timeout=timeout, env=ENV)


def extract_code(raw):
    """Solidity out of a reply: fenced block first, JSON-escaped second."""
    m = re.search(r"```(?:solidity)?\s*(.*?)```", raw, re.S)
    if m and "pragma solidity" in m.group(1):
        return m.group(1).strip()
    d = extract_json(raw)
    if d and "solidity" in d:
        return d["solidity"]
    return None


def gen_json(mission, max_tokens=16000, dump="last_build_raw.txt"):
    raw = call_model(mission, max_tokens=max_tokens)
    open(os.path.join(DATA, dump), "w").write(raw)
    code = extract_code(raw)
    assert code, "model gave no usable solidity"
    m = re.search(r"^NOTE:\s*(.+)$", raw, re.M)
    note = (m.group(1).strip() if m else (extract_json(raw) or {}).get("note", ""))
    return {"solidity": code, "note": note[:140]}
    return d


def main(task):
    td = os.path.join(ROOT, "tasks", task)
    sp = spec(task)
    src = os.path.join(td, "src", sp["contract_file"])
    os.makedirs(os.path.join(td, "src"), exist_ok=True)
    os.makedirs(os.path.join(td, "test"), exist_ok=True)
    if not os.path.exists(os.path.join(td, "foundry.toml")):
        open(os.path.join(td, "foundry.toml"), "w").write(
            "[profile.default]\nsrc = 'src'\nout = 'out'\nlibs = ['lib']\nsolc_version = '0.8.26'\n")
    log = []

    if not os.path.exists(src):
        d = gen_json("Reply with the FULL source in one ```solidity fenced block, then a line NOTE: <140 chars plain words>.\n{sp['contract']}")
        open(src, "w").write(d["solidity"])
        log.append(f"contract {len(d['solidity'])}b note={d.get('note', '')[:140]}")

    for attempt in range(3):
        p = forge(["build"], td)
        if p.returncode == 0:
            log.append("build ok")
            break
        d = gen_json("The contract below FAILS TO COMPILE. Reply with the FULL fixed source in one ```solidity fenced block, then NOTE: <140 chars>. "
                     f"Errors:\n{(p.stdout + p.stderr)[-3000:]}\nSOURCE:\n{open(src).read()}")
        open(src, "w").write(d["solidity"])
    else:
        return fail(task, log, "build never passed")

    tpath = os.path.join(td, "test", sp["contract_name"] + ".t.sol")
    if not os.path.exists(tpath):
        d = gen_json("Reply with the FULL test source in one ```solidity fenced block, then NOTE: <140 chars>.\n{sp['tests']}\nSOURCE:\n{open(src).read()}")
        open(tpath, "w").write(d["solidity"])
        log.append("tests generated")

    for attempt in range(3):
        p = forge(["test"], td)
        tail = (p.stdout + p.stderr)[-1500:]
        if p.returncode == 0 and "FAILED" not in tail:
            log.append("tests green")
            break
        d = gen_json("Tests FAIL. Reply JSON only: {\"solidity\": \"<full fixed CONTRACT source>\", "
                     "\"note\": \"...\"}. Fix the CONTRACT (tests encode the spec, do not "
                     f"soften them).\nOutput:\n{tail}\nCONTRACT:\n{open(src).read()}\n"
                     f"TESTS:\n{open(tpath).read()}")
        open(src, "w").write(d["solidity"])
    else:
        return fail(task, log, "tests never green")

    audit_raw = call_model("You audit this Solidity 0.8.26 contract. Checklist: reentrancy, "
                           "access control, integer math, vote/ticket manipulation, treasury/pool "
                           "drain, DoS, zero-address. Reply JSON only: {\"findings\": "
                           "[{\"severity\": \"critical|high|medium|low|info\", \"title\": \"...\", "
                           f"\"detail\": \"...\", \"fix\": \"...\"}}], \"note\": \"...\"}}.\nSOURCE:\n{open(src).read()}",
                           max_tokens=16000)
    ad = extract_json(audit_raw)
    assert ad and "findings" in ad, "no usable audit"
    open(os.path.join(td, "AUDIT.md"), "w").write(
        "# Self-audit (model)\n\n" + "\n".join(
            f"- [{f['severity']}] {f['title']}: {f['detail']} | fix: {f.get('fix', '')}"
            for f in ad["findings"]))
    crit = [f for f in ad["findings"] if f["severity"] in ("critical", "high")]
    log.append(f"audit: {len(ad['findings'])} findings, {len(crit)} critical/high")
    if crit:
        d = gen_json("Patch this contract to resolve these CRITICAL/HIGH findings with minimal "
                     "changes. Keep all existing tests passing. Do NOT print the tests back, "
                     "only the contract. Reply with the FULL fixed source in one ```solidity fenced block, then NOTE: <140 chars>.\nFindings:\n" +
                     "\n".join(f"- [{f['severity']}] {f['title']}: {f['fix']}" for f in crit) +
                     f"\nSOURCE:\n{open(src).read()}", max_tokens=20000)
        open(src, "w").write(d["solidity"])
        p = forge(["test"], td)
        if p.returncode != 0 or "FAILED" in p.stdout:
            return fail(task, log, "tests red after audit fix")
        log.append("audit fixes applied, tests still green")

    probe(task, sp)
    log.append("red-first probe passed")
    receipt(task, td, sp)
    log.append("deployed locally")
    with open(NEEDS["lessons_file"], "a") as f:
        f.write(f"\n## {now()} {task} BUILT\n" + "".join(f"- {l}\n" for l in log))
    print("\n".join(log))
    print(f"{task}: BUILT")


def probe(task, sp=None):
    sp = sp or spec(task)
    td = os.path.join(ROOT, "tasks", task)
    tmp = tempfile.mkdtemp(prefix="probe-")
    try:
        for sub in ("src", "test", "foundry.toml"):
            s, dst = os.path.join(td, sub), os.path.join(tmp, sub)
            if os.path.isdir(s):
                shutil.copytree(s, dst)
            else:
                shutil.copy(s, dst)
        f = os.path.join(tmp, "src", sp["contract_file"])
        src = open(f).read()
        assert sp["probe_pattern"] in src, "probe pattern moved — update SPEC"
        open(f, "w").write(src.replace(sp["probe_pattern"], sp["probe_replacement"]))
        p = forge(["test"], tmp)
        red = p.returncode != 0 or "FAILED" in p.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(NEEDS["lessons_file"], "a") as f2:
        f2.write(f"\n## {now()} {task} mutation probe: "
                 f"{'PROBE-OK (gate caught the mutation)' if red else 'GATE-BROKEN'}\n")
    if not red:
        sys.exit(f"{task}: GATE-BROKEN — tests stayed green on broken math")
    return True


def receipt(task, td, sp):
    anvil = subprocess.Popen(["anvil", "--port", "8547"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    try:
        import time as _t
        _t.sleep(2)
        p = forge(["create", f"src/{sp['contract_file']}:{sp['contract_name']}",
                   "--broadcast", "--rpc-url", "http://127.0.0.1:8547",
                   "--mnemonic", "test test test test test test test test test test test junk"],
                  td)
        out = p.stdout + p.stderr
        m = re.search(r"Deployed to:\s*(\S+)", out)
        assert m, f"deploy failed:\n{out[-1000:]}"
        open(os.path.join(td, "RECEIPT.md"), "w").write(
            f"# {task} deploy receipt (local anvil, no real chain, no real money)\n"
            f"- deployed to: {m.group(1)}\n- contract: {sp['contract_file']} (audited, probe-gated)\n")
    finally:
        anvil.terminate()


def now():
    import datetime as dt
    return dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")


def fail(task, log, why):
    with open(NEEDS["lessons_file"], "a") as f:
        f.write(f"\n## {now()} {task} STUCK: {why}\n" + "".join(f"- {l}\n" for l in log))
    print("\n".join(log))
    sys.exit(f"{task}: STUCK — {why}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: build.py <task-dir>")
    main(sys.argv[1])
