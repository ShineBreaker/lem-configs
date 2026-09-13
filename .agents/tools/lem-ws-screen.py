#!/usr/bin/env python3
"""从 lem-ws-dump 重建屏幕文本：按 view 分组 put 文本。"""
import json, sys
from collections import defaultdict

f = sys.argv[1]
views = {}          # id -> view meta (含 x,y,w,h)
screens = {}        # id -> {(row,col): char}
login_views = None

def apply(arg, method):
    vid = arg.get("id") or arg.get("viewId") or arg.get("view", {}).get("id") if isinstance(arg, dict) else None
    if method == "make-view" and isinstance(arg, dict):
        # 可能直接是 view 对象
        vid = arg.get("id")
        views[vid] = {"x": arg.get("x"), "y": arg.get("y"), "w": arg.get("width"),
                      "h": arg.get("height"), "kind": arg.get("kind")}
        screens.setdefault(vid, {})
    elif method == "delete-view":
        views.pop(arg.get("id"), None); screens.pop(arg.get("id"), None)
    elif method == "put":
        vinfo = arg.get("viewInfo") or {}
        vid = vinfo.get("id", arg.get("id"))
        x, y = arg.get("x"), arg.get("y")
        txt = arg.get("text") or arg.get("char") or ""
        scr = screens.setdefault(vid, {})
        if isinstance(x, int) and isinstance(y, int):
            scr[(y, x)] = str(txt)
    elif method == "clear-eol":
        vinfo = arg.get("viewInfo") or {}
        vid = vinfo.get("id", arg.get("id")); y, x = arg.get("y"), arg.get("x")
        scr = screens.get(vid)
        if scr is not None and isinstance(y, int):
            for (yy, xx) in list(scr):
                if yy == y and xx >= (x or 0): del scr[(yy, xx)]

for line in open(f):
    line = line.strip()
    if not line.startswith("RECV "): continue
    try: msg = json.loads(line[5:])
    except Exception: continue
    if "method" not in msg:
        res = msg.get("result") or {}
        if "views" in res: login_views = res["views"]
        continue
    m, arg = msg["method"], msg.get("params")
    if m == "bulk":
        items = arg if isinstance(arg, list) else []
        for it in items:
            apply(it.get("argument", {}), it.get("method"))
    else:
        apply(arg, m)

# login views（静态快照）优先
if login_views:
    for v in login_views:
        if isinstance(v, dict) and v.get("id") not in views:
            views[v["id"]] = {"x": v.get("x"), "y": v.get("y"), "w": v.get("width"),
                              "h": v.get("height"), "kind": v.get("kind")}

print(f"views: {len(views)}")
for vid, v in sorted(views.items(), key=lambda kv: (kv[1].get('y') or 0, kv[1].get('x') or 0)):
    scr = screens.get(vid, {})
    if not v.get("w"): continue
    print(f"\n===== view {vid} kind={v.get('kind')} pos=({v.get('x')},{v.get('y')}) size={v.get('w')}x{v.get('h')} chars={len(scr)} =====")
    if scr:
        rows = defaultdict(dict)
        for (y, x), ch in scr.items(): rows[y][x] = ch
        for y in sorted(rows)[:40]:
            line_txt = "".join(rows[y].get(x, " ") for x in range(min(rows[y]), max(rows[y])+1))
            print(f"{y:3d}|{line_txt.rstrip()}")
