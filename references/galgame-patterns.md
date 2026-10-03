# Galgame 惯用模式

生成 body 时反复用到的结构套路。`wire.py` 已内建其中多数，这里说明「为什么这样写」。

## 1. 线路拓扑

### 直线（无分支）
```
start → s1 → s2 → ending_normal
```
适合短篇、Demo。spec 里只写一条 `common` 线即可。

### 共通线 + 个人线（最经典）
```
              ┌─ alice_route ─→ ending_alice
start → common ┤
              └─ ren_route   ─→ ending_ren
        (route_router 按 flag 分流)
```
共通线结束时进 `route_router`，按各角色好感度决定进谁的线。
**判定顺序：先看条件更强的 grand 线，再看 character 线，最后兜底普通结局。**

### 带真结局（grand route）
```
route_router:
    真结局条件(多个 flag)  → true_route
    alice_affection >= 5   → alice_route
    ren_trust >= 5         → ren_route
    兜底                    → ending_normal
```
真结局通常要求「多个 flag 同时满足」，所以必须最先判。

## 2. 好感度 / flag 设计

- 用 `default <角色>_affection = 0` 起步，选项里 `+= 1`（或 +2 表示关键选择）。
- 布尔 flag 记「事件是否发生」：`saw_lighthouse`、`met_sister`。
- **进入线的阈值**（如 `>= 5`）与**结局的阈值**（如 `>= 8`）要留差距，
  否则一条线里所有结局都会在第一个判定点被同一条满足。
- 反面：阈值太密会让玩家无论怎么选都进同一结局——用 `validate.py` 的
  "结局永远走不到"告警反查这类问题。

## 3. 选项写法

```renpy
menu:
    "雨里，你要……"
    "把伞递给爱丽丝":
        $ alice_affection += 2
        jump s_street
    "陪莲等雨停":
        $ ren_trust += 2
        jump s_street
    "独自跑开":
        $ saw_lighthouse = True   # 埋一个后面才用到的伏笔
        jump s_street
```
- 选项文字短、带一点性格，别写成说明书。
- 每次选择至少影响一个 flag，否则分支没有意义（除非纯风格呈现）。
- 「沉默/离开」常常是埋暗线的好位置。

## 4. 结局标签

```renpy
label ending_true:
    $ record_ending("true")       # 记忆层，画廊用
    $ unlock_cg("cg_finale")
    "【真结局 · 回声归位】"
    return                        # 回主菜单
```
- 结局体量可以很大：先播一段结局专属场景，再 `record_ending` 收尾。
- 一个线可以有多个结局（好/坏/普通），由线内的 if 判定分流。

## 5. 结局 / CG 画廊（persistent 解锁）

```renpy
default persistent.endings_seen = set()

screen endings_gallery():
    tag menu
    add Solid("#101018")
    vbox:
        align (0.5, 0.5)
        text "结局"
        if ending_seen("true"):
            text "✔ 真结局" color "#ffe08a"
        else:
            text "🔒 ???" color "#666"
        textbutton _("返回") action Return()
```
- `persistent.` 变量跨存档保存，是画廊解锁的标准做法。
- 用 `tag menu` 让画廊替换菜单屏，避免多屏叠在一起。

## 6. 存档与章节边界

- 会进存档的状态全部用 `default` 声明，别用普通 Python 全局。
- 发版前跑 `./renpy.sh <项目> add_from`，给所有 `call` 补 `from` 子句，
  否则后续版本改动会让老存档错位。

## 7. 转场与演出（克制使用）

- `scene X with fade`：换大场景（时间/地点跳变）。
- `with dissolve`：同场景内小幅变化。
- `show alice happy at left`：立绘出场；`hide alice` 退场。
- 别每句都加转场——密集转场又慢又晕。默认不加，关键节点加。

## 8. 美术槽位约定

- 背景：`bg_<地点>`，1920×1080（或与分辨率一致）。
- 立绘：`<角色id>_<表情>`，竖构图，透明底，高度≈屏高。
- CG：`cg_<事件>`，全屏。
- `assets.py` 会为每个 key 生成同尺寸占位图，保证在正式美术到位前也能跑通与 lint。

## 9. 与"生成剧情"的配合

「全自动/半自动」模式下，把剧情落到 spec 的顺序：
logline → 拆 3 幕 → 每幕 3~5 场 → 关键抉择处放 menu → 每条角色线 2~3 场 → 结局。
**先写进 spec，再编译**；不要直接手写 .rpy，否则下次重编译会被覆盖。
