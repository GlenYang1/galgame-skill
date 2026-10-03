# galgame.spec.yaml 输入契约

`wire.py` 的唯一输入。**除 `project.title` 外全部可选**；缺省由脚本按规则补全。
字段名用英文，值可以用中文。

## project（项目）

| 字段 | 类型 | 缺省 | 说明 |
|---|---|---|---|
| `title` | str | **必填** | 游戏名，写入 `config.name` |
| `slug` | str | 由 title 生成 | 英文标识，用于 `save_directory`/`build.name` |
| `resolution` | [w,h] | `[1920,1080]` | 屏幕尺寸 |
| `language` | str | `zh-CN` | 主语言 |
| `theme` | str | `classic` | 视觉主题，供 GUI 调整参考 |

## meta（风格约束，可选）

`genre` 题材、`tone` 基调/人称、`rating` 分级、`logline` 一句话梗概。
这些不影响编译，只作为生成剧情/对白时的风格锚点。

## characters（角色 / 人物线）

```yaml
- id: alice            # 必填。英文标识；对白写作 alice "台词"
  name: 爱丽丝          # 显示名
  color: "#ff88aa"     # 名字颜色
  sprite_slots: [neutral, happy, sad]   # 表情槽；决定要几张立绘
  arc: 角色弧光(自由文本)
  route: alice_route   # 归属线路；共通角色留空
```

缺省时：从 `scenes.lines[].who` 里出现的说话人自动补建角色（名字=id，无颜色）。

## flags（数值 / 开关）

```yaml
- {id: alice_affection, init: 0, type: int}
- {id: saw_lighthouse, init: false, type: bool}
```

`type` 仅作说明；实际由 `init` 推断。生成 `default <id> = <init>`。
选项的 `effects` 用 `+=`（数字）或 `=`（布尔/字符串）修改它们。

## routes（线路 / 各种线）

```yaml
- id: common
  type: common                 # common | character | grand
  title: 序章 ~ 第三章
  entry: start                 # 哪条线是开局；或填进入条件
- id: alice_route
  type: character
  entry_condition: alice_affection >= 5   # 从共通线进入本线的条件
```

缺省时：自动生成「一条 common + 每个带 route 的角色一条 character 线」。
`type: grand` 的线条件更强，路由时会**优先判定**，避免被角色线截胡。

## scenes（场景 / 情节）

```yaml
- id: s1                       # 必填；作为 label 名，需全局唯一
  route: common                # 归属线路；缺省归第一条线
  bg: bg_seaside               # 背景 image key
  transition: fade             # 可选转场：fade/dissolve/None
  show:                        # 出场立绘
    - {char: alice, expr: neutral, pos: left}   # pos: left/center/right/truecenter
  lines:                       # 对白/旁白
    - {narrator: "旁白文本"}    # 旁白（Ren'Py 内置 narrator）
    - {who: alice, text: "台词"}
  choices:                     # 内联选项（也可写成顶层 choices + 引用 id）
    - {id: c1, prompt: "…", options: [...]}
  next: s2                     # 下一场；缺省自动接本线路下一场/出口
```

**自动接线规则**：`next` 缺失 → 接同 route 的下一场；本 route 最后一场 → 接
`route_router`（有分支时）或对应结局。

## choices（选项）

```yaml
options:
  - text: 认真回答           # 按钮文字
    effects: {alice_affection: 1, saw_lighthouse: true}   # 数值/开关变更
    next: s2                 # 跳转目标；缺省用本场的 next
```

## endings（结局）

```yaml
- id: true_ending
  title: 真结局 · 回声归位
  route: true_route          # 归属线路
  requires: "alice_affection >= 8"   # 说明用；判定实际在 router 里
  scene: a1                  # 可选，指向结局前的场景
  unlock_cg: cg_finale       # 可选，解锁到画廊
```

缺省时：为共通线补一个 `normal` 结局，保证至少有终点。
生成 `label ending_<id>:`，内部 `record_ending("<id>")` + 显示结局卡 + `return`。

## assets（图片 / 音频）

```yaml
images:
  bg_seaside: images/bg/seaside.png       # bg_* -> image bg_seaside
  alice_happy: images/char/alice_happy.png # <角色>_<表情> -> image alice happy
  cg_finale: images/cg/finale.png
audio:
  bgm_main: audio/bgm_main.ogg
```

- key 形如 `<已知角色id>_<表情>` → 生成 `image <角色> <表情>`，这样 `show alice happy` 能用。
- 其它 key 原样生成 `image <key>`。
- 文件缺失时用 `assets.py` 生成占位图；有正式图直接放进对应路径即可。

## build（输出选项）

```yaml
build:
  include_gallery: true        # 生成结局画廊 screen + label gallery
  target: [pc, mac, web]       # 打包目标，对应 build.py 的 action
```
