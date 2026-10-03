# 生成用的 prompt 配方

「全自动 / 半自动」模式里，agent 用这些配方把一句设定扩写进 `galgame.spec.yaml`。
原则：**先扩写进 spec，再编译**；任何时候都不直接手写 .rpy。

## 配方 A：从 logline 生成角色表

> 依据以下设定，设计 3~5 名角色。为每名角色给出：英文 `id`、中文 `name`、
> 名字颜色（十六进制）、3~4 个 `sprite_slots`（表情）、一句 `arc`（弧光）、
> 以及归属的 `route`（每个主要角色一条）。只输出 YAML，字段与 spec 的
> `characters` 一致。设定：{logline}

## 配方 B：从角色与题材生成三幕场景

> 为下面这款 galgame 生成场景（`scenes`）。要求：
> 1. 分「共通线(common)」与各角色线；共通线 6~8 场，每条角色线 2~3 场。
> 2. 每场给出 `id`、`route`、`bg`（形如 bg_xxx）、必要的 `show`（谁、什么表情、站位）、
>    3~8 条 `lines`（旁白与对白，带角色性格）、关键处放 `choices`、并给 `next`。
> 3. 对白要口语、有潜台词，不要解说腔。输出 YAML。
> 设定：{meta}；角色：{characters}

## 配方 C：设计好感度与结局条件

> 为下面角色设计 `flags` 与 `endings`。要求：
> 1. 每个主要角色一个 int 好感度（0 起步），若干 bool 事件 flag。
> 2. 每条角色线 1 个好结局 + 可能的普通结局；一条真结局线要求多个 flag 同时满足。
> 3. 进入线的阈值与达成结局的阈值要留出差距（如进入 >=5、好结局 >=8）。
> 4. 只输出 YAML，字段与 spec 的 `flags`/`endings`/`routes.entry_condition` 一致。
> 角色：{characters}

## 配方 D：登记美术

> 为下面所有场景与角色列出需要的图像，输出 `assets.images` 的 YAML：
> key 用 `bg_<地点>` / `<角色id>_<表情>` / `cg_<事件>`，value 用
> `images/bg/…` `images/char/…` `images/cg/…` 路径。同时给出每张图一句
> 画面描述，供生图使用（可写进 manifest）。场景：{scenes}；角色：{characters}

## 配方 E：把已有剧本切成 spec

> 把下面的剧本整理进 spec 的 `scenes`：按自然段切场，识别地点→`bg`，
> 识别说话人→`who`，无主句→`narrator`，分支处→`choices`（为每个选项
> 推断它对哪些 flag 的影响）。保持原文对白不改写。剧本：{script}

## 收尾检查（每次都做）

1. `wire.py` 编译 → `validate.py` 跑到 0 error。
2. 若报「结局永远走不到」：回到配方 C，检查是不是有结局的阈值永远无法同时满足，
   或该结局没被任何 `next`/router 指向。
3. 若报「引用但未定义的图像」：跑 `assets.py` 补占位图，或用生图回填。
4. 对白全部过一遍 Humanizer，去掉 AI 腔。
