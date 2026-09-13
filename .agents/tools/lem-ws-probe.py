#!/usr/bin/env python3
"""lem-server WebSocket 探针：login → 注入按键 → 收集绘制通知流。

用法: lem-ws-probe.py PORT OUTFILE "KEY1;KEY2;..."
按键格式: C-g / M-x / Right / x / C-x（分号分隔）
"""
import json, sys, time
import websocket

PORT = sys.argv[1]
OUT = sys.argv[2]
keys = [k for k in (sys.argv[3] if len(sys.argv) > 3 else "").split(";") if k]
COLLECT_SECS = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0

ws = websocket.create_connection(f"ws://127.0.0.1:{PORT}", timeout=10)

def send_key(seq):
    if seq.startswith("s:"):  # input-string 形式
        ws.send(json.dumps({"jsonrpc": "2.0", "id": 100, "method": "input",
                            "params": {"kind": "input-string", "value": seq[2:]}}))
        return
    # 上游 key 规范名（src/key.lisp *key-names*）与浏览器 key 名的差异
    seq = {"Enter": "Return", "Esc": "Escape"}.get(seq, seq)
    ctrl = meta = shift = super_ = False
    name = seq
    while True:
        if seq.startswith("C-"):
            ctrl = True; seq = seq[2:]
        elif seq.startswith("M-"):
            meta = True; seq = seq[2:]
        elif seq.startswith("S-"):
            shift = True; seq = seq[2:]
        elif seq.startswith("sM-"):
            super_ = True; seq = seq[3:]
        else:
            name = seq; break
    value = {"key": name, "ctrl": ctrl, "meta": meta,
             "shift": shift, "super": super_}
    ws.send(json.dumps({"jsonrpc": "2.0", "id": 100, "method": "input",
                        "params": {"kind": "key", "value": value}}))

out = open(OUT, "w")
# login（响应里带初始 views；size 用字符网格——原生 webview JS 传的就是
# 字符数，传像素会让 display-width 失真、面板列数计算翻倍）
ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "login",
                    "params": {"size": {"width": 151, "height": 43}}}))
deadline = time.time() + 2
ws.settimeout(0.4)
while time.time() < deadline:
    try:
        out.write("RECV " + ws.recv() + "\n")
    except websocket.WebSocketTimeoutException:
        break

for k in keys:
    send_key(k)
    time.sleep(0.35)

# 收集绘制流
deadline = time.time() + COLLECT_SECS
n = 0
while time.time() < deadline:
    try:
        out.write("RECV " + ws.recv() + "\n"); n += 1
    except websocket.WebSocketTimeoutException:
        continue
    except Exception as e:
        out.write(f"ERR {e}\n"); break
out.write(f"TOTAL {n}\n")
out.close()
ws.close()
print(f"collected {n} messages -> {OUT}")
