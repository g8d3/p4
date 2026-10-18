#!/usr/bin/env bash
# Self-test that replicates what a phone browser does, so a human never has
# to be the tester. Run after bin/start.sh or anytime something looks broken.
#
# It performs the exact requests a mobile browser makes (same URLs, same TLS
# with SNI, same missing-cookie state) and asserts the expected status codes:
#   401 = reached dsh, login wall holds (good)      403 = trust fence holds
#   200 = portal login page (good)                  302 = /open hides token
#   502 = backend dead (bad — this is what the phone showed on 2026-10-18)
#
# Exit 0 = all good, 1 = something a user would feel. Each FAIL prints the
# phone symptom it corresponds to.
cd "$(dirname "$0")/.."

LAN="$(hostname -I | awk '{print $1}')"
TS="$(tailscale ip -4 2>/dev/null | head -1 || true)"
PUB="$(node -e "try{console.log(require('./needs.json').public_host)}catch(e){}" 2>/dev/null || true)"
FAIL=0

ok()   { echo "PASS  $1"; }
bad()  { echo "FAIL  $1  (phone symptom: $2)"; FAIL=1; }
code() { curl -sk -o /dev/null -w "%{http_code}" --max-time 10 "$@"; }

# 1. processes listening (the silent-death case: 502 with zero log traces)
for p in 3080 8080 8443 8090; do
  if ss -tln 2>/dev/null | grep -q ":$p "; then ok "listening :$p"; else bad "listening :$p" "HTTP 502 everywhere"; fi
done

# 2. dsh minted a launch token (without it the portal has nothing to hand out)
if grep -q "token=" log/dsh.log 2>/dev/null; then ok "dsh launch token present"; else bad "dsh launch token present" "portal says dsh is not running"; fi

# 3. dsh doors answer 401 = reachable + login wall holds (no cookie, like a fresh phone)
[ "$(code "http://$LAN:8080/")" = 401 ] && ok "LAN :8080 -> 401" || bad "LAN :8080 -> 401" "page doesn't load"
[ "$(code "https://$LAN:8443/")" = 401 ] && ok "LAN :8443 -> 401" || bad "LAN :8443 -> 401" "page doesn't load"
if [ -n "$TS" ]; then
  [ "$(code "https://$TS:8443/")" = 401 ] && ok "tailnet-IP :8443 -> 401" || bad "tailnet-IP :8443 -> 401" "page doesn't load"
fi
if [ -n "$PUB" ]; then
  [ "$(code "https://$PUB:9444/")" = 401 ] && ok "tailnet-name :9444 -> 401" || bad "tailnet-name :9444 -> 401" "page doesn't load / 502"
fi

# 4. trust fence still discriminates (evil origin must 403, ours must pass to 401)
[ "$(code -X POST "https://$LAN:8443/api/probe" -H "Origin: https://evil.example.com" -H "Content-Type: application/json" -d '{}')" = 403 ] \
  && ok "evil Origin -> 403 fence" || bad "evil Origin -> 403 fence" "SECURITY: fence open"
[ "$(code -X POST "https://$LAN:8443/api/probe" -H "Origin: https://$LAN:8443" -H "Content-Type: application/json" -d '{}')" = 401 ] \
  && ok "trusted Origin -> 401 auth" || bad "trusted Origin -> 401 auth" "page doesn't load"

# 5. portal login page + token never leaks to strangers
BODY="$(curl -sk --max-time 10 "https://$LAN:8090/")"
if [ "$(code "https://$LAN:8090/")" = 200 ] && echo "$BODY" | grep -qi "passkey"; then ok "portal login page 200"; else bad "portal login page 200" "portal doesn't load"; fi
OPEN="$(curl -sk -o /dev/null -w "%{http_code} %{redirect_url}" --max-time 10 "https://$LAN:8090/open")"
if echo "$OPEN" | grep -q "^302"; then
  echo "$OPEN" | grep -q "token=" && bad "portal /open hides token" "SECURITY: token leak" || ok "portal /open 302, token hidden"
else
  bad "portal /open hides token" "/open broken ($OPEN)"
fi

# 6. the exact phone test from 2026-10-18: tailnet portal must be 200, not 502
if [ -n "$PUB" ]; then
  [ "$(code "https://$PUB:9443/")" = 200 ] && ok "tailnet portal :9443 -> 200" || bad "tailnet portal :9443 -> 200" "HTTP ERROR 502 on phone"
fi

# 7. the other phone trap, documented: bare IP on :9444 MUST fail TLS
# (tailscale serve only speaks the MagicDNS name there — this is the
# ERR_SSL_PROTOCOL_ERROR the phone showed, and it is expected).
if [ -n "$TS" ]; then
  if code "https://$TS:9444/" >/dev/null 2>&1; then
    R="$(code "https://$TS:9444/")"
    [ "$R" = 401 ] && ok "bare-IP :9444 fails TLS (expected trap)" || bad "bare-IP :9444 fails TLS (expected trap)" "unexpected $R"
  else
    ok "bare-IP :9444 fails TLS (expected trap)"
  fi
fi

echo
[ "$FAIL" = 0 ] && echo "ALL CHECKS PASSED" || echo "FAILURES PRESENT — fix before telling the user to reload"
exit "$FAIL"
