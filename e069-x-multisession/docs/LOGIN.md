# X login runbook (user-assisted, no secrets in repo)

Login happens ONCE per account inside its own persistent profile.
The agent never sees or stores your password.

## Option A — password login (recommended for throwaway/test accounts)
1. Agent launches the account session (`chrome` backend, headed if you want to watch).
2. You type (or paste) username + password YOURSELF in that window.
   Agent looks away — it only checks `login_status` afterwards via snapshot.
3. If X shows a challenge/captcha: STOP. Do not grind it. Mark account `blocked`, retry later.

## Option B — Google auth (recommended for your real account)
1. Agent launches the account session with its persistent profile.
2. On x.com login page you click "Continue with Google" and complete
   Google's flow yourself (2FA stays yours).
3. Agent verifies via snapshot that your handle appears, marks `ok`.

## Rules (from e020 findings — hard)
- One profile per account, forever. Never copy cookies into another
  backend/profile — fingerprint mismatch reads as session theft.
- Passwords/OTP codes: transient only, never written to disk or git.
- `profiles/` and `data/` are git-ignored. Only `accounts.json`
  (id/handle/backend) is safe to keep.
- Challenge hit = stop + report. Never auto-retry logins in a loop.
