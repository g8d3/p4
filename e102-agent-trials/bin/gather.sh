#!/bin/bash
# Gather facts for Mango Z's daily report. All times come from command output.
set -u
P=~/code/p4; INBOX=$P/e092-echolike/correo/inbox; ST=$P/e102-agent-trials/daily/.last_run
echo "## Facts gathered $(TZ=America/Bogota date '+%Y-%m-%d %H:%M %Z (Bogota)')"
echo; echo "### Health"
for h in /sys/class/hwmon/hwmon*; do [ -r $h/temp1_input ] && echo "- temp $(cat $h/name): $(( $(cat $h/temp1_input)/1000 ))°C"; done
SSID=$(nmcli -t -f active,ssid dev wifi 2>/dev/null | awk -F: '$1=="yes"{print $2}' | head -1)
echo "- wifi SSID: ${SSID:-none} ($([ "$SSID" = sc-00b8-5G ] && echo OK || echo 'PROBLEM: expected sc-00b8-5G'))"
curl -s -m 10 -o /dev/null -w '%{http_code}' https://1.1.1.1 >/dev/null 2>&1 && echo "- internet: OK" || echo "- internet: PROBLEM (no response from 1.1.1.1)"
df -h / | awk 'NR==2{print "- disk /: "$3" used of "$2" ("$5"), "$4" free"}'
echo "- uptime: $(uptime -p)"
echo; echo "### Services (expected running: correo-receptor, e101-hummingbot container, e101-liquidity-publish.timer, OpenBot, PI WEB)"
for u in correo-receptor.service e101-liquidity-publish.timer pi-web.service pi-web-sessiond.service; do echo "- $u: $(systemctl --user is-active $u)"; done
pgrep -f OpenBot-x86_64.AppImage >/dev/null && echo "- OpenBot: running" || echo "- OpenBot: NOT running"
echo "- docker running: $(docker ps --format '{{.Names}}' | paste -sd, -)"
docker ps --format '{{.Names}}' | grep -vx e101-hummingbot | sed 's/^/- UNEXPECTED container running: /'
docker ps --format '{{.Names}}' | grep -qx e101-hummingbot || echo "- PROBLEM: e101-hummingbot not running"
BASE='^(at-spi-dbus-bus|dbus|dconf|filter-chain|gnome-keyring-daemon|gpg-agent|gvfs-.*|pipewire.*|wireplumber|xdg-.*|correo-receptor|pi-web|pi-web-sessiond|e102-daily-report)\.service$'
systemctl --user list-units --type=service --state=running --no-legend --plain | awk '{print $1}' | grep -Ev "$BASE" | sed 's/^/- UNEXPECTED user service running: /'
systemctl --user list-timers --no-legend --plain | awk '{for(i=1;i<=NF;i++) if($i ~ /\.timer$/) print $i}' | grep -Ev '^(e101-liquidity-publish|e102-daily-report|launchpadlib-cache-clean|snap\..*)\.timer$' | sed 's/^/- UNEXPECTED user timer active: /'
echo; echo "### New emails since last run ($( [ -f $ST ] && TZ=America/Bogota date -r $ST '+%Y-%m-%d %H:%M Bogota' || echo 'first run: last 24h'))"
if [ -f $ST ]; then F=$(find $INBOX -type f -name '*.json' -newer $ST | sort); else F=$(find $INBOX -type f -name '*.json' -mmin -1440 | sort); fi
[ -z "$F" ] && echo "(none)"
for f in $F; do echo; echo "#### $(basename $f) (received $(TZ=America/Bogota date -r $f '+%Y-%m-%d %H:%M Bogota'))"; python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print("From:",d.get("from"));print("To:",d.get("to"));print("Subject:",d.get("subject"));print();print((d.get("text") or "")[:3000])' "$f"; done
