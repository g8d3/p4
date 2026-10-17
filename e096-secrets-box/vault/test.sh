#!/usr/bin/env bash
# vault prototype test. DUMMY VALUES ONLY. Never real secrets here:
# this file, its output, and the agent transcript that runs it are stored
# in cleartext, so any value used here must be treated as already public.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export VAULT_FILE="$(mktemp -d)/test-vault.enc"
export VAULT_PASSPHRASE="dummy-test-passphrase-NOT-A-REAL-SECRET"
export VAULT_TEST_VALUE="dummy-secret-value-NOT-A-REAL-SECRET"
export VAULT_BACKEND="openssl"

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

echo "== vault prototype test (dummy values only) =="
echo "vault file: $VAULT_FILE"
command -v age >/dev/null 2>&1 && echo "(age installed)" || echo "(age NOT installed -> openssl fallback expected)"

# 1. set
"$DIR/vault" set dummy_token >/dev/null 2>&1 || fail "set dummy_token"
pass "set dummy_token"

# 1b. vault file must exist, be 0600, and NOT contain the dummy in cleartext
[ -f "$VAULT_FILE" ] || fail "vault file created"
[ "$(stat -c %a "$VAULT_FILE")" = "600" ] || fail "vault file is mode 600"
if grep -q "dummy-secret-value" "$VAULT_FILE"; then
  fail "vault file leaks secret in cleartext"
fi
pass "vault file encrypted at rest (no cleartext secret, mode 600)"

# 2. list shows the name, never the value
LIST_OUT="$("$DIR/vault" list 2>/dev/null)" || fail "list"
[ "$LIST_OUT" = "dummy_token" ] || fail "list shows exactly dummy_token (got: $LIST_OUT)"
echo "$LIST_OUT" | grep -q "dummy-secret-value" && fail "list leaks value" || true
pass "list shows names only (masked display)"

# 3. get returns the exact dummy value (for piping)
unset VAULT_TEST_VALUE  # get must NOT depend on the test hook
GOT="$("$DIR/vault" get dummy_token 2>/dev/null)" || fail "get dummy_token"
[ "$GOT" = "dummy-secret-value-NOT-A-REAL-SECRET" ] || fail "get returns exact value (got: $GOT)"
pass "get returns exact value"

# 4. get of unknown name fails
if "$DIR/vault" get no_such_name >/dev/null 2>&1; then
  fail "get unknown name should fail"
fi
pass "get unknown name fails cleanly"

# 5. exec injects secret as env into the child only
export VAULT_TEST_VALUE="second-dummy-NOT-A-REAL-SECRET"
"$DIR/vault" set dummy_other >/dev/null 2>&1 || fail "set dummy_other"
unset VAULT_TEST_VALUE
EXEC_OUT="$(VAULT_PASSPHRASE="$VAULT_PASSPHRASE" VAULT_FILE="$VAULT_FILE" \
  "$DIR/vault" exec TOKEN=dummy_token OTHER=dummy_other -- printenv TOKEN OTHER 2>/dev/null)" \
  || fail "exec"
[ "$EXEC_OUT" = "$(printf 'dummy-secret-value-NOT-A-REAL-SECRET\nsecond-dummy-NOT-A-REAL-SECRET')" ] \
  || fail "exec injects both secrets (got: $EXEC_OUT)"
pass "exec injects secrets as env into child process"

# 5b. exec must not leak values to its own stdout/stderr beyond child output
LEAK_CHECK="$(VAULT_PASSPHRASE="$VAULT_PASSPHRASE" VAULT_FILE="$VAULT_FILE" \
  "$DIR/vault" exec TOKEN=dummy_token -- true 2>&1)" || fail "exec true"
[ -z "$LEAK_CHECK" ] || fail "exec leaks on silent run (got: $LEAK_CHECK)"
pass "exec is silent (no leak) when child produces no output"

# 6. wrong passphrase fails (and says so without leaking)
if VAULT_PASSPHRASE="wrong-dummy-passphrase" "$DIR/vault" list >/dev/null 2>&1; then
  fail "wrong passphrase should fail"
fi
pass "wrong passphrase fails cleanly"

# 7. list with two secrets shows both names
LIST2="$("$DIR/vault" list 2>/dev/null)" || fail "list 2"
[ "$LIST2" = "$(printf 'dummy_other\ndummy_token')" ] || fail "list both names sorted (got: $LIST2)"
pass "list shows all names sorted"

rm -f "$VAULT_FILE"
pass "openssl backend cleaned up"

# 8. age backend round-trip (dummy values only; skipped if age not on PATH).
# Exercises the same set/list/get/exec surface through the age backend,
# on a separate isolated temp vault file, then deletes it.
if command -v age >/dev/null 2>&1; then
  export VAULT_FILE="$(mktemp -d)/test-vault-age.enc"
  export VAULT_BACKEND="age"
  echo "== age backend round-trip (dummy values only) =="
  echo "age vault file: $VAULT_FILE"
  export VAULT_TEST_VALUE="dummy-secret-value-NOT-A-REAL-SECRET"
  "$DIR/vault" set dummy_token >/dev/null 2>&1 || fail "age: set dummy_token"
  pass "age: set dummy_token"
  [ -f "$VAULT_FILE" ] || fail "age: vault file created"
  [ "$(stat -c %a "$VAULT_FILE")" = "600" ] || fail "age: vault file is mode 600"
  if grep -q "dummy-secret-value" "$VAULT_FILE"; then
    fail "age: vault file leaks secret in cleartext"
  fi
  head -c 64 "$VAULT_FILE" | grep -q "age-encryption.org" \
    || fail "age: vault file is not age format"
  pass "age: vault file encrypted at rest (age format, no cleartext, mode 600)"
  AGE_LIST_OUT="$("$DIR/vault" list 2>/dev/null)" || fail "age: list"
  [ "$AGE_LIST_OUT" = "dummy_token" ] || fail "age: list shows exactly dummy_token (got: $AGE_LIST_OUT)"
  echo "$AGE_LIST_OUT" | grep -q "dummy-secret-value" && fail "age: list leaks value" || true
  pass "age: list shows names only (masked display)"
  unset VAULT_TEST_VALUE  # get must NOT depend on the test hook
  AGE_GOT="$("$DIR/vault" get dummy_token 2>/dev/null)" || fail "age: get dummy_token"
  [ "$AGE_GOT" = "dummy-secret-value-NOT-A-REAL-SECRET" ] || fail "age: get returns exact value (got: $AGE_GOT)"
  pass "age: get returns exact value"
  if "$DIR/vault" get no_such_name >/dev/null 2>&1; then
    fail "age: get unknown name should fail"
  fi
  pass "age: get unknown name fails cleanly"
  export VAULT_TEST_VALUE="second-dummy-NOT-A-REAL-SECRET"
  "$DIR/vault" set dummy_other >/dev/null 2>&1 || fail "age: set dummy_other"
  unset VAULT_TEST_VALUE
  AGE_EXEC_OUT="$(VAULT_PASSPHRASE="$VAULT_PASSPHRASE" VAULT_FILE="$VAULT_FILE" \
    VAULT_BACKEND=age "$DIR/vault" exec TOKEN=dummy_token OTHER=dummy_other -- printenv TOKEN OTHER 2>/dev/null)" \
    || fail "age: exec"
  [ "$AGE_EXEC_OUT" = "$(printf 'dummy-secret-value-NOT-A-REAL-SECRET\nsecond-dummy-NOT-A-REAL-SECRET')" ] \
    || fail "age: exec injects both secrets (got: $AGE_EXEC_OUT)"
  pass "age: exec injects secrets as env into child process"
  AGE_LEAK_CHECK="$(VAULT_PASSPHRASE="$VAULT_PASSPHRASE" VAULT_FILE="$VAULT_FILE" \
    VAULT_BACKEND=age "$DIR/vault" exec TOKEN=dummy_token -- true 2>&1)" || fail "age: exec true"
  [ -z "$AGE_LEAK_CHECK" ] || fail "age: exec leaks on silent run (got: $AGE_LEAK_CHECK)"
  pass "age: exec is silent (no leak) when child produces no output"
  if VAULT_PASSPHRASE="wrong-dummy-passphrase" VAULT_BACKEND=age VAULT_FILE="$VAULT_FILE" \
      "$DIR/vault" list >/dev/null 2>&1; then
    fail "age: wrong passphrase should fail"
  fi
  pass "age: wrong passphrase fails cleanly"
  AGE_LIST2="$("$DIR/vault" list 2>/dev/null)" || fail "age: list 2"
  [ "$AGE_LIST2" = "$(printf 'dummy_other\ndummy_token')" ] || fail "age: list both names sorted (got: $AGE_LIST2)"
  pass "age: list shows all names sorted"
  rm -f "$VAULT_FILE"
  pass "age backend cleaned up"
else
  echo "SKIP: age backend (age not found on PATH)"
fi

# ---------------------------------------------------------------------------
# fd path (added for e096-secrets-box): the PI WEB server peer cannot use a TTY,
# so the value goes to fd 0 and the passphrase to fd 3. Neither may appear in
# argv, the environment or the file in cleartext.
# ---------------------------------------------------------------------------
echo "== fd path: value on fd 0, passphrase on fd 3 (dummy values only) =="
FD_VALUE="dummy-fd-value-NOT-A-REAL-SECRET-$$"
FD_PASS="dummy-fd-passphrase-NOT-A-REAL-SECRET-$$"
for fdbe in openssl age; do
  command -v age >/dev/null 2>&1 || [ "$fdbe" = "openssl" ] || { echo "SKIP: fd path on age (no age)"; continue; }
  FD_VAULT="$(mktemp -d)/fd-$fdbe.enc"
  # SB_VALUE_OVERRIDE / SB_PASS_OVERRIDE let a case change what travels on the
  # pipes (an empty value, a wrong passphrase) without touching fd_run itself.
  fd_run() { # $@ = vault args, including the backend flag
    VAULT_FILE="$FD_VAULT" VAULT_PASSPHRASE= VAULT_TEST_VALUE= \
      SB_VALUE="${SB_VALUE_OVERRIDE-$FD_VALUE}" SB_PASS="${SB_PASS_OVERRIDE-$FD_PASS}" \
      bash -c 'printf "%s" "$SB_VALUE" | "$0" "$@" 3<<<"$SB_PASS"' "$DIR/vault" "$@"
  }
  fd_run --backend "$fdbe" set fd_token --value-fd 0 --passphrase-fd 3 >/dev/null 2>&1 \
    || fail "$fdbe: fd set"
  pass "$fdbe: fd set (value on fd 0, passphrase on fd 3)"
  [ "$(stat -c %a "$FD_VAULT")" = "600" ] || fail "$fdbe: fd vault mode 600"
  grep -q "$FD_VALUE" "$FD_VAULT" && fail "$fdbe: fd value in cleartext" || true
  pass "$fdbe: fd vault encrypted at rest (mode 600, no cleartext)"
  GOT="$(fd_run --backend "$fdbe" get fd_token --passphrase-fd 3 2>/dev/null)"
  [ "$GOT" = "$FD_VALUE" ] || fail "$fdbe: fd get round-trip (got: $GOT)"
  pass "$fdbe: fd get returns the exact value"
  if SB_PASS_OVERRIDE="wrong-passphrase-$$" fd_run --backend "$fdbe" get fd_token --passphrase-fd 3 >/dev/null 2>&1; then
    fail "$fdbe: wrong passphrase via fd must fail"
  fi
  pass "$fdbe: wrong passphrase via fd fails cleanly"
  if SB_VALUE_OVERRIDE= fd_run --backend "$fdbe" set empty_fd --value-fd 0 --passphrase-fd 3 >/dev/null 2>&1; then
    fail "$fdbe: empty value on fd must abort"
  fi
  pass "$fdbe: empty value on fd aborts (nothing stored)"
  rm -f "$FD_VAULT"
done

echo "== ALL TESTS PASSED (dummy values only, vault file removed) =="
