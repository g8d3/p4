python3 -c '
import re, os

zshrc = os.path.expanduser("~/.zshrc")
code = """
conn() {
  local H1="${1:?Suministra al menos un host}"
  local H2="${2:-$1}"
  local MOD="${3:-hibrido}"
  local H="$H1"

  while true; do
    local INICIO=$SECONDS
    echo "--- Conectando a $H (tmux: main) ---"
    
    ssh -o ConnectTimeout=4 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=2 -t "$H" "tmux new -A -s main"
    
    local DURACION=$(( SECONDS - INICIO ))
    echo -e "\nIntento finalizado en $H. Duración SSH: ${DURACION}s."
    
    [[ "$MOD" == "enter" ]] && read -r
    [[ "$MOD" == "tiempo" ]] && sleep 3
    [[ "$MOD" == "hibrido" ]] && read -r -k 1 -t 3
    
    [[ "$H" == "$H1" ]] && H="$H2" || H="$H1"
  done
}"""

content = open(zshrc).read() if os.path.exists(zshrc) else ""
pattern = r"\n?conn\(\) \{.*?\n\}"

if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, code, content, flags=re.DOTALL)
else:
    content += "\n" + code + "\n"

open(zshrc, "w").write(content)
' && source ~/.zshrc

