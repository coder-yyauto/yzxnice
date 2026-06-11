# CLAUDE.md

用于减少常见大语言模型编码错误的行为指南。

## 项目环境

- **框架**：NiceGUI（基于 FastAPI 的 Web UI 框架）
- **Python**：3.12
- **包管理器**：Pixi（替代 conda/mamba/pip）

### 核心命令

```bash
pixi install              # 安装环境
pixi run python main.py   # 启动 NiceGUI
pixi run pytest           # 运行测试
pixi add <pkg>            # 添加 conda 包
pixi add --pypi <pkg>     # 添加 PyPI 包
pixi shell                # 进入交互环境
```

### 环境规则

1. **所有 Python 命令必须以 `pixi run` 为前缀**
2. **禁止使用** `conda activate` / `source activate` / `pip install`（pip 在 pixi 管理的 env 里也未安装；用 `pixi add`）
   - conda 包：`pixi add <pkg>`（写入 `[dependencies]`）
   - PyPI 包：`pixi add --pypi <pkg>`（写入 `[pypi-dependencies]`，**不要**先 `pixi run pip install`）
   - 仅 dev 环境用：`pixi add --pypi <pkg> --feature dev`
   - 装完必须 `pixi install` 让 lockfile 同步；**不要**直接编辑 `pixi.toml` 后跳过 install
3. 安装新依赖前先检查 `pixi.toml` 中是否已声明
4. 配置文件：`pixi.toml`（依赖声明）、`pixi.lock`（锁文件）
5. NiceGUI 启动：`pixi run python main.py`
6. **Git 提交约定**：`pre-commit` hook 已注册（`.git/hooks/pre-commit`）。当前有 24 个 ruff + 307 个 mypy 历史 lint/type 债未清（与本会话无关，详见 `.crush/session_context.md`），所以 `git commit` 默认会被拦下。约定：
   - **开发中临时提交用 `git commit --no-verify` 绕过**（先确保 `pixi run ruff check .` 和 `pixi run ruff format .` 自己看过）
   - **推送前用 `git commit --no-verify` 或 `SKIP=ruff,mypy git commit`**
   - 长期目标：补齐类型注解、解掉 ruff 历史告警（独立工单），届时去掉 `--no-verify`
   - 手动跑 lint：`pixi run lint`、`pixi run --environment dev ruff check .`、`pixi run format`
   - 装新环境后第一次提交前要 `pre-commit install`

**权衡说明：** 本指南在谨慎与速度之间偏向于谨慎。对于琐碎任务，请自行判断。

## 1. 编码前思考

**不要假设。不要隐藏困惑。将权衡摆上台面。**

在实现之前：
- 明确陈述你的假设。如果不确定，主动询问。
- 如果存在多种解释，将它们都列出来——不要默默自行选择。
- 如果存在更简单的方法，就指出来。必要时提出反对意见。
- 如果某事不清楚，停下来。指出哪里令人困惑。然后提问。

## 2. 简洁至上

**能解决问题的最少代码。不要添加推测性的东西。**

- 不要添加超出要求范围的功能。
- 不要为一次性使用的代码创建抽象。
- 不要添加未被要求的"灵活性"或"可配置性"。
- 不要为不可能发生的场景编写错误处理逻辑。
- 如果你写了200行代码，而本可以用50行完成，请重写。

问自己一个问题："一位资深工程师会说这过于复杂了吗？"如果不是，则继续简化。

## 3. 精准修改

**只触碰你不得不碰的地方。只清理你自己制造的遗留问题。**

在编辑现有代码时：
- 不要"顺手改进"相邻的代码、注释或格式。
- 不要重构那些没有问题的部分。
- 保持与现有风格一致，即使你自己有不同偏好。
- 如果发现不相关的无用代码，可以提及它——但不要删除。

当你的修改产生了无用的残留项时：
- 移除那些因**你的**修改而变得未使用的导入、变量或函数。
- 除非被要求，否则不要移除原本就存在的无用代码。

检验标准：每一行被修改的代码，都应该能直接追溯到用户的请求。

## 4. 目标驱动执行

**定义成功标准。循环迭代直至验证通过。**

将任务转化为可验证的目标：
- "添加校验" → "先为无效输入编写测试，然后让这些测试通过"
- "修复这个Bug" → "先编写一个能复现该Bug的测试，然后让这个测试通过"
- "重构模块X" → "确保重构前后的测试全部通过"

对于多步骤任务，简要陈述执行计划：
```
1. [执行步骤] → 验证方式：[验证项]
2. [执行步骤] → 验证方式：[验证项]
3. [执行步骤] → 验证方式：[验证项]
```

强有力的成功标准能让AI自行循环迭代。弱标准（如"把它弄好"）则需要持续不断的澄清。

---

**这些指南生效时的表现是：** 代码差异中的无关变更更少，因过度设计而导致的重写更少，澄清性问题出现在实现之前，而不是出现在错误发生之后。
