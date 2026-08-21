# X thread — 2 tweets for opencode users who tried fx (each <140)

1/2 Have $10 opencode and tried fx? fx ignores `BASE_URL` to opencode. Fix: `bash e035-fx-opencode-bridge/bin/install.sh`

2/2 Now `fx` uses your opencode model (`fx status` proves it). Undo: `bash install.sh unpatch`. Bridge until fx is native.
