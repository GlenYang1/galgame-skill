#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assets.py —— 为缺失的图像生成占位图，并导出给「生图能力」的接棒清单。

用法:
    python3 assets.py <spec.yaml> <project_dir> [--game game]
                      [--manifest out.json] [--only-missing]

三种用法：
  * 生成占位图：让项目立刻能跑、能 lint（图像文件到位，不会缺图告警）。
  * 导出 manifest：把 spec 里每个图像 key 的理想描述整理成 JSON，
    交给 gen-images / Firecrawl 等能力产出正式美术，再回填到 assets.images。
  * --only-missing：只补缺失的，不覆盖已有正式图。

中文字体显式指定，避免标题渲染成方框（豆腐块）。
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess
import sys

try:
    import yaml
except Exception:
    yaml = None

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]


def find_font() -> str | None:
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", ":lang=zh"],
                             capture_output=True, text=True).stdout.strip()
        if out and os.path.exists(out):
            return out
    except Exception:
        pass
    return None


FONT_PATH = find_font()


def load_spec(path: str) -> dict:
    text = open(path, encoding="utf-8").read()
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_load(text)
    return json.loads(text)


def collect_keys(spec: dict) -> dict[str, str]:
    """返回 image key -> 目标相对路径。优先用 assets.images 的声明，其次按场景推断。"""
    imgs = (spec.get("assets", {}) or {}).get("images", {}) or {}
    keys = dict(imgs)
    for sc in spec.get("scenes", []) or []:
        if sc.get("bg"):
            keys.setdefault(sc["bg"], f"images/bg/{sc['bg']}.png")
        for s in (sc.get("show") or []):
            if s.get("char") and s.get("expr"):
                k = f"{s['char']}_{s['expr']}"
                keys.setdefault(k, f"images/char/{k}.png")
    return keys


def guess_kind(key: str) -> str:
    if key.startswith("bg"):
        return "background"
    if key.startswith("cg"):
        return "cg"
    if key.startswith("ui") or key.startswith("logo"):
        return "ui"
    return "sprite"


def placeholder(key: str, kind: str, res: tuple[int, int], path: str, title: str = "") -> None:
    W, H = res
    if kind == "sprite":
        w, h = int(H * 0.62), H
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([w * 0.12, H * 0.06, w * 0.88, h * 0.98],
                            radius=28, fill=(60, 66, 96, 220), outline=(150, 170, 230, 255), width=4)
    else:
        w, h = W, H
        img = Image.new("RGBA", (w, h), (28, 30, 46, 255))
        d = ImageDraw.Draw(img)
        for y in range(h):  # 竖向渐变
            t = y / max(1, h - 1)
            d.line([(0, y), (w, y)], fill=(int(28 + 30 * t), int(30 + 24 * t), int(46 + 40 * t), 255))
        d.rectangle([8, 8, w - 8, h - 8], outline=(120, 140, 200, 200), width=3)

    label = f"[{kind}] {key}"
    size = max(28, h // 22)
    font = ImageFont.truetype(FONT_PATH, size) if FONT_PATH else ImageFont.load_default()
    try:
        box = d.textbbox((0, 0), label, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
    except Exception:
        tw, th = len(label) * size // 2, size
    d.text(((w - tw) / 2, (h - th) / 2), label, font=font, fill=(255, 240, 200, 255))
    if title and kind != "sprite":
        tf = ImageFont.truetype(FONT_PATH, max(20, size // 2)) if FONT_PATH else font
        tb = d.textbbox((0, 0), title, font=tf)
        d.text(((w - (tb[2] - tb[0])) / 2, (h + th) / 2 + size * 0.6), title,
               font=tf, fill=(200, 210, 240, 220))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("project_dir")
    ap.add_argument("--game", default="game")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--only-missing", action="store_true")
    args = ap.parse_args()

    if FONT_PATH is None:
        print("[assets] 警告：未找到中文字体，占位图文字可能显示为方框", file=sys.stderr)

    spec = load_spec(args.spec)
    res = tuple((spec.get("project", {}) or {}).get("resolution", [1920, 1080]))
    base = os.path.join(args.project_dir, args.game)
    keys = collect_keys(spec)

    manifest = []
    made = 0
    for key, rel in keys.items():
        kind = guess_kind(key)
        # assets.images 里给的是相对项目根的路径，落到 game/ 下
        rel_in_game = rel if rel.startswith("images/") or rel.startswith("audio/") else os.path.join("images", rel)
        dst = os.path.join(base, rel_in_game)
        exists = os.path.exists(dst) or bool(glob.glob(os.path.splitext(dst)[0] + ".*"))
        if not exists or not args.only_missing:
            placeholder(key, kind, res, dst, spec.get("project", {}).get("title", ""))
            made += 1
        manifest.append({
            "key": key, "kind": kind, "path": os.path.join("game", rel_in_game),
            "exists": exists,
            "suggested_prompt": f"{spec.get('project', {}).get('title', '')} {kind} - {key}",
            "source": "user" if exists else "placeholder",
        })

    out = {"resolution": list(res), "assets": manifest}
    if args.manifest:
        with open(args.manifest, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print(f"[assets] manifest -> {args.manifest}")
    print(f"[assets] 生成/确认 {made} 张占位图，共 {len(keys)} 个图像 key")


if __name__ == "__main__":
    main()
