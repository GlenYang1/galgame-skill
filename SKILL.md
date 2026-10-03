---
name: galgame
description: 用 Ren'Py 制作可运行的 galgame / 视觉小说 / 文字冒险游戏。当用户想创建、扩展或打包一个 galgame——生成剧情、角色、线路、选项、结局，把它们编译成 Ren'Py 的 .rpy 工程，产出或放置美术，lint 校验并打包——时使用。支持"部分输入"：情节、图片、人物线、选项、结局、线路结构全部可选，用户给多少用多少，其余自动补全。
license: MIT
metadata:
  version: 1.0.0
  engine: "Ren'Py 8.x"
  author: ClawsGO Science Agent
---

# Galgame Builder（Ren'Py 视觉小说生成）

把「一句设定 + 若干可选素材」变成一套 **lint 干净、能直接跑** 的 Ren'Py 工程。
声明式输入（`galgame.spec.yaml`）→ 单向编译 → 命令式输出（`.rpy`），全程可重复、幂等。

## 何时启用

用户提到 galgame、Galgame、视觉小说、VN、文字冒险、恋爱模拟、Ren'Py、AVG、选项分支、多结局、
立绘/背景/CG、人物线/角色线时启用。也用于给已有工程「加一条线 / 加一个结局 / 换一批美术」。

## 核心原则：一切输入皆可选

本 skill 的契约是 **降级可用**。用户可能只给一个标题，也可能给全套剧本和美术。
**缺什么就生成什么**，绝不停下来追问"还缺 XX"：

| 用户给了 | 处理 |
|---|---|
| 只有 `project.title` | 生成共通线骨架 + 默认结局，可跑 |
| 给了 logline / 题材 | 按题材生成人物、场景、分支 |
| 给了角色 | 只补缺失的表情槽、线路 |
| 给了 scenes | 直接编译，只补 next/出口跳转 |
| 给了图片路径 | 直接登记；没给的文件名生成占位图 |
| 给了结局/线路条件 | 按条件生成 router 与 ending 标签 |

**唯一必填字段是 `project.title`。** 其余留空即自动生成。

## 输入契约（速览）

完整字段见 `references/spec-schema.md`。最常用的顶层字段：

```yaml
project:   {title, slug, resolution, language, theme}
meta:      {genre, tone, rating, logline}          # 风格约束
characters: [{id, name, color, sprite_slots, arc, route}]
flags:     [{id, init, type}]                       # 数值/开关，决定走向
routes:    [{id, type: common|character|grand, entry_condition}]
scenes:    [{id, route, bg, transition, show, lines, choices, next}]
choices:   [{id, prompt, options: [{text, effects, next}]}]   # 可内联在 scene 里
endings:   [{id, title, route, requires, unlock_cg}]
assets:    {images: {key: path}, audio: {key: path}}
build:     {include_gallery, target}
```

## 四种运行模式（按用户给的信息量自动选）

1. **全自动**：只有标题/题材 → 从零生成完整小体量 galgame。
2. **半自动**：给了 logline + 角色 → 生成场景/分支/结局，保留用户设定。
3. **导入式**：给了完整 scenes + 美术 → 只做编译、接线、校验、打包。
4. **增量式**：已有工程 → 追加一条线/一个结局/一批 CG，改 spec 后重编译。

## 标准工作流

```
0. 判模式      —— 看用户手里有什么，决定上面的 1~4
1. 起草 spec   —— 写 galgame.spec.yaml（缺的字段留空，别硬编）
2. 建工程骨架  —— python3 scripts/scaffold.py <proj> --name "标题"
3. 编译 .rpy   —— python3 scripts/wire.py galgame.spec.yaml <proj>
4. 备美术      —— python3 scripts/assets.py galgame.spec.yaml <proj> --manifest m.json
                  （有正式图就放进 images/，没有就先用占位图跑通）
5. 校验        —— python3 scripts/validate.py <proj>
                  有 ERROR 必须回改 spec 并重编译，直到 0 error
6. 打包/交付   —— python3 scripts/build.py <proj> --action pc   （或 web）
```

第 5 步是**循环**：`validate.py` 报出的每一条 ERROR 都指向 spec 的一处结构问题
（如"某结局永远走不到"），回到第 3 步修，不要靠手改生成的 .rpy 绕过。

## 脚本工具

| 脚本 | 作用 | 退出码 |
|---|---|---|
| `scripts/scaffold.py` | 从 SDK `template/` 复制工程骨架，改 name/save_directory | 2=缺 SDK |
| `scripts/wire.py` | **核心**：spec → 8 个 .rpy（角色/flag/图像/剧情/路由/结局/画廊/核心） | 1=spec 错 |
| `scripts/assets.py` | 缺图生成占位图（显式指定中文字体）+ 导出给生图能力的 manifest | 0 |
| `scripts/validate.py` | 静态一致性检查（可达性/结局/缺图/未定义角色）+ 可选官方 lint | 1=有 error |
| `scripts/build.py` | 包 `renpy.sh`：lint / compile / run / pc / mac / web / android | 透传 |

所有脚本都支持 `--print-only`（scaffold/build）或 `--json`（validate），便于在流水线里接。

## 与其它 skill 协同（按流水线阶段）

- **Planning with Files** → 维护 `galgame.spec.yaml` 与路线图，作为长任务的单一事实源。
- **Humanizer** → 对白/旁白过一遍，去掉 AI 腔，让角色说话像人。
- **gen-images** → 读 `assets.py` 的 manifest，产出立绘/背景/CG，回填 `assets.images`。
- **Firecrawl** → 抓设定集、参考资料、素材来源、引擎文档。
- **Browser use** → 构建 web 版后在线试玩；查 Ren'Py 文档与社区范例。
- **Code review** → 审生成的 .rpy 与脚本质量、命名一致、无魔法数。
- **Frontend design Anthropic** → 改 GUI 主题（`gui.rpy`/`screens.rpy`）与界面观感。
- **Guizang PPT** → 把设定/路线图导出成策划 PPT 或发售页面素材。
- **Skill Creator** → 用来迭代本 skill 本身（增删脚本、改 description 触发）。
- **Superpowers** → 长任务编排与深度推理，尤其在"全自动"模式下铺大结构时。
- **find skill** → 找同类 skill/范例，复用既有轮子。

## 质量红线（交付前自查）

- `validate.py` **0 error**；warning 要能解释（如"故意留的占位结局")。
- `label start:` 存在且能走到至少一个 `ending_*`。
- 每条线（route）都有入口场景，router 的每个跳转目标都存在。
- 图像引用要么有文件、要么有 `image` 语句；缺图跑过 `assets.py`。
- 生成的中文文本所在 .rpy **编码为 UTF-8**；图像里的中文用显式中文字体渲染。
- 不手改 `wire.py` 生成的文件后又被覆盖——要改就改 spec（或改 spec 后重编译）。

## 常见坑

- **jump vs call**：`jump` 单程、`call` 需 `return` 配对；混用会重复场景或死循环。
- **label 重名**：所有 .rpy 内 label 全局唯一，重名直接起不来。
- **`default` vs `define`**：会进存档的变量用 `default`；常量用 `define`。
- **路由顺序**：条件强的线（grand/真结局）要先判，否则被弱条件截胡。
- **坐标/转场**：`scene X with fade`、`show c e at left`；`at` 只在需要定位置时给。
- **CLI 非稳定接口**：不同 Ren'Py 版本 lint/distribute 的选项可能微调，用 `--help` 确认。

## 参考文件

- `references/spec-schema.md` — 输入契约全字段与语义
- `references/renpy-syntax.md` — 生成时用到的 Ren'Py 语法速查
- `references/galgame-patterns.md` — 线路/好感度/结局/画廊/存档的惯用模式
- `assets/spec.example.yaml` — 一份填满的示例 spec
- `assets/prompts.md` — 把设定扩写进 spec 的 prompt 配方
