# Autopsy c010 (voided, no version)
- Symptom: 30+ min running, zero output, zero CPU on pi child (1176153, Sl, TIME 00:00:00).
- False positive: `pgrep -f "pi --print"` matched the probing shell's own cmdline twice ("pi alive" was a lie). Use `pgrep -f "pi --prin[t]"` + check child CPU TIME.
- Chain parent (1176138) blocked in `pi --print` wait the whole time; cron ticks correctly exited lane-busy.
- Fix shipped: /api/cycle/void (no version bump, marks goal done); legs stream stdout+status from leg 1 so silence is visible, not inferred.
