# galgame Skill for Ren'Py / Ren'Py Galgame 制作 Skill

把「一句设定 + 可选素材」编译成一套能直接跑的 Ren'Py 视觉小说工程。
支持部分输入：**情节、图片、人物线、选项、结局、线路结构全部可选**。

## 它做什么

```
galgame.spec.yaml  ──wire.py──▶  game/*.rpy  ──renpy──▶  可玩的 galgame
     (声明式)                      (命令式)                 (pc/web/…)
```

## 中文说明

### 功能

把声明式的 `galgame.spec.yaml` 编译为可运行的 Ren'Py 工程：

```text
galgame.spec.yaml -> wire.py -> game/*.rpy -> Ren'Py -> PC/Web 等发行包
```

支持剧情、角色、线路、选项、好感度、旗标、多结局、结局画廊、背景、立绘、CG、占位资源、静态检查、Ren'Py lint 和 PC/Web 等构建目标。

## English

This Agent Skills-compatible skill turns a declarative `galgame.spec.yaml` into a runnable Ren'Py visual-novel project. It covers story scenes, characters, routes, choices, flags, endings, image placeholders, validation, linting, and packaging.

### Installation / 安装

Codex / 支持 agent skills 标准的工具，把本目录放进对应的 skills 目录即可：

```bash
# Codex（用户级）
mkdir -p ~/.agents/skills && cp -r galgame ~/.agents/skills/

# 或项目级（随仓库走）
mkdir -p .agents/skills && cp -r galgame .agents/skills/
```

Claude Code 用 `~/.claude/skills/` 或 `.claude/skills/`；两者共用同一份 `SKILL.md` 规范。

## 依赖

- Python 3.10+，`PyYAML`（`pip install pyyaml`；用 JSON spec 则不需要）
- 生成占位图需要 `Pillow`，以及一款中文字体（脚本会自动探测 Noto Sans CJK）
- 真正编译/运行/lint 需要 **Ren'Py SDK 8.x**：https://www.renpy.org/latest.html
  （设 `RENPY_SDK=/path/to/sdk`，或给脚本传 `--sdk`）

## 快速开始

```bash
# 1. 写 spec（最小只要一行 title）
cat > galgame.spec.yaml <<'YAML'
project:
  title: "星海回声"
YAML

# 2. 建工程骨架（需要 SDK；也可先手工建空目录）
python3 scripts/scaffold.py ./star_echo --name "星海回声"

# 3. 编译成 .rpy
python3 scripts/wire.py galgame.spec.yaml ./star_echo

# 4. 生成占位美术 + 给生图能力的清单
python3 scripts/assets.py galgame.spec.yaml ./star_echo --manifest manifest.json

# 5. 校验（循环到 0 error）
python3 scripts/validate.py ./star_echo

# 6. 打包
python3 scripts/build.py ./star_echo --action pc
```

更完整的输入见 `assets/spec.example.yaml`，字段语义见 `references/spec-schema.md`。 Only `project.title` is required; other fields are optional.

## 目录

```
galgame/
├── SKILL.md                      # 触发与工作流（agent 读这个）
├── scripts/
│   ├── scaffold.py               # 从 SDK template 建工程
│   ├── wire.py                   # spec → .rpy（核心）
│   ├── assets.py                 # 占位图 + 生图清单
│   ├── validate.py               # 静态一致性 + 官方 lint
│   └── build.py                  # 调 renpy CLI 打包
├── references/
│   ├── spec-schema.md            # 输入契约全字段
│   ├── renpy-syntax.md           # Ren'Py 语法速查
│   └── galgame-patterns.md       # 线路/好感度/结局/画廊 套路
└── assets/
    └── spec.example.yaml         # 填满的示例
```

## License

MIT. See [LICENSE](LICENSE) when present.

ClawsGO Science Agent
