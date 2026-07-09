import json, os, base64, subprocess, sys

audio_path = '/home/vuos/code/p4/e015-video-pipeline/ag-02-pipeline/agent-005/audio.mp3'

with open(audio_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

payload = {
    'model': 'mimo-v2.5-asr',
    'messages': [{'role': 'user', 'content': [
        {'type': 'input_audio', 'input_audio': {
            'data': 'data:audio/mp3;base64,' + b64,
            'format': 'mp3'
        }}
    ]}]
}

# Source the env file and extract vars
env_output = subprocess.run(
    'bash -c "source ~/.secrets/.env && echo \$XIAOMI_BASE_URL && echo \$XIAOMI_API_KEY"',
    shell=True, capture_output=True, text=True
)
lines = env_output.stdout.strip().split('\n')
url = lines[0]
key = lines[1]

cmd = [
    'curl', '-s', '-k', f'{url}/chat/completions',
    '-H', f'Authorization: Bearer {key}',
    '-H', 'Content-Type: application/json',
    '-d', json.dumps(payload)
]
result = subprocess.run(cmd, capture_output=True, text=True)
data = json.loads(result.stdout)
print(data['choices'][0]['message']['content'])
