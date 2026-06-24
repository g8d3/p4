#!/bin/bash
# Demo script v3 — spinner during API calls, better formatting.
# Executes REAL Xiaomi API commands. Records timing for audio post-production.

BASE="/home/vuos/code/p4/e010-more-videos/ag-03"
XIAOMI_API="/home/vuos/code/p4/e009-xiaomi-display/ag-01/bin/xiaomi-api"
TTS_OUT="$BASE/assets/tts_demo_final.wav"
EVENTS="$BASE/assets/timing.events"

C_GRN='\033[0;32m'; C_YEL='\033[0;33m'; C_BLU='\033[0;34m'; C_CYN='\033[0;36m'; C_MGT='\033[0;35m'
B='\033[1m'; D='\033[2m'; N='\033[0m'

> "$EVENTS"
mark() { echo "$(date +%s.%N) $1" >> "$EVENTS"; }

type_slow() {
    local text="$1" delay="${2:-0.015}"
    local i
    for ((i=0; i<${#text}; i++)); do
        printf '%s' "${text:$i:1}"
        sleep "$delay"
    done
}

spinner() {
    local pid=$1 msg="$2"
    local spin='-\|/' i=0
    while kill -0 "$pid" 2>/dev/null; do
        echo -ne "\r${C_BLU}${B}>>> ${msg} [${spin:$((i%4)):1}]${N}"
        ((i++))
        sleep 0.15
    done
    echo -ne "\r${C_BLU}${B}>>> ${msg} [done]${N}        \n"
}

clear

mark intro_start
echo -e "${C_CYN}${B}======================================${N}"
echo -e "${C_CYN}${B}   Xiaomi MIMO - TTS + ASR Demo${N}"
echo -e "${C_CYN}${B}======================================${N}"
echo ""
echo -e "  ${C_MGT}TTS${N}  Text  ${C_YEL}->${N}  AI Voice"
echo -e "  ${C_MGT}ASR${N}  Voice ${C_YEL}->${N}  Text"
echo ""
echo -e "${D}API: token-plan-sgp.xiaomimimo.com${N}"
echo -e "${D}Models: mimo-v2.5-tts / mimo-v2.5-asr${N}"
sleep 6

echo ""
echo -e "${C_YEL}${B}=== [1] Text to Speech ===${N}"
echo ""
sleep 1

# Show the text that will be converted
echo -e "${D}Input text:${N}"
echo -e "  ${C_CYN}\"Hola, soy Salome. Esta voz fue\"${N}"
echo -e "  ${C_CYN}generada con la API de Xiaomi MIMO.\"${N}"
echo ""

# Type TTS command
type_slow "${D}\$ ${N}${C_GRN}xiaomi-api tts \\\\${N}\n" 0.015
sleep 0.2
type_slow "${C_GRN}    --voice Mia --format wav \\\\${N}\n" 0.015
sleep 0.2
type_slow "${C_GRN}    -o tts_demo.wav${N}\n" 0.015
sleep 1
mark tts_cmd_done

echo ""
# Run API call with spinner
python3 "$XIAOMI_API" tts \
    --text "Hola, soy Salome. Esta voz fue generada con la API de Xiaomi MIMO. La inteligencia artificial puede crear audio realista desde texto." \
    --voice Mia --format wav -o "$TTS_OUT" >/dev/null 2>&1 &
API_PID=$!
mark tts_exec_start
spinner $API_PID "Calling TTS API"
wait $API_PID
mark tts_exec_done

echo ""
TTS_SIZE=$(stat -c%s "$TTS_OUT")
TTS_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TTS_OUT" 2>/dev/null)
echo -e "${C_GRN}${B}OK${N} Audio generated: tts_demo.wav"
echo -e "   ${D}Size: $(echo "scale=0; $TTS_SIZE/1024" | bc) KB | Duration: ${TTS_DUR}s${N}"
sleep 2

echo ""
echo -e "${C_CYN}${B}=== Playing TTS Audio ===${N}"
echo -e "${D}   (Narration paused - listen)${N}"
echo ""
mark tts_play_start

# Visual progress bar during TTS playback
TTS_INT=${TTS_DUR%.*}
[ "$TTS_INT" -lt 1 ] && TTS_INT=1
for i in $(seq 1 "$TTS_INT"); do
    FILL=$(printf '#%.0s' $(seq 1 $((i * 3))))
    SPACES=$(printf ' %.0s' $(seq 1 $(((TTS_INT - i) * 3))))
    echo -ne "\r${C_GRN}>>> [${FILL}${SPACES}] ${i}s/${TTS_INT}s${N}  "
    sleep 1
done
echo ""
mark tts_play_end

echo ""
echo -e "${C_GRN}${B}>>> TTS playback complete${N}"
sleep 2

echo ""
echo -e "${C_YEL}${B}=== [2] Speech to Text (ASR) ===${N}"
echo ""
sleep 1

type_slow "${D}\$ ${N}${C_GRN}xiaomi-api asr --audio tts_demo.wav${N}\n" 0.015
sleep 1
mark asr_cmd_done

echo ""
# Run ASR call with spinner
ASR_RESULT_FILE="$BASE/assets/asr_result.txt"
python3 "$XIAOMI_API" asr --audio "$TTS_OUT" -o "$ASR_RESULT_FILE" >/dev/null 2>&1 &
API_PID=$!
mark asr_exec_start
spinner $API_PID "Calling ASR API"
wait $API_PID
mark asr_exec_done

ASR_RESULT=$(cat "$ASR_RESULT_FILE" 2>/dev/null)
echo ""
echo -e "${C_YEL}${B}Transcription:${N}"
echo ""
echo -e "  ${B}${C_GRN}\"${ASR_RESULT}\"${N}"
echo ""
sleep 3

mark outro_start
echo ""
echo -e "${C_GRN}${B}======================================${N}"
echo -e "${C_GRN}${B}   Pipeline Complete!${N}"
echo -e "${C_GRN}${B}======================================${N}"
echo ""
echo -e "  ${C_MGT}TTS${N}: text  ${C_YEL}->${N} AI voice  ${D}(mimo-v2.5-tts)${N}"
echo -e "  ${C_MGT}ASR${N}: voice ${C_YEL}->${N} text      ${D}(mimo-v2.5-asr)${N}"
echo ""
echo -e "${D}token-plan-sgp.xiaomimimo.com${N}"
mark demo_end

sleep 5
