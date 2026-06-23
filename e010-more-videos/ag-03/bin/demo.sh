#!/bin/bash
# Demo script — runs inside foot terminal on Sway headless display.
# Executes REAL Xiaomi API commands. Records timing for audio post-production.

BASE="/home/vuos/code/p4/e010-more-videos/ag-03"
XIAOMI_API="/home/vuos/code/p4/e009-xiaomi-display/ag-01/bin/xiaomi-api"
TTS_OUT="$BASE/assets/tts_demo_final.wav"
EVENTS="$BASE/assets/timing.events"

C_GRN='\033[0;32m'; C_YEL='\033[0;33m'; C_BLU='\033[0;34m'; C_CYN='\033[0;36m'
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

clear

mark intro_start
echo -e "${C_CYN}${B}======================================${N}"
echo -e "${C_CYN}${B}   Xiaomi MIMO - TTS + ASR Demo${N}"
echo -e "${C_CYN}${B}======================================${N}"
echo ""
echo -e "${D}API: token-plan-sgp.xiaomimimo.com${N}"
echo -e "${D}Models: mimo-v2.5-tts / mimo-v2.5-asr${N}"
sleep 6

echo ""
echo -e "${C_YEL}${B}[1] Text to Speech${N}"
echo ""
sleep 1

# Type TTS command line by line
type_slow "${D}\$ ${N}${C_GRN}xiaomi-api tts \\\\${N}\n" 0.015
sleep 0.3
type_slow "${C_GRN}    --text \"Hola, soy Salome. \\\\${N}\n" 0.015
sleep 0.2
type_slow "${C_GRN}      Voz generada con IA\" \\\\${N}\n" 0.015
sleep 0.2
type_slow "${C_GRN}    --voice Mia \\\\${N}\n" 0.015
sleep 0.2
type_slow "${C_GRN}    --format wav \\\\${N}\n" 0.015
sleep 0.2
type_slow "${C_GRN}    -o tts_demo.wav${N}\n" 0.015
sleep 1
mark tts_cmd_done

echo ""
echo -e "${C_BLU}${B}>>> Calling Xiaomi API...${N}"
sleep 1
mark tts_exec_start

# Real API call
python3 "$XIAOMI_API" tts \
    --text "Hola, soy Salome. Esta voz fue generada con la API de Xiaomi MIMO. La inteligencia artificial puede crear audio realista desde texto." \
    --voice Mia --format wav -o "$TTS_OUT" 2>&1
mark tts_exec_done

echo ""
TTS_SIZE=$(stat -c%s "$TTS_OUT")
TTS_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TTS_OUT" 2>/dev/null)
echo -e "${C_YEL}Output: tts_demo.wav${N}"
echo -e "${D}Size: ${TTS_SIZE} bytes | Duration: ${TTS_DUR}s${N}"
sleep 2

echo ""
echo -e "${C_CYN}${B}======================================${N}"
echo -e "${C_CYN}${B}   Playing TTS Audio Output${N}"
echo -e "${C_CYN}${B}======================================${N}"
echo -e "${D}   (Narration paused - listen)${N}"
echo ""
mark tts_play_start

# Visual progress bar during TTS playback duration
TTS_INT=${TTS_DUR%.*}
[ "$TTS_INT" -lt 1 ] && TTS_INT=1
for i in $(seq 1 "$TTS_INT"); do
    FILL=$(printf '#%.0s' $(seq 1 $((i * 3))))
    SPACES=$(printf ' %.0s' $(seq 1 $(((TTS_INT - i) * 3))))
    echo -ne "\r${C_GRN}>>> [${FILL}${SPACES}] ${i}s/${TTS_INT}s${N}"
    sleep 1
done
echo ""
mark tts_play_end

echo ""
echo -e "${C_GRN}${B}>>> TTS playback complete${N}"
sleep 2

echo ""
echo -e "${C_YEL}${B}[2] Speech to Text (ASR)${N}"
echo ""
sleep 1

type_slow "${D}\$ ${N}${C_GRN}xiaomi-api asr \\\\${N}\n" 0.015
sleep 0.3
type_slow "${C_GRN}    --audio tts_demo.wav${N}\n" 0.015
sleep 1
mark asr_cmd_done

echo ""
echo -e "${C_BLU}${B}>>> Calling Xiaomi API for ASR...${N}"
echo -e "${D}    Processing audio...${N}"
sleep 1
mark asr_exec_start

# Real API call
ASR_RESULT=$(python3 "$XIAOMI_API" asr --audio "$TTS_OUT" 2>/dev/null)
mark asr_exec_done

echo ""
echo -e "${C_YEL}${B}Transcription result:${N}"
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
echo -e "  ${C_CYN}TTS${N}: text  -> AI voice  (mimo-v2.5-tts)"
echo -e "  ${C_CYN}ASR${N}: audio -> text      (mimo-v2.5-asr)"
echo ""
echo -e "${D}token-plan-sgp.xiaomimimo.com${N}"
mark demo_end

sleep 5
