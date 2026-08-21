#!/usr/bin/env python3
"""
fx -> opencode gateway translation proxy.

- Listens on http://127.0.0.1:8765 (or $FX_PROXY_PORT)
- Accepts fx's Vercel AI Gateway protocol:
    GET  /coding-agent/v1/models  -> returns model catalog containing OPENCODE_GO_MODEL
    GET  /coding-agent/v1/credits -> dummy balance
    POST /v3/ai/language-model    -> translates to OpenAI chat/completions at OPENCODE_GO_BASE_URL
- Forwards to OPENCODE_GO_BASE_URL (default https://opencode.ai/zen/go/v1/)
  using OPENCODE_GO_API_KEY / OPENCODE_API_KEY
- Translates OpenAI SSE stream back to Vercel gateway SSE (text-delta, tool-call, finish)

Usage:
  OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1/ OPENCODE_GO_API_KEY=sk-... python3 fx-opencode-proxy.py
  FX_GATEWAY_BASE_URL=http://127.0.0.1:8765 FX_GATEWAY_CHAT_URL=http://127.0.0.1:8765/v3/ai/language-model fx ask "hi"

Caveat: fx only trusts loopback http overrides (FX_GATEWAY_* checked by isLoopbackHttpUrl).
  This proxy is the bridge that lets an external https base URL be used via loopback.
"""
import os
import sys
import json
import urllib.request
import urllib.error
import http.server
import socketserver
import threading

PORT = int(os.getenv("FX_PROXY_PORT", "8765"))
OPENCODE_BASE = (os.getenv("OPENCODE_GO_BASE_URL") or "https://opencode.ai/zen/go/v1/").rstrip("/")
OPENCODE_KEY = os.getenv("OPENCODE_GO_API_KEY") or os.getenv("OPENCODE_API_KEY") or ""
OPENCODE_MODEL_ENV = os.getenv("OPENCODE_GO_MODEL") or ""

def log(msg):
    print(f"[fx-proxy] {msg}", file=sys.stderr, flush=True)

def strip_provider_prefix(model_id: str) -> str:
    # fx model ids are like "meta/muse-spark-1.2-contributor", "deepseek/deepseek-v4-flash"
    # opencode expects bare id like "muse-spark-1.2-contributor"
    if "/" in model_id:
        return model_id.split("/")[-1]
    return model_id

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        log(f"GET {self.path}")
        # Strip query
        path = self.path.split("?")[0]
        if "models" in path:
            self.handle_models()
        elif "credits" in path:
            self.handle_credits()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{}')

    def handle_models(self):
        # Try to fetch real models from opencode, else synth
        models = []
        try:
            headers = {"User-Agent": "fx/0.0.4", "Accept": "application/json"}
            if OPENCODE_KEY:
                headers["Authorization"] = f"Bearer {OPENCODE_KEY}"
            req = urllib.request.Request(
                f"{OPENCODE_BASE}/models",
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                for m in data.get("data", []):
                    mid = m.get("id")
                    if mid:
                        models.append(mid)
        except Exception as e:
            log(f"models fetch failed: {e}, using env model")
            if OPENCODE_MODEL_ENV:
                models = [OPENCODE_MODEL_ENV]
            else:
                models = ["muse-spark-1.2-contributor", "deepseek-v4-flash", "mimo-v2.5"]

        # Ensure env model is present
        if OPENCODE_MODEL_ENV and OPENCODE_MODEL_ENV not in models:
            models.insert(0, OPENCODE_MODEL_ENV)
        stripped_env = strip_provider_prefix(OPENCODE_MODEL_ENV) if OPENCODE_MODEL_ENV else None
        if stripped_env and stripped_env not in models:
            models.insert(0, stripped_env)

        # Build Vercel catalog-like response: fx expects {"models":[ {id, type, ...} ]}
        # We provide minimal fields; fx's model_catalog parser is tolerant
        catalog = []
        for mid in models:
            # Provide both bare and prefixed variants so fx /status and /models see matches
            catalog.append({
                "id": mid,
                "object": "model",
                "type": "language",
                "has_tool_use": True,
                "has_vision": False,
                "has_file_input": False,
                "context_window": 200000,
                "max_tokens": 32000,
            })
            # Also add prefixed form if not already prefixed
            if "/" not in mid:
                # guess prefix for known models
                prefix_map = {
                    "muse": "meta/muse-spark-1.2-contributor",
                    "muse-spark": "meta/muse-spark-1.2-contributor",
                    "deepseek": "deepseek/deepseek-v4-flash",
                    "mimo": "xiaomi/mimo-v2.5",
                    "glm": "zai/glm-5.2",
                }
                for k, v in prefix_map.items():
                    if mid.startswith(k):
                        if v not in models and v != mid:
                            catalog.append({"id": v, "object": "model", "type": "language", "has_tool_use": True, "context_window": 200000, "max_tokens": 32000})
                        break

        # Deduplicate by id
        seen = set()
        uniq = []
        for e in catalog:
            if e["id"] not in seen:
                seen.add(e["id"])
                uniq.append(e)

        body = json.dumps({"models": uniq}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_credits(self):
        body = json.dumps({"balance": "100", "credit_balance": "100"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        log(f"POST {self.path} len={self.headers.get('content-length')}")
        if not self.path.startswith("/v3/ai/language-model"):
            self.send_error(404, "not found")
            return
        length = int(self.headers.get("content-length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode())
        except Exception as e:
            log(f"invalid json: {e}")
            self.send_error(400, "invalid json")
            return

        # Extract gateway fields
        prompt = body.get("prompt", [])
        tools = body.get("tools", [])
        tool_choice = body.get("toolChoice", {})
        max_output = body.get("maxOutputTokens")
        # model comes from header ai-language-model-id, fallback to body? fx uses header
        model_header = self.headers.get("ai-language-model-id") or self.headers.get("Ai-Language-Model-Id") or OPENCODE_MODEL_ENV or "muse-spark-1.2-contributor"
        # Also body may contain model? gateway doesn't include model in JSON (it's header)
        model_for_opencode = strip_provider_prefix(model_header)
        log(f"gateway model header: {model_header} -> opencode model: {model_for_opencode}")

        # Translate prompt to OpenAI messages
        openai_messages = []
        # Filter out network_recovery system messages that confuse the model
        filtered_prompt = []
        for m in prompt:
            c = m.get("content") or ""
            if isinstance(c, str) and "<network_recovery>" in c:
                continue
            filtered_prompt.append(m)
        prompt = filtered_prompt
        for m in prompt:
            role = m.get("role")
            content = m.get("content")
            # tool_calls in assistant messages (handle snake and camel)
            tool_calls = m.get("tool_calls") or m.get("toolCalls") or m.get("tool_calls_json")
            if role == "assistant" and tool_calls:
                tc = []
                for c in tool_calls:
                    tc.append({
                        "id": c.get("id") or c.get("toolCallId") or f"call_{len(tc)}",
                        "type": "function",
                        "function": {"name": c.get("name") or c.get("toolName") or "unknown", "arguments": c.get("arguments_json") or c.get("arguments") or c.get("input") or "{}"}
                    })
                # Ensure arguments is string
                for entry in tc:
                    if not isinstance(entry["function"]["arguments"], str):
                        entry["function"]["arguments"] = json.dumps(entry["function"]["arguments"])
                openai_messages.append({"role": role, "content": content or "", "tool_calls": tc})
            elif role == "tool":
                # gateway tool result: content is often [{type:"tool-result", toolCallId, output:{value}}]
                # OpenAI expects role tool with tool_call_id and string content, but ONLY if preceding assistant had tool_calls.
                # If no preceding assistant tool_calls, convert to user message to avoid 400.
                has_prev_tool_call = openai_messages and openai_messages[-1].get("role") == "assistant" and openai_messages[-1].get("tool_calls")
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool-result":
                            tc_id = item.get("toolCallId") or item.get("tool_call_id") or m.get("tool_call_id") or m.get("toolCallId") or ""
                            out = item.get("output", {})
                            if isinstance(out, dict):
                                val = out.get("value") or out.get("text") or json.dumps(out)
                            else:
                                val = str(out)
                            if not val and isinstance(item.get("content"), str):
                                val = item["content"]
                            if has_prev_tool_call and tc_id:
                                openai_messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc_id,
                                    "content": val or ""
                                })
                            else:
                                # No preceding tool call – convert to user message with tool output
                                tool_name = item.get("toolName") or "tool"
                                openai_messages.append({
                                    "role": "user",
                                    "content": f"[Tool {tool_name} result]\n{val or ''}"
                                })
                        elif isinstance(item, dict) and "text" in item:
                            openai_messages.append({
                                "role": "user",
                                "content": item.get("text","")
                            })
                    continue
                tc_id = m.get("tool_call_id") or m.get("toolCallId") or ""
                if not tc_id and isinstance(content, dict):
                    tc_id = content.get("toolCallId") or content.get("tool_call_id") or ""
                if has_prev_tool_call and tc_id:
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": content if isinstance(content, str) else (json.dumps(content) if content else "")
                    })
                else:
                    # Convert orphan tool result to user
                    openai_messages.append({
                        "role": "user",
                        "content": f"[Tool result]\n{content if isinstance(content, str) else json.dumps(content)}"
                    })
            else:
                # system/user/assistant normal
                if content is not None:
                    # content may be string or maybe structured? keep as string
                    if isinstance(content, list):
                        # handle image arrays? simplify to text
                        text_parts = [p.get("text","") for p in content if isinstance(p, dict) and p.get("type")=="text"]
                        content = "\n".join(text_parts)
                    openai_messages.append({"role": role, "content": content})
                else:
                    # assistant with no content but maybe reasoning? skip
                    continue

        # Translate tools: gateway tools is JSON string? In body it's already parsed array? Check type
        # Tools forwarding is now enabled by default (fixed UA). Set FX_PROXY_DISABLE_TOOLS=1 to disable.
        enable_tools = os.getenv("FX_PROXY_DISABLE_TOOLS") != "1"
        openai_tools = None
        if enable_tools and isinstance(tools, list) and tools:
            if isinstance(tools, str):
                try:
                    tools = json.loads(tools)
                except:
                    tools = []
            openai_tools = []
            for t in tools:
                if "function" in t:
                    openai_tools.append(t)
                else:
                    name = t.get("name") or t.get("function", {}).get("name")
                    desc = t.get("description", "")
                    schema = t.get("inputSchema") or t.get("parameters") or t.get("input_schema") or {"type":"object","properties":{}}
                    if name:
                        openai_tools.append({
                            "type": "function",
                            "function": {"name": name, "description": desc, "parameters": schema}
                        })
            if not openai_tools:
                openai_tools = None

        # Build OpenAI payload
        oai_payload = {
            "model": model_for_opencode,
            "messages": openai_messages,
            "stream": True,
            "temperature": 0.7,
        }
        if openai_tools:
            oai_payload["tools"] = openai_tools
            # Map tool_choice
            tc_type = tool_choice.get("type") if isinstance(tool_choice, dict) else tool_choice
            if tc_type == "required":
                oai_payload["tool_choice"] = "required"
            elif tc_type == "auto":
                oai_payload["tool_choice"] = "auto"
            else:
                oai_payload["tool_choice"] = "auto"

        if max_output:
            try:
                oai_payload["max_tokens"] = int(max_output)
            except:
                pass

        log(f"forwarding to {OPENCODE_BASE}/chat/completions with {len(openai_messages)} messages, tools={bool(openai_tools)}")

        # Forward to opencode with streaming, translate back
        url = f"{OPENCODE_BASE}/chat/completions"
        headers = {"Content-Type": "application/json", "User-Agent": "fx/0.0.4", "Accept": "text/event-stream"}
        if OPENCODE_KEY:
            headers["Authorization"] = f"Bearer {OPENCODE_KEY}"

        data = json.dumps(oai_payload).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        # No content-length for SSE
        self.end_headers()

        finish_emitted = False
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                # resp is a stream of `data: {...}\n\n` lines
                # We need to translate each OpenAI chunk to gateway events
                # Buffer handling
                buf = b""
                tool_calls_buffer = {}  # index -> {id, name, args}
                pending_tool_ids = {}  # index -> id
                # For gateway we want to emit tool-input-start/delta/end then tool-call
                # We'll accumulate and emit incrementally
                def emit(obj):
                    nonlocal finish_emitted
                    if obj.get("type") == "finish":
                        finish_emitted = True
                    line = f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode()
                    self.wfile.write(line)
                    # Flush
                    try:
                        self.wfile.flush()
                    except:
                        pass

                # Also emit initial response-metadata
                # (optional but helps fx tracing)
                # Send nothing yet, wait for content

                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    buf += chunk
                    # Process lines
                    while b"\n\n" in buf or b"\n" in buf:
                        # Extract SSE lines
                        # OpenAI uses `data: {json}\n\n`
                        if b"\n\n" in buf:
                            block, buf = buf.split(b"\n\n", 1)
                        else:
                            # incomplete?
                            break
                        block = block.strip()
                        if not block:
                            continue
                        # block may contain multiple `data:` lines
                        lines = block.split(b"\n")
                        for line in lines:
                            line=line.strip()
                            if not line.startswith(b"data:"):
                                continue
                            payload_str = line[5:].strip().decode()
                            if payload_str == "[DONE]":
                                continue
                            try:
                                j = json.loads(payload_str)
                            except:
                                continue
                            choices = j.get("choices", [])
                            if not choices:
                                continue
                            choice = choices[0]
                            delta = choice.get("delta", {})
                            finish = choice.get("finish_reason")

                            # Content delta
                            if "content" in delta and delta["content"] is not None:
                                content_piece = delta["content"]
                                if content_piece:
                                    emit({"type": "text-delta", "delta": content_piece})

                            # Tool calls delta
                            if "tool_calls" in delta and delta["tool_calls"]:
                                for tc in delta["tool_calls"]:
                                    idx = tc.get("index", 0)
                                    if idx not in tool_calls_buffer:
                                        tool_calls_buffer[idx] = {"id": "", "name": "", "args": ""}
                                    buf_entry = tool_calls_buffer[idx]
                                    if "id" in tc and tc["id"]:
                                        buf_entry["id"] = tc["id"]
                                        # On first id seen, emit tool-input-start
                                        # need name may come later
                                    if "function" in tc:
                                        func = tc["function"]
                                        if "name" in func and func["name"]:
                                            buf_entry["name"] = func["name"]
                                            # Emit start if not yet emitted for this idx
                                            # Use a marker
                                            if not buf_entry.get("started"):
                                                emit({"type": "tool-input-start", "id": buf_entry["id"] or f"call_{idx}", "toolName": buf_entry["name"]})
                                                buf_entry["started"] = True
                                        if "arguments" in func and func["arguments"]:
                                            piece = func["arguments"]
                                            buf_entry["args"] += piece
                                            emit({"type": "tool-input-delta", "id": buf_entry["id"] or f"call_{idx}", "delta": piece})
                                    # Store
                                    if "id" in tc and tc["id"]:
                                        pending_tool_ids[idx] = tc["id"]

                            if finish:
                                # If tool calls pending, emit tool-input-end and tool-call
                                for idx, entry in tool_calls_buffer.items():
                                    if entry.get("started"):
                                        emit({"type": "tool-input-end", "id": entry["id"] or f"call_{idx}"})
                                        # Emit tool-call with final input as object if possible
                                        args_str = entry["args"]
                                        # Try to parse args as json, keep as object if valid else string
                                        try:
                                            args_obj = json.loads(args_str) if args_str else {}
                                        except:
                                            args_obj = args_str
                                        # gateway expects input as object or string; we'll send as object if json else stringify
                                        input_val = args_obj if isinstance(args_obj, (dict, list)) else args_str
                                        emit({
                                            "type": "tool-call",
                                            "toolCallId": entry["id"] or f"call_{idx}",
                                            "toolName": entry["name"],
                                            "input": input_val
                                        })
                                # Map finish reason
                                # openai: stop, length, tool_calls, content_filter
                                # gateway unified: stop, length, tool-calls, content-filter
                                unified = "stop"
                                if finish == "tool_calls":
                                    unified = "tool-calls"
                                elif finish == "length":
                                    unified = "length"
                                elif finish == "content_filter":
                                    unified = "content-filter"
                                emit({"type": "finish", "finishReason": {"unified": unified}})
                                # After finish, break outer loop? But we still need to send [DONE]
                                # We'll finish after loop

                # After stream ends, ensure finish if not already sent
                if not finish_emitted:
                    # No finish seen (opencode sometimes omits finish_reason for simple text) – synthesize stop
                    for idx, entry in tool_calls_buffer.items():
                        if entry.get("started"):
                            emit({"type": "tool-input-end", "id": entry["id"] or f"call_{idx}"})
                            args_str = entry["args"]
                            try:
                                args_obj = json.loads(args_str) if args_str else {}
                            except:
                                args_obj = args_str
                            input_val = args_obj if isinstance(args_obj, (dict, list)) else args_str
                            emit({
                                "type": "tool-call",
                                "toolCallId": entry["id"] or f"call_{idx}",
                                "toolName": entry["name"],
                                "input": input_val
                            })
                    # Determine unified: if we had tool calls but no finish, use tool-calls, else stop
                    unified = "tool-calls" if tool_calls_buffer else "stop"
                    emit({"type": "finish", "finishReason": {"unified": unified}})
                # We maintain a flag `finish_emitted` was handled above via emit wrapper
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:4000]
            log(f"upstream HTTPError {e.code}: {body}")
            # dump last payload for debug (first 8000 chars)
            try:
                with open("/tmp/fx_last_payload.json","w") as f:
                    json.dump(oai_payload, f, indent=2)
                log(f"dumped payload to /tmp/fx_last_payload.json ({len(json.dumps(oai_payload))} bytes)")
            except Exception as dump_e:
                log(f"dump failed: {dump_e}")
            err_obj = {"type": "error", "error": {"message": body[:800]}}
            self.wfile.write(f"data: {json.dumps(err_obj)}\n\n".encode())
            # Also emit finish with error?
            self.wfile.write(f"data: {json.dumps({'type':'finish','finishReason':{'unified':'error'}})}\n\n".encode())
        except Exception as e:
            log(f"proxy error: {e}")
            import traceback; traceback.print_exc()
            err_obj = {"type": "error", "error": {"message": str(e)[:500]}}
            try:
                self.wfile.write(f"data: {json.dumps(err_obj)}\n\n".encode())
            except:
                pass
        finally:
            try:
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except:
                pass

    def log_message(self, fmt, *args):
        # suppress default log, we use our log
        log(fmt % args)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def main():
    if not OPENCODE_KEY:
        log("WARNING: OPENCODE_GO_API_KEY/OPENCODE_API_KEY not set! Upstream will likely 401")
    log(f"OPENCODE_BASE={OPENCODE_BASE}")
    log(f"OPENCODE_MODEL_ENV={OPENCODE_MODEL_ENV}")
    log(f"listening on http://127.0.0.1:{PORT}")
    with ThreadedTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            log("shutting down")

if __name__ == "__main__":
    main()
