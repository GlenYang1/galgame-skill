#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate.py —— 对生成的 Ren'Py 项目做静态一致性检查（可选叠加官方 lint）。

用法:
    python3 validate.py <project_dir> [--game game] [--renpy /path/to/renpy.sh]
                        [--json] [--strict]

检查项（纯静态，无需安装 Ren'Py）:
  1. jump / call 的目标 label 是否存在
  2. 从 start 出发，是否存在不可达的 label
  3. 是否存在永远走不到的结局（ending_*）
  4. 剧本引用的图像（scene/show）是否已定义或文件已存在
  5. 出现过的角色是否已 define；flag 是否已 default
若提供 --renpy，则额外运行官方 `lint --error-code`。
退出码：0 通过；1 有 error（--strict 下 warning 也算失败）。
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import re
import subprocess
import sys

KEYWORDS = {
    "jump", "call", "menu", "scene", "show", "hide", "play", "stop", "queue",
    "pause", "return", "if", "elif", "else", "python", "init", "label", "with",
    "text", "image", "default", "define", "screen", "vbox", "hbox", "add", "at",
    "window", "nvl", "voice", "extend", "transform", "style", "layeredimage",
    "translate", "while", "for", "pass", "camera", "use",
}

RE_LABEL = re.compile(r"^\s*label\s+([A-Za-z_]\w*)")
RE_JUMP = re.compile(r"\b(?:jump|call)\s+(?!screen\b)([A-Za-z_]\w*)")
RE_DEF_CHAR = re.compile(r"^\s*define\s+([A-Za-z_]\w*)\s*=\s*Character\s*\(")
RE_DEFAULT = re.compile(r"^\s*default\s+([A-Za-z_]\w*)\s*=")
RE_IMAGE_DEF = re.compile(r'^\s*image\s+([\w ]+?)\s*=\s*"([^"]+)"')
RE_SCENE = re.compile(r"^\s*scene\s+([\w ]+?)(?:\s+with\s+\w+)?\s*$")
RE_SHOW = re.compile(r"^\s*show\s+([A-Za-z_]\w*)(?:\s+([A-Za-z_]\w*))?")
RE_SAY = re.compile(r'^\s{4,8}([A-Za-z_]\w*)\s+"')
RE_PERSISTENT_OK = re.compile(r"persistent\.")


def read_rpy(game_dir: str) -> list[tuple[str, str]]:
    out = []
    for path in sorted(glob.glob(os.path.join(game_dir, "*.rpy"))):
        out.append((os.path.basename(path), open(path, encoding="utf-8").read()))
    return out


def strip_comments(text: str) -> str:
    return "\n".join(l.split("#", 1)[0] if l.lstrip().startswith("#") else l
                     for l in text.splitlines())


def analyze(game_dir: str, project_dir: str) -> dict:
    files = read_rpy(game_dir)
    labels: dict[str, str] = {}          # label -> file
    jumps: list[tuple[str, str]] = []     # (target, file)
    chars_defined: set[str] = set()
    flags_defined: set[str] = set()
    images_defined: dict[str, str] = {}   # image name -> path
    scenes_used: set[str] = set()
    shows_used: set[str] = set()
    says_used: set[str] = set()
    label_bodies: dict[str, list[str]] = {}

    for fname, raw in files:
        text = strip_comments(raw)
        # 单遍扫描：把每一行归到"最近一个 label"之下，同时收集各类引用
        cur = None
        for line in text.splitlines():
            if m := RE_LABEL.match(line):
                cur = m.group(1)
                labels[cur] = fname
                label_bodies.setdefault(cur, [])
                continue
            if cur:
                label_bodies[cur].append(line)
            if m := RE_JUMP.search(line):
                jumps.append((m.group(1), fname))
            if m := RE_DEF_CHAR.match(line):
                chars_defined.add(m.group(1))
            if m := RE_DEFAULT.match(line):
                flags_defined.add(m.group(1))
            if m := RE_IMAGE_DEF.match(line):
                images_defined[m.group(1).strip()] = m.group(2)
            if m := RE_SCENE.match(line):
                scenes_used.add(m.group(1).strip())
            if m := RE_SHOW.match(line):
                base = m.group(1)
                full = f"{base} {m.group(2)}" if m.group(2) else base
                shows_used.add(full)
            if m := RE_SAY.match(line):
                says_used.add(m.group(1))

    # 磁盘上按文件名自动识别的图像（Ren'Py 用文件名，不含目录；空格分隔为多段名）
    disk_images = set()
    for ext in ("png", "jpg", "jpeg", "webp"):
        for p in glob.glob(os.path.join(game_dir, "images", "**", f"*.{ext}"), recursive=True):
            stem = os.path.splitext(os.path.basename(p))[0]
            disk_images.add(stem)                 # bg_room.png        -> bg_room
            disk_images.add(stem.replace("_", " "))  # alice_happy.png -> alice happy

    issues: list[dict] = []

    def issue(sev, kind, msg):
        issues.append({"severity": sev, "kind": kind, "message": msg})

    # 1. jump 目标存在性
    for target, fname in jumps:
        if target not in labels:
            issue("error", "missing-label", f"{fname}: jump/call 目标不存在 -> {target}")

    # 2. 可达性
    adj: dict[str, set[str]] = {}
    for lbl, body in label_bodies.items():
        outs = set()
        for line in body:
            if m := RE_JUMP.search(line):
                outs.add(m.group(1))
        adj[lbl] = outs
    seen, stack = set(), ["start"]
    while stack:
        n = stack.pop()
        if n in seen or n not in labels:
            continue
        seen.add(n)
        stack.extend(adj.get(n, ()))
    for lbl in labels:
        if lbl.startswith("ending_") or lbl.startswith("gallery"):
            continue  # 结局另有一致性检查，画廊为可选用户入口
        if lbl not in seen:
            issue("warning", "unreachable-label", f"从 start 无法到达 -> {lbl}")

    # 3. 结局可达
    ending_labels = [l for l in labels if l.startswith("ending_")]
    for el in ending_labels:
        if el not in seen:
            issue("error", "unreachable-ending", f"结局永远走不到 -> {el}")
    if not ending_labels:
        issue("warning", "no-ending", "项目里没有任何 ending_* 标签")

    # 4. 图像存在性
    for name in sorted(scenes_used | shows_used):
        if name in images_defined or name in disk_images:
            continue
        issue("warning", "missing-image",
              f"引用但未定义/不存在的图像 -> {name}（可用 assets.py 生成占位图）")

    # 5. 角色与 flag
    for who in sorted(says_used):
        if who in KEYWORDS or who in chars_defined:
            continue
        if who in ("narrator",):
            continue
        if who in flags_defined:
            continue
        issue("warning", "undefined-character",
              f"对白使用了未 define 的角色 -> {who}")

    return {"labels": len(labels), "jumps": len(jumps), "issues": issues}


def run_lint(project_dir: str, renpy_sh: str) -> dict | None:
    if not renpy_sh or not os.path.exists(renpy_sh):
        return None
    try:
        p = subprocess.run([renpy_sh, project_dir, "lint", "--error-code"],
                           capture_output=True, text=True, timeout=300)
    except Exception as e:  # pragma: no cover
        return {"ran": False, "error": str(e)}
    return {"ran": True, "returncode": p.returncode,
            "stdout": p.stdout[-4000:], "stderr": p.stderr[-2000:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--game", default="game")
    ap.add_argument("--renpy", default=os.environ.get("RENPY_SH", ""))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    game_dir = os.path.join(args.project_dir, args.game)
    if not os.path.isdir(game_dir):
        print(f"[validate] 找不到 {game_dir}", file=sys.stderr)
        sys.exit(2)

    report = analyze(game_dir, args.project_dir)
    lint = run_lint(args.project_dir, args.renpy)
    errors = [i for i in report["issues"] if i["severity"] == "error"]
    warns = [i for i in report["issues"] if i["severity"] == "warning"]

    if args.json:
        print(json.dumps({"static": report, "lint": lint}, ensure_ascii=False, indent=2))
    else:
        print(f"[validate] {report['labels']} 个 label，{report['jumps']} 处跳转")
        for i in report["issues"]:
            tag = "ERROR" if i["severity"] == "error" else "warn "
            print(f"  [{tag}] {i['message']}")
        if lint and lint.get("ran"):
            rc = lint["returncode"]
            print(f"[validate] 官方 lint 退出码 = {rc}")
            if rc != 0:
                print(lint.get("stdout", "")[-2000:])
        if not errors and not warns:
            print("[validate] 全部通过 ✔")

    if errors or (args.strict and warns):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
