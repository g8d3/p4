#!/usr/bin/env python3
"""HTTP transcription server — delegates to model_worker via Unix socket."""
import time, json, os, socket, csv, subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

WORKER_SOCKET = '/tmp/transcribe-worker.sock'
LOG = Path(__file__).parent.parent / 'output' / 'transcribe_log.csv'
HOST, PORT = '127.0.0.1', 9877

def worker_request(audio_path):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(120)
    sock.connect(WORKER_SOCKET)
    sock.sendall(json.dumps({'path': str(audio_path)}).encode())
    sock.shutdown(socket.SHUT_WR)
    data = b''
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        data += chunk
    sock.close()
    return json.loads(data)

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode()
        try:
            path = json.loads(body)['path']
        except Exception:
            self.send_error(400, 'JSON with "path" field required')
            return
        if not os.path.exists(path):
            self.send_error(404, f'File not found: {path}')
            return

        t0 = time.time()
        result = worker_request(path)
        elapsed = time.time() - t0

        if 'error' in result:
            self.send_error(500, result['error'])
            return

        r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_entries', 'format=duration', path], capture_output=True, text=True)
        audio_sec = round(float(json.loads(r.stdout)['format']['duration']), 1)
        result['audio_sec'] = audio_sec

        LOG.parent.mkdir(parents=True, exist_ok=True)
        if not LOG.exists():
            with open(LOG, 'w', newline='') as f:
                csv.writer(f).writerow(['file','audio_sec','transcribe_sec','words','segments'])
        with open(LOG, 'a', newline='') as f:
            csv.writer(f).writerow([path, audio_sec, result['transcribe_sec'],
                result['words'], result['segments']])

        srt_path = Path(path).with_suffix('.srt')
        srt_path.write_text(result['srt'])
        txt_path = Path(path).with_suffix('.txt')
        txt_path.write_text(result['text'])

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        resp = json.dumps(result, indent=2)
        self.wfile.write(resp.encode())
        fname = Path(path).name
        ratio = f'{audio_sec/result["transcribe_sec"]:.1f}x' if result['transcribe_sec'] else '?'
        print(f'  {fname}: {result["transcribe_sec"]}s ({ratio})', flush=True)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/log':
            if not LOG.exists():
                self.send_error(404, 'No log yet')
                return
            lines = LOG.read_text().strip().split('\n')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write('\n'.join(lines[-10:]).encode())
        elif path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            ok = os.path.exists(WORKER_SOCKET)
            self.wfile.write(json.dumps({'status': 'ok' if ok else 'no_worker',
                'worker_socket': str(WORKER_SOCKET), 'socket_exists': ok}).encode())
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer((HOST, PORT), Handler)
    print(f'Server on http://{HOST}:{PORT}', flush=True)
    print(f'Worker socket: {WORKER_SOCKET}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
