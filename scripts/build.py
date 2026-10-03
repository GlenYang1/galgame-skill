#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.py —— 调用 Ren'Py 官方 CLI 做 lint / 编译 / 启动 / 打包。

用法:
    python3 build.py <project_dir> --action lint|compile|run|add_from|pc|mac|web|android
                      [--sdk /path/to/renpy-sdk] [--print-only] [--dest DIR]

Ren'Py 命令行（以 SDK 根目录下的 renpy.sh 为主，CLI 在不同版本间可能微调）:
    ./renpy.sh <base> lint [--error-code]
    ./renpy.sh <base> compile
    ./renpy.sh <base> add_from
    ./renpy.sh launcher distribute <base> [--destination DIR]
    ./renpy.sh launcher web_build <base>
    ./renpy.sh launcher android_build <base>
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scaffold import find_sdk  # noqa: E402


def build_cmd(action: str, sdk: str, project: str, dest: str) -> list[str]:
    sh = os.path.join(sdk, "renpy.sh") if os.path.exists(os.path.join(sdk, "renpy.sh")) else "renpy"
    if action == "lint":
        return [sh, project, "lint", "--error-code"]
    if action == "compile":
        return [sh, project, "compile"]
    if action == "run":
        return [sh, project]
    if action == "add_from":
        return [sh, project, "add_from"]
    if action in ("pc", "mac", "linux", "markets"):
        cmd = [sh, "launcher", "distribute", project, "--package", action]
        if dest:
            cmd += ["--destination", dest]
        return cmd
    if action == "web":
        return [sh, "launcher", "web_build", project]
    if action == "android":
        return [sh, "launcher", "android_build", project]
    raise SystemExit(f"[build] 未知 action: {action}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--action", required=True)
    ap.add_argument("--sdk", default="")
    ap.add_argument("--dest", default="")
    ap.add_argument("--print-only", action="store_true")
    args = ap.parse_args()

    sdk = find_sdk(args.sdk)
    if not sdk:
        print("[build] 找不到 Ren'Py SDK，请 --sdk 指定或设置 $RENPY_SDK", file=sys.stderr)
        sys.exit(2)

    cmd = build_cmd(args.action, sdk, args.project_dir, args.dest)
    print("[build] 执行:", " ".join(cmd))
    if args.print_only:
        return
    try:
        rc = subprocess.call(cmd, cwd=sdk)
    except FileNotFoundError:
        print("[build] 无法执行 renpy.sh；请确认 SDK 路径与执行权限", file=sys.stderr)
        sys.exit(2)
    sys.exit(rc)


if __name__ == "__main__":
    main()
