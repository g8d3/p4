#!/bin/bash
# Detached capture launcher: runs the capture script in its own session.
setsid /home/vuos/code/p4/e023-build-in-public/ag-01/bin/ep1_capture.sh \
  > /tmp/opencode/capture-launch.log 2>&1 < /dev/null &
echo "detached capture launched pid=$!"
