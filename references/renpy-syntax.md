# Ren'Py 语法速查（本 skill 生成时用到的部分）

面向"生成 .rpy"这一用途，只列高频、易错的语法。

## 文件与项目结构

```
project/
├── game/
│   ├── script.rpy          # 剧情主脚本（label start 所在）
│   ├── characters.rpy      # define X = Character(...)
│   ├── options.rpy         # config.name / save_directory / 尺寸
│   ├── gui.rpy             # 界面外观
│   ├── screens.rpy         # 对话框/菜单/存档 等屏幕
│   ├── images/  ├ bg/ ├ char/ ├ cg/
│   └── audio/
└── (sdk 相关文件)
```
同一目录下所有 `.rpy` 会被一起编译，label 名**全局唯一**。

## 标签与控制流

```renpy
label start:          # 入口，必须有
label alice_route_1:  # 任意唯一名
    jump other        # 单程转移
    call sub          # 记栈，需配对 return
label sub:
    return
```
- `jump` 不返回；`call`/`return` 配对，用于子过程。
- 特殊 label：`start`、`quit`、`after_load`、`splashscreen`、`main_menu`。

## 变量

```renpy
define config.name = _("标题")   # 常量，不进存档
default alice_affection = 0       # 会随存档持久化
$ alice_affection += 1            # 运行时修改
```

## 角色与对白

```renpy
define alice = Character("爱丽丝", color="#ff88aa")
alice "你好。"          # 具名对白
"海风很冷。"            # 裸字符串 = 旁白(narrator)
```

## 图像 / 场景 / 转场

```renpy
image bg_seaside = "images/bg/seaside.png"
image alice happy = "images/char/alice_happy.png"   # 名字带空格
scene bg_seaside with fade      # 换场景
show alice happy at left        # 出场；位置 left/center/right/truecenter
hide alice
with dissolve                   # 转场
```

## 菜单（选项）

```renpy
menu:
    "要怎么回应？"               # 标题（可选）
    "认真回答":
        $ alice_affection += 1
        jump s2
    "沉默":
        jump s2
```

## if / 条件分支

```renpy
if alice_affection >= 8:
    jump true_route_1
elif alice_affection >= 5:
    jump alice_route_1
else:
    jump ending_normal
```

## 屏幕（screen language，用于画廊/自定义 UI）

```renpy
screen endings_gallery():
    tag menu
    add Solid("#101018")
    vbox:
        align (0.5, 0.5)
        text "结局" size 40
        textbutton _("返回") action Return()

label gallery:
    call screen endings_gallery()
    return
```
- 常用的内建 action：`Jump()`、`Call()`、`Return()`、`Show()`、`Hide()`、
  `SetVariable()`、`ToggleVariable()`、`Preference()`。
- `add Solid("#rrggbb")` 是最省事的纯色底，不依赖主题。

## persistent（跨存档/跨周目）

```renpy
default persistent.endings_seen = set()
$ persistent.endings_seen.add("true")
```
适合做画廊解锁、结局收集、二周目内容。

## lint 与打包（SDK 根目录下）

```bash
./renpy.sh <项目> lint --error-code      # 校验，有错退出码 1
./renpy.sh <项目> compile                 # 重新生成 .rpyc
./renpy.sh <项目> add_from                # 给 call 补 from 子句（发版前）
./renpy.sh launcher distribute <项目>     # 打包 pc/mac
./renpy.sh launcher web_build <项目>      # 打 web 版
```
> 注意：Ren'Py 官方声明 CLI 不是稳定接口，跨版本选项可能变化，用 `--help` 确认。

## 易错点

- 缩进必须一致（空格，通常 4 个）；缺冒号、引号不闭合都会报错。
- `scene` 在 image 层；`show` 主角层；背景不要用 `show`。
- 图像文件名建议 `<角色>_<表情>.png`，Ren'Py 会自动识别成 `image 角色 表情`。
- 中文文本请确保 .rpy 为 UTF-8；图像里的中文要用显式中文字体渲染。
