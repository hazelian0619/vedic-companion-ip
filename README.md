# Vedic Companion IP

> 把一份只在本地计算的出生信息，转化为一只可以长期陪伴用户的 Codex
> 小伙伴。它不是把星盘报告发给模型，也不是用一段泛化提示词直接生一只宠物。

Vedic Companion IP 是一个可安装的 Codex Skill。它先在本地完成确定性的
chart computation，再将结果收敛为三个不包含个人信息的视觉候选。用户选择
其中一个角色后，官方 `hatch-pet` 才会把它制作成可安装、可动的 Codex pet。

```text
private intake
  -> local chart computation
  -> three visual-safe IP candidates
  -> three official Hatch canonical bases
  -> three text-bearing Character Bibles
  -> user chooses one
  -> selected Hatch animation, QA, and Codex pet package
```

## 用户会经历什么

1. 用户只在本地提供出生信息。系统计算，但不把原始输入、坐标、报告或推理
   发送到图像服务。
2. 用户看到三只不同方向的角色，而不是一个被算法替他决定的“唯一答案”。
3. 每个方向都有来自同一 Hatch canonical base 的 Character Bible，用于理解
   角色的轮廓、材质、动作和不可改变的识别特征。
4. 用户确认一只后，只有这一只进入九状态动画、图集、视觉 QA 和安装包。

这条顺序是产品约束：`hatch-pet` 拥有角色身份、动画和最终包；图像生成只为
同一角色制作文字化的 Character Bible，不能反过来重定义宠物。

整个过程保存在一个本地 session 中。它不是云端账号，也不是黑箱队列：session
把每个可公开检查的阶段写成可验证状态，并把私有计算单独留在 owner-only 目录里。
因此，用户可以暂停在三个角色设计板处思考，也可以在选定后继续；任何试图跳过
Hatch base、替换已选素材或把外部图片塞回流程的操作都会被拒绝。

## 两条边界

| 本地私有层 | 可用于视觉生产的公开层 |
| --- | --- |
| 出生日期、时间、地点、坐标、时区 | 三个设计安全的候选角色 |
| 原始 chart report 与推理 | Hatch canonical base |
| 候选的私有证据账本 | Character Bible、选择记录、QA、动画包 |

私有层永远不进入图像提示词、Skill 产物、Git 仓库或安装包。公开层会通过
schema、关键词扫描、SHA-256 锁定和状态门进行检查。

## 安装到 Codex

前提：本机已有 Codex、官方 `hatch-pet` Skill、系统 `imagegen` Skill，以及
可用的本地 Vedic runtime。图像服务凭据只放在当前进程环境变量中。

```bash
git clone https://github.com/hazelian0619/vedic-companion-ip.git
cd vedic-companion-ip
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD/skill" "$HOME/.codex/skills/vedic-companion-ip"
```

链接故意不会覆盖同名已安装 Skill；如需更新，先检查并移除旧链接，再重新创建。

安装后，在 Codex 中直接描述需求即可，例如：

```text
根据我的出生信息做三个可选择的长期陪伴宠物方向；本地计算，先给我看角色设计板，
我选定后再制作 Codex pet。
```

完整的运行时命令、输入契约和失败处理在
[skill/SKILL.md](skill/SKILL.md) 中。这个文件是自动化执行的唯一操作手册。

## 一次完整体验的节奏

先在本地计算并得到三个候选方向。系统为三个方向分别准备官方 Hatch run，先形成
可动画的角色 base；接着才用同一张 base 生成带文字、材质、比例和动作说明的
Character Bible。用户只需要在这三份设计板中做一次选择。选择记录会锁定对应的
base 与设计板，后续九状态动画无法悄悄换成另一只角色。

这也是它比“一次性生一张宠物图”更适合长期陪伴的原因：每一层都在保护同一个
角色身份，而不是在每次生成时重新猜测它应该长什么样。

## 为什么不是一次生图

角色一旦进入动画，最重要的是稳定，而不是某一张图的瞬间好看。因此每一步都有
明确的责任边界：

- **Candidate compiler**：从本地事实得到恰好三个视觉安全方向。
- **Hatch base**：为每个方向建立唯一、可动画的角色身份。
- **Base acceptance**：只登记三个 session 内、base job 已完成且经过人工视觉确认的
  canonical base；这一步是 Hatch 与 Character Bible 的明确交接。
- **Character Bible**：使用同一个 base 呈现专业版式的身份、比例、材质和动作
  说明。版式来自现代信息栅格、藏品标注与角色设定集语言，但不固定产品色彩、材质
  或字体。
- **Character Bible QA**：确认身份一致、文字可读、版面完整后，才允许候选进入选择。
- **Selected Hatch run**：锁定被选中 base 和 board 的哈希，拒绝旧分支或被改动素材。
- **Delivery QA**：九个状态预览、帧检查、图集验证和显式视觉验收必须全部通过。

## 开发与验证

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skill
```

仓库只保存可执行的生产源码、Skill、测试和说明。所有真实用户资料、会话产物、
历史图像、报告、私有证据和凭据均被 Git 忽略，不能作为提交内容。

## 当前边界

本仓库交付的是可复用的工作流与质量门，不附带任何真实用户的宠物、星盘、图像或
服务密钥。用户选择角色是刻意保留的人为决定；系统不会替用户从三个方向中擅自选出
最终陪伴者。
