# Vedic Companion IP

把只在本地计算的出生信息，转化成一只可以长期陪伴、可动画、可安装的 Codex pet。

它不是把星盘报告交给图像模型，也不是用一段泛化提示词随机生成一个玩具角色。这个仓库把「身份探索」和「宠物生产」分开：先让人选择真正想长期相处的角色，再让 Hatch 把它制作成可动的宠物。

```text
private intake
  -> local deterministic chart computation
  -> 3 visual-safe art-direction contracts
  -> 3 non-canonical imagev2 heroes
  -> 3 text-bearing imagev2 Identity Boards
  -> user chooses one board
  -> 1 official hatch-pet canonical base
  -> Hatch rows, atlas, QA, and Codex pet package
```

## 用户实际会看到什么

用户只会看到三张 **Identity Board**。每张都是一个完整的身份探索图：主角色、局部材质、互动姿态、简短文字标注，以及不可丢失的识别规则。

每张板内有一张同源的 hero，但 hero 只是给 Hatch 使用的内部身份参考，不会变成另一个用户步骤。用户选定一张板后，只有这一个 hero 会进入 Hatch。Hatch 生成 canonical base、九种状态、图集和安装包。

这意味着：

- 不会为了让用户选择而先生产三只可动画宠物。
- 不会在 Hatch 之后再额外生成一张“最终 Character Bible”来重新解释角色。
- 不会把固定的色盘、模板卡片或中心指示灯当成角色身份。
- 每个方向都必须有不同的身体语法、亲近用户的姿态、可触摸细节，以及明确禁止的泛化玩具造型。

## 为什么这样设计

旧的顺序是「三个 Hatch base -> 三张说明板 -> 选择」。问题在于 Hatch 在没有确切角色参考时容易把安全词汇收敛成对称、封闭、像消费电子的泛化玩具。

现在 imagev2 负责非 canonical 的身份探索，Hatch 只负责被选择角色的生产与动画。Hatch 仍然是最终宠物的唯一生产 owner，但它不再负责从抽象文字发明 IP。它拿到的是一张被选中、哈希锁定的 hero reference。

## 隐私边界

| 永远留在本地私有层 | 可以进入视觉生产层 |
| --- | --- |
| 出生日期、时间、地点、坐标、时区 | 三个视觉安全候选合同 |
| 原始 chart report、推理与证据账本 | 三张 Identity Board、hero、选择与 QA 哈希 |
| 服务密钥 | 被选 hero 的 Hatch base、rows、atlas、安装包 |

图像提示词不包含出生数据、坐标、报告、占星术语或私有推理。凭据只存在于调用进程的环境变量中，不写入提示、session、Git 或生成文件。

## 安装

前提：本机有 Codex、官方 `hatch-pet` Skill、系统 `imagegen` Skill，以及可用的本地 Vedic runtime。

```bash
git clone https://github.com/hazelian0619/vedic-companion-ip.git
cd vedic-companion-ip
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD/skill" "$HOME/.codex/skills/vedic-companion-ip"
```

安装后可直接对 Codex 说：

```text
根据我的出生信息做三张可选择的陪伴 IP 身份版图。本地计算，不要把我的资料发到图像模型；我选定一张后再用 hatch-pet 做成 Codex pet。
```

完整可执行命令在 [skill/SKILL.md](skill/SKILL.md)。Skill 会在用户选择前停止，不会擅自生成 Hatch base 或动画。

部分 OpenAI-compatible provider 能处理 `images.generate`，但其 SDK `images.edit` 实现不完整。此时可在显式提供 endpoint 的前提下使用 `--provider-http-fallback`。它仍调用同一 `gpt-image-2` endpoint：hero 使用 JSON generation，Identity Board 使用 hero-first multipart edit；不会改用文本重绘、不会降级模型、不会写入凭据。

## 一次完整体验

1. 本地计算出生信息，写入 owner-only `private/`。
2. 编译三个公共且安全的 art-direction contracts。
3. 每个候选先生成一个 hero，再用该 hero 生成一张带文字的 Identity Board。
4. 对每张板做视觉 QA：角色是否一致、三者是否真不同、文字是否可读、信息是否完整。
5. 用户选择一张。选择文件锁定 hero 和 board 的 SHA-256。
6. Hatch 只用该 hero 作为 reference scaffold 一个生产 run。
7. Hatch base 完成且人工确认后，`identity-lock.json` 锁定 board、hero、copy reference 和 canonical base。
8. 官方 `hatch-pet` 从同一 canonical base 生成九行状态，完成提取、图集、视觉 QA 和安装。

`session.json` 是可恢复的本地状态机，而不是云端黑箱。它拒绝跳过选择、替换已锁素材、用非 session 图片混入 Hatch，或在 base job 未完成时进入动画。

## 图像质量标准

一张合格的 Identity Board 不是“看起来像产品卡片”的拼贴。它必须同时做到：

- hero 与所有辅助视图是同一个角色，而不是同一配色的不同角色；
- 有完整身体语法和可读的互动姿态，而不只是一个颜色壳；
- 有可触摸、可记忆的实体细节；
- 字体、标签和小字真实可读，不是伪文字；
- 版面从角色形状和信息密度出发，而不强行套固定色、固定网格或产品统一模板；
- 明确避开对称 pod、壳内椭圆脸、中心按钮/状态灯、盔甲与消费电子外壳。

## 开发验证

```bash
PYTHONPATH=. pytest -q --ignore=tests/test_pipeline.py
python3 -m py_compile *.py scripts/*.py skill/*.py skill/scripts/*.py
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skill
```

真实用户资料、session 产物、生成图像和凭据均为 Git 忽略内容，不能提交。旧的三 Hatch 候选 / Character Bible 脚本仅用于读取和维护历史 session；它们不是新产品主线。
