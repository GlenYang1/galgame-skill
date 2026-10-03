#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scaffold.py —— 从 Ren'Py SDK 的 template/ 复制出一个新项目骨架。

Ren'Py 没有 `renpy create` 之类的建项目命令；官方做法是把 SDK 里的 template
目录复制过来、删掉 launcherinfo.py、再改一个唯一的 save_directory（见 Lemma Soft 论坛）。

用法:
    python3 scaffold.py <project_dir> [--sdk /path/to/renpy-sdk]
                        [--name "游戏名"] [--slug star_echo] [--template DIR]
                        [--print-only]

SDK 定位顺序: --sdk > $RENPY_SDK > 常见安装路径 > PATH 中的 renpy。
"""
from __future__ import annotations
import argparse
import os
import re
import shutil
import sys

COMMON_SDK_PATHS = [
    os.path.expanduser("~/renpy-sdk"),
    os.path.expanduser("~/renpy"),
    "/opt/renpy-sdk",
    "/opt/renpy",
    "/usr/local/renpy",
    "/usr/share/renpy",
]
TEMPLATE_SUBDIRS = ["template", "templates", "templates/english"]


def looks_like_sdk(path: str) -> bool:
    return os.path.exists(os.path.join(path, "renpy.sh")) or \
        os.path.exists(os.path.join(path, "renpy.py"))


def find_sdk(explicit: str = "") -> str | None:
    cands = []
    if explicit:
        cands.append(explicit)
    if os.environ.get("RENPY_SDK"):
        cands.append(os.environ["RENPY_SDK"])
    cands += COMMON_SDK_PATHS
    if which := shutil.which("renpy"):
        cands.append(os.path.dirname(os.path.dirname(which)))
    for c in cands:
        if c and looks_like_sdk(c):
            return c
    return None


def find_template(sdk: str, explicit: str = "") -> str | None:
    if explicit:
        return explicit if os.path.isdir(explicit) else None
    for sub in TEMPLATE_SUBDIRS:
        p = os.path.join(sdk, sub)
        if os.path.isdir(os.path.join(p, "game")):
            return p
    return None


def patch_options(path: str, name: str, slug: str) -> None:
    if not os.path.exists(path):
        return
    text = open(path, encoding="utf-8").read()
    text = re.sub(r'define config\.name = .*', f'define config.name = _("{name}")', text, count=1)
    text = re.sub(r'define config\.save_directory = .*',
                  f'define config.save_directory = "{slug}_save"', text, count=1)
    text = re.sub(r'define build\.name = .*', f'define build.name = "{slug}"', text, count=1)
    open(path, "w", encoding="utf-8").write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--sdk", default="")
    ap.add_argument("--template", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--slug", default="")
    ap.add_argument("--print-only", action="store_true")
    args = ap.parse_args()

    sdk = find_sdk(args.sdk)
    if not sdk and not args.template:
        print("[scaffold] 找不到 Ren'Py SDK。请用 --sdk 指定，或设置 $RENPY_SDK。", file=sys.stderr)
        print("           下载: https://www.renpy.org/latest.html", file=sys.stderr)
        sys.exit(2)
    template = find_template(sdk, args.template)
    if not template:
        print(f"[scaffold] SDK 内找不到 template 目录（试过 {TEMPLATE_SUBDIRS}）。"
              f"请用 --template 指定一个已有项目目录。", file=sys.stderr)
        sys.exit(2)

    name = args.name or os.path.basename(os.path.abspath(args.project_dir))
    slug = args.slug or re.sub(r"\W+", "_", name).strip("_").lower() or "game"

    print(f"[scaffold] SDK      : {sdk}")
    print(f"[scaffold] template : {template}")
    print(f"[scaffold] 目标     : {args.project_dir}")
    if args.print_only:
        return

    if os.path.exists(args.project_dir) and os.listdir(args.project_dir):
        print(f"[scaffold] 目标目录非空，为安全起见不覆盖：{args.project_dir}", file=sys.stderr)
        sys.exit(1)

    shutil.copytree(template, args.project_dir)
    # 删掉会让 launcher 认成"模板项目"的标记
    for junk in ("launcherinfo.py", "project.json"):
        p = os.path.join(args.project_dir, junk)
        if os.path.exists(p):
            os.remove(p)
    patch_options(os.path.join(args.project_dir, "game", "options.rpy"), name, slug)

    # 顺手放一份 .gitignore
    with open(os.path.join(args.project_dir, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write("/game/saves/\n/game/*.rpyc\n/*-dists/\n/.renpy/\n")

    print(f"[scaffold] 完成。接着运行 wire.py 把 spec 编译成 .rpy")
    print(f"           例: python3 scripts/wire.py galgame.spec.yaml {args.project_dir}")


if __name__ == "__main__":
    main()
