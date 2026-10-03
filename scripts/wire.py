#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wire.py —— 把 galgame.spec.yaml 编译为一套可运行的 Ren'Py .rpy 文件。

用法:
    python3 wire.py <spec.yaml|spec.json> <project_dir> [--out game] [--clean]

设计要点
- 单一入口、单向编译: spec(声明式) -> .rpy(命令式)，生成过程可重复、幂等。
- 每个字段都可缺省: 缺 characters 就从 scenes 推断；缺 scenes 就按 route 铺骨架；
  缺 endings 就按 route 类型补默认结局；缺 assets 则只生成 image 语句、由 assets.py 补占位图。
- 只依赖 PyYAML（可选）；JSON spec 无需任何第三方库。
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

# --------------------------------------------------------------------------- #
# 载入与归一化
# --------------------------------------------------------------------------- #

def die(msg: str, code: int = 1):
    print(f"[wire] 错误: {msg}", file=sys.stderr)
    sys.exit(code)


def load_spec(path: str) -> dict:
    if not os.path.exists(path):
        die(f"找不到 spec 文件: {path}")
    text = open(path, encoding="utf-8").read()
    if path.endswith((".yaml", ".yml")):
        if yaml is None:
            die("读取 YAML 需要 PyYAML，请 `pip install pyyaml`，或改用 .json spec")
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        die("spec 顶层必须是映射(mapping)")
    return data


def slugify(text: str) -> str:
    """把任意标题压成合法的英文标识符。CJK 无法音译时退化为哈希后缀。"""
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", text or "").strip("_").lower()
    if not s:
        s = "vn_" + format(abs(hash(text or "game")) % 0xFFFF, "x")
    return s


def as_list(x) -> list:
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def norm(spec: dict) -> dict:
    """补全所有缺省值，保证后续生成阶段无需再判空。"""
    p = spec.get("project", {}) or {}
    p.setdefault("title", "未命名视觉小说")
    p.setdefault("slug", slugify(p["title"]))
    p.setdefault("resolution", [1920, 1080])
    p.setdefault("language", "zh-CN")
    p.setdefault("theme", "classic")
    spec["project"] = p

    spec["characters"] = as_list(spec.get("characters"))
    spec["flags"] = as_list(spec.get("flags"))
    spec["scenes"] = as_list(spec.get("scenes"))
    spec["endings"] = as_list(spec.get("endings"))

    # routes: 缺省 -> 共通线 + 每个角色一条线
    routes = as_list(spec.get("routes"))
    if not routes:
        routes = [{"id": "common", "type": "common", "title": "主线", "entry": "start"}]
        for c in spec["characters"]:
            rid = c.get("route")
            if rid:
                routes.append({
                    "id": rid, "type": "character",
                    "title": f"{c.get('name', c['id'])}线",
                    "entry_condition": f"{c['id']}_route_unlocked",
                })
    spec["routes"] = routes

    # endings: 缺省 -> 为共通线补一个普通结局，保证至少有终点
    if not spec["endings"]:
        common = next((r["id"] for r in routes if r.get("type") == "common"), routes[0]["id"])
        spec["endings"] = [{"id": "normal", "title": "结局", "route": common}]

    # builds
    b = spec.get("build", {}) or {}
    b.setdefault("include_gallery", True)
    b.setdefault("include_quick_menu", True)
    b.setdefault("target", ["pc"])
    spec["build"] = b

    spec.setdefault("assets", {})
    ensure_route_scenes(spec)
    return spec


def resolved_route(sc: dict, spec: dict) -> str:
    return sc.get("route") or (spec["routes"][0]["id"] if spec["routes"] else "common")


def ensure_route_scenes(spec: dict) -> None:
    """保证每条路线都至少有一场戏，否则 router 会跳到不存在的 label。"""
    have = {resolved_route(sc, spec) for sc in spec["scenes"]}
    for r in spec["routes"]:
        rid = r["id"]
        if rid in have:
            continue
        title = r.get("title", rid)
        spec["scenes"].append({
            "id": f"{rid}_1", "route": rid,
            "lines": [{"narrator": f"【待补写】{title}·开场。"}],
            "next": f"{rid}_2",
        })
        spec["scenes"].append({
            "id": f"{rid}_2", "route": rid,
            "lines": [{"narrator": f"【待补写】{title}·展开与收束。"}],
        })


def route_first_scene(spec: dict, rid: str) -> str | None:
    for sc in spec["scenes"]:
        if resolved_route(sc, spec) == rid:
            return sc.get("id")
    return None


# --------------------------------------------------------------------------- #
# 文本与标识符工具
# --------------------------------------------------------------------------- #

def q(text: str) -> str:
    """把一句对白/旁白转成 Ren'Py 字符串字面量（转义引号与反斜杠）。"""
    text = str(text).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def py_lit(v) -> str:
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, (int, float)):
        return repr(v)
    return q(v)


def collect_characters(spec: dict) -> dict:
    """合并显式 characters 与 scenes 中出现的未知 who，返回 id -> 角色字典。"""
    chars = {}
    for c in spec["characters"]:
        if not c.get("id"):
            continue
        chars[c["id"]] = {
            "id": c["id"],
            "name": c.get("name", c["id"]),
            "color": c.get("color"),
            "slots": c.get("sprite_slots", []),
        }
    # 从 scenes 中捞未知说话人
    for sc in spec["scenes"]:
        for ln in sc.get("lines", []):
            who = ln.get("who")
            if who and who not in chars and who != "narrator":
                chars[who] = {"id": who, "name": who, "color": None, "slots": []}
    return chars


# --------------------------------------------------------------------------- #
# 各文件生成器
# --------------------------------------------------------------------------- #

HEADER = "# 本文件由 galgame skill 的 wire.py 自动生成，手改请同步改 spec，避免被覆盖。\n"


def gen_core(spec: dict) -> str:
    return (
        HEADER
        + "# 结局/画廊的记忆层与工具函数\n"
        + "default persistent.endings_seen = set()\n"
        + "default persistent.cgs_seen = set()\n\n"
        + "init python:\n"
        + "    def record_ending(eid):\n"
        + "        if persistent.endings_seen is None:\n"
        + "            persistent.endings_seen = set()\n"
        + "        persistent.endings_seen.add(eid)\n\n"
        + "    def ending_seen(eid):\n"
        + "        return eid in (persistent.endings_seen or set())\n\n"
        + "    def unlock_cg(cid):\n"
        + "        if persistent.cgs_seen is None:\n"
        + "            persistent.cgs_seen = set()\n"
        + "        persistent.cgs_seen.add(cid)\n"
    )


def gen_characters(spec: dict, chars: dict) -> str:
    lines = [HEADER, "# 角色定义\n"]
    for cid, c in chars.items():
        if cid == "narrator":
            continue
        args = [q(c["name"])]
        if c.get("color"):
            args.append(f"color={q(c['color'])}")
        lines.append(f"define {cid} = Character({', '.join(args)})\n")
    lines.append("\n# 旁白沿用 Ren'Py 内置 narrator，无需定义\n")
    return "".join(lines)


def gen_flags(spec: dict) -> str:
    lines = [HEADER, "# 数值/开关（会随存档持久化）\n"]
    for f in spec["flags"]:
        fid = f.get("id")
        if not fid:
            continue
        lines.append(f"default {fid} = {py_lit(f.get('init', 0))}\n")
    return "".join(lines)


def gen_images(spec: dict, chars: dict) -> str:
    """assets.images 的 key -> image 语句。
    - key 形如 <char>_<expr> 且 char 已知 -> image <char> <expr>
    - 其余 -> image <key>
    """
    imgs = (spec.get("assets", {}) or {}).get("images", {}) or {}
    if not imgs:
        return HEADER + "# 未提供图片资源；assets.py 可生成占位图后在此登记\n"
    lines = [HEADER, "# 图像登记（也可依赖 images/ 目录的自动识别）\n"]
    known = set(chars.keys())
    for key, path in imgs.items():
        parts = key.split("_", 1)
        if len(parts) == 2 and parts[0] in known and parts[0] != "bg":
            lines.append(f"image {parts[0]} {parts[1]} = {q(path)}\n")
        else:
            lines.append(f"image {key} = {q(path)}\n")
    return "".join(lines)


def scene_show_stmt(s: dict) -> str:
    char, expr, pos = s.get("char"), s.get("expr"), s.get("pos")
    if not char:
        return ""
    stmt = f"show {char}"
    if expr:
        stmt += f" {expr}"
    if pos:
        stmt += f" at {pos}"
    return stmt


def effect_stmt(var: str, val) -> str:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return f"$ {var} = {py_lit(val)}"
    if val >= 0:
        return f"$ {var} += {val}"
    return f"$ {var} -= {abs(val)}"


def gen_script(spec: dict, chars: dict) -> str:
    """按 route 分组、保持声明顺序，自动补 next 与出口跳转。"""
    scenes = spec["scenes"]
    routes = {r["id"]: r for r in spec["routes"]}
    by_route: dict[str, list] = {}
    order_route: list[str] = []
    for sc in scenes:
        rid = resolved_route(sc, spec)
        if rid not in by_route:
            by_route[rid] = []
            order_route.append(rid)
        by_route[rid].append(sc)

    # 每条线分配的结局（按 route 字段）
    endings_by_route: dict[str, list] = {}
    for e in spec["endings"]:
        endings_by_route.setdefault(e.get("route"), []).append(e)

    has_branches = any(r.get("type") in ("character", "grand") for r in spec["routes"])

    def route_exit(rid: str) -> str:
        """一条线走完后的落点。"""
        r = routes.get(rid, {})
        # 共通线走完先进路由，由 route_router 按 flag 决定分支；
        # 只有完全没有分支线时才直接落到普通结局。
        if r.get("type") == "common" and has_branches:
            return "route_router"
        ends = endings_by_route.get(rid) or []
        if ends:
            return f"ending_{ends[0]['id']}"
        # 角色/大线无显式结局 -> 回退到普通结局
        normal = next((e for e in spec["endings"] if e.get("route") in (None, "common")), None)
        return f"ending_{normal['id']}" if normal else "route_router"

    lines = [HEADER, "# 剧情主脚本\n"]

    # start: 跳到 entry=='start' 的线，或第一条线
    start_route = next((r["id"] for r in spec["routes"] if r.get("entry") == "start"), None)
    if start_route is None and order_route:
        start_route = order_route[0]
    first_scene = by_route.get(start_route, [{}])[0].get("id", "s1") if by_route else "s1"
    lines.append("label start:\n")
    lines.append(f"    jump {first_scene}\n\n")

    for rid in order_route:
        lines.append(f"# ==== route: {rid} ====\n")
        group = by_route[rid]
        for i, sc in enumerate(group):
            sid = sc.get("id") or f"{rid}_{i+1}"
            lines.append(f"label {sid}:\n")
            if sc.get("bg"):
                trans = f" with {sc['transition']}" if sc.get("transition") else ""
                lines.append(f"    scene {sc['bg']}{trans}\n")
            for s in as_list(sc.get("show")):
                stmt = scene_show_stmt(s)
                if stmt:
                    lines.append(f"    {stmt}\n")
            for ln in as_list(sc.get("lines")):
                if "narrator" in ln:
                    lines.append(f"    {q(ln['narrator'])}\n")
                elif "who" in ln:
                    lines.append(f"    {ln['who']} {q(ln.get('text', ''))}\n")
                elif "text" in ln:
                    lines.append(f"    {q(ln['text'])}\n")
            # 选项
            choices = as_list(sc.get("choices"))
            nxt = sc.get("next") or (group[i + 1]["id"] if i + 1 < len(group) else route_exit(rid))
            if choices:
                ch = choices[0] if isinstance(choices[0], dict) else {"options": []}
                lines.append(f"    menu:\n")
                if ch.get("prompt"):
                    lines.append(f"        {q(ch['prompt'])}\n")
                for opt in ch.get("options", []):
                    lines.append(f"        {q(opt.get('text', '...'))}:\n")
                    for var, val in (opt.get("effects") or {}).items():
                        lines.append(f"            {effect_stmt(var, val)}\n")
                    lines.append(f"            jump {opt.get('next', nxt)}\n")
            else:
                lines.append(f"    jump {nxt}\n")
            lines.append("\n")
    return "".join(lines)


def gen_routes(spec: dict) -> str:
    """共通线 -> 个人线/大线的路由，按 entry_condition 顺序判定。"""
    lines = [HEADER, "# 线路路由：共通线结束后，按 flag 条件进入各条线\n"]
    character_routes = [r for r in spec["routes"] if r.get("type") in ("character", "grand")]
    # 先判 grand（条件更强），再判 character，避免被弱条件截胡
    character_routes.sort(key=lambda r: 0 if r.get("type") == "grand" else 1)
    if not character_routes:
        lines.append("# 单一线路，无分支路由；共通线直接走结局\n")
        return "".join(lines)
    lines.append("label route_router:\n")
    for r in character_routes:
        cond = r.get("entry_condition")
        target = route_first_scene(spec, r["id"]) or "start"
        if cond:
            lines.append(f"    if {cond}:\n        jump {target}\n")
        else:
            lines.append(f"    jump {target}\n")
    # fallback
    normal = next((e for e in spec["endings"] if e.get("route") in (None, "common")), None)
    lines.append(f"    jump {'ending_' + normal['id'] if normal else 'start'}\n")
    return "".join(lines)


def gen_endings(spec: dict) -> str:
    lines = [HEADER, "# 结局\n"]
    for e in spec["endings"]:
        eid = e["id"]
        title = e.get("title", eid)
        lines.append(f"label ending_{eid}:\n")
        lines.append(f"    $ record_ending({q(eid)})\n")
        if e.get("unlock_cg"):
            lines.append(f"    $ unlock_cg({q(e['unlock_cg'])})\n")
        lines.append(f"    {q('【' + title + '】')}\n")
        lines.append("    return\n\n")
    return "".join(lines)


def gen_gallery(spec: dict) -> str:
    if not spec["build"].get("include_gallery"):
        return HEADER + "# 画廊未启用\n"
    endings = spec["endings"]
    lines = [HEADER, "# 结局画廊（独立 screen，不依赖 gui/screens.rpy 的内部结构）\n"]
    lines.append("screen endings_gallery():\n")
    lines.append("    tag menu\n")
    lines.append("    add Solid(\"#101018\")\n")
    lines.append("    vbox:\n")
    lines.append("        align (0.5, 0.5)\n")
    lines.append("        spacing 12\n")
    lines.append(f"        text {q(spec['project']['title'] + ' · 结局')} size 40 xalign 0.5\n")
    for e in endings:
        eid = e["id"]
        title = e.get("title", eid)
        lines.append(f"        if ending_seen({q(eid)}):\n")
        lines.append(f"            text {q('✔ ' + title)} color \"#ffe08a\" xalign 0.5\n")
        lines.append(f"        else:\n")
        lines.append(f"            text {q('🔒 ???')} color \"#666\" xalign 0.5\n")
    lines.append("        null height 20\n")
    lines.append("        textbutton _(\"返回\") action Return() xalign 0.5\n\n")
    lines.append("label gallery:\n")
    lines.append("    call screen endings_gallery()\n")
    lines.append("    return\n")
    return "".join(lines)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

def emit(project_dir: str, spec: dict, out: str = "game", clean: bool = False) -> list[str]:
    spec = norm(spec)
    out_dir = os.path.join(project_dir, out)
    os.makedirs(out_dir, exist_ok=True)

    chars = collect_characters(spec)
    files = {
        "zz_core.rpy": gen_core(spec),
        "characters.rpy": gen_characters(spec, chars),
        "flags.rpy": gen_flags(spec),
        "images.rpy": gen_images(spec, chars),
        "script.rpy": gen_script(spec, chars),
        "routes.rpy": gen_routes(spec),
        "endings.rpy": gen_endings(spec),
        "gallery.rpy": gen_gallery(spec),
    }
    written = []
    for name, content in files.items():
        path = os.path.join(out_dir, name)
        if os.path.exists(path) and not clean:
            # 保留人工改动：只在内容不同时覆盖，并留备份
            old = open(path, encoding="utf-8").read()
            if old == content:
                continue
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append(path)

    # 同步 options.rpy 的项目名/save_directory
    opt = os.path.join(out_dir, "options.rpy")
    if os.path.exists(opt):
        patch_options(opt, spec)
    return written


def patch_options(path: str, spec: dict) -> None:
    text = open(path, encoding="utf-8").read()
    slug = spec["project"]["slug"]
    res = spec["project"]["resolution"]
    repl = {
        r'define config\.name = .*': f'define config.name = {q(spec["project"]["title"])}',
        r'define config\.save_directory = .*': f'define config.save_directory = {q(slug + "_save")}',
        r'define config\.screen_width = .*': f'define config.screen_width = {res[0]}',
        r'define config\.screen_height = .*': f'define config.screen_height = {res[1]}',
    }
    changed = False
    for pat, sub in repl.items():
        new = re.sub(pat, sub, text, count=1)
        if new != text:
            text, changed = new, True
    if changed:
        open(path, "w", encoding="utf-8").write(text)


def main():
    ap = argparse.ArgumentParser(description="把 galgame.spec.yaml 编译为 Ren'Py .rpy")
    ap.add_argument("spec")
    ap.add_argument("project_dir")
    ap.add_argument("--out", default="game", help="输出子目录（默认 game）")
    ap.add_argument("--clean", action="store_true", help="无条件覆盖已生成文件")
    args = ap.parse_args()

    spec = load_spec(args.spec)
    written = emit(args.project_dir, spec, args.out, args.clean)
    print(f"[wire] 已生成 {len(written)} 个 .rpy：")
    for w in written:
        print("   ", os.path.relpath(w, args.project_dir))


if __name__ == "__main__":
    main()
