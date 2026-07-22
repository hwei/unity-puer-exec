[English](README.md) | [中文](README.zh-CN.md)

[![OpenUPM](https://img.shields.io/npm/v/com.txcombo.unity-puer-exec?label=openupm&registry_uri=https://package.openupm.com)](https://openupm.com/packages/com.txcombo.unity-puer-exec/)
[![Agentic AI Project](https://img.shields.io/badge/Agentic%20AI-Project-0a7ea4)](https://github.com/hwei/unity-puer-exec)

# Unity Puer Exec

Unity 包 + CLI，让 AI Agent 通过 [PuerTS](https://github.com/Tencent/puerts) host **完全自主地**驱动 Unity 工作流。

Agent 自行启动 Editor、编写代码、处理编译错误、解除阻塞对话框、验证结果——全程无需人类在 Editor 前操作。

## 为什么选择 unity-puer-exec？

大多数 Unity 自动化工具都假设人类已经打开了 Editor，并且随时在旁边解除阻塞。`unity-puer-exec` 为另一种场景而生：**Agent 独自面对项目**：

- **从零到结果的会话生命周期。** CLI 自动定位项目所需的 Unity 版本并启动，等待就绪，恢复崩溃的会话，防止重复启动，并自动解除模态阻塞（Safe Mode、保存场景对话框等）。全程无需人类介入。
- **结构化编译错误闭环。** `exec --refresh-before-exec` 完整包裹 refresh → 等待编译稳定 → 执行 的周期。编译失败时返回机器可读的诊断信息（exit code 23 + 内联错误列表），Agent 可以直接修代码重试，无需解析日志。
- **多项目并行操作。** 动态端口分配、per-project 会话产物、launch claim 机制，让一个（或多个）Agent 可以同时驱动多个 Unity 项目而互不干扰。
- **基于 PuerTS 的即时执行。** 脚本通过 PuerTS JavaScript 桥接执行——解释执行，无编译步骤，无外部编译器依赖。如果你的项目已经在使用 PuerTS，则无需安装任何额外依赖。

### 真实场景：资源管线自动化

这正是 `unity-puer-exec` 诞生的工作流。在一次 Agent 会话中，人类完全不碰 Editor：

1. Agent 调查美术资源，理解其结构特点。
2. 编写资源管线的 C# 处理代码。
3. 通过 CLI 触发编译，失败时读取结构化诊断信息。
4. 修复错误、重新编译、触发打包。
5. 检查构建产出，验证正确性后汇报结果。

人类只负责描述意图和评审结果，中间的一切属于 Agent。

### 与同类方案对比

| 能力 | unity-puer-exec | [Unity CLI](https://unity.com/blog/meet-the-unity-cli)（官方） | [unity-cli-loop](https://github.com/hatayama/unity-cli-loop) | [UniCli](https://github.com/yucchiy/UniCli) | [Puerts Agent](https://github.com/Tencent/puerts)（Puerts.AI） |
|---|:-:|:-:|:-:|:-:|:-:|
| CLI 自主启动并恢复 Editor | 是 | 部分（`unity open`） | 部分（`uloop launch`） | 否 | 否 |
| 结构化编译错误重试闭环 | 是 | 否 | 部分（compile + get-logs） | 否 | 否 |
| 自动解除模态阻塞（Safe Mode 等） | 是 | 否 | 否 | 否 | 否 |
| 会话恢复与防重复启动 | 是 | 否 | 基础 | 否 | 否 |
| 多项目并行（一等公民） | 是 | 否 | 基础（端口参数） | 否 | 否 |
| 动态代码执行 | JS via PuerTS（解释执行，即时） | C# eval（pipeline 包，实验性） | C# via Roslyn（编译为 DLL） | C# eval | JS via PuerTS |
| 额外运行时依赖 | 无（自包含 .exe） | 无 | Node.js 22+ + Unity 内置 Roslyn | 无 | 无 |
| 最低 Unity 版本 | 2022.3 | 6.0 LTS | 2022.3 | 2022.3 | 2022.3 |
| PlayMode 输入模拟 / 录制 | 否 | 否 | 是 | 否 | 否 |
| 截图 / 多模态反馈 | 可通过 JS 实现 | 否 | 是 | 是 | 是 |

与最接近替代方案的关键差异：

- **vs unity-cli-loop**：其 `execute-dynamic-code` 通过 Unity 内置 Roslyn（`csc.dll` / `Microsoft.CodeAnalysis.CSharp.dll`）将 C# 编译为 DLL，并维护一个热的编译器工作进程——每次执行成本更高，活动部件更多。`unity-puer-exec` 通过 PuerTS 解释执行 JavaScript，无编译步骤。对于已经使用 PuerTS 的项目，依赖 footprint 显著更小：无需 Roslyn 路径解析、无编译器进程管理、无 Node.js 运行时。
- **vs Unity CLI（官方）**：方向正确，但连接运行中 Editor 的 `com.unity.pipeline` 包仍为实验性，且要求 Unity 6.0 LTS+。尚无编译错误闭环、阻塞恢复和多项目管理。
- **vs UniCli / Puerts Agent**：两者都要求人类预先打开 Editor，均不管理会话、编译错误或模态阻塞。

## Design Philosophy

`unity-puer-exec` 有意保持精简。

- 接口是 CLI-native 的，因此 Agent 可以通过 `--help` 自行发现能力、选择命令，并在遇到非成功状态时做分支处理，而不是依赖仓库外很难沉淀的隐性知识。
- 核心能力面保持最小化：围绕 ready、exec、observe、recover 提供少量基础原语，而不是堆很多一次性的高层命令。
- 每个非成功响应都携带 `next_steps` 和 `situation` 引导——Agent 可以直接执行的具体后续命令。
- 重复出现的高层工作流应该沉淀成 skill。当你和 Agent 都发现某个模式反复出现时，就该把它固化下来，而不是每次都重新解释一遍。

## Requirements

- Unity 2022.3 或更高版本
- [com.tencent.puerts.core](https://github.com/Tencent/puerts) 3.0.0

## Installation

请从 **OpenUPM**（https://package.openupm.com，开源 Unity 包注册中心）安装。**不要**将本仓库 clone 到你的项目中——仓库是开发源码，OpenUPM 上的包才是构建后的版本化分发产物。

把下面这段提示词直接交给你的 Agent：

```text
请把 Unity 包 com.txcombo.unity-puer-exec 从 OpenUPM（registry: https://package.openupm.com）安装到我的 Unity 项目里。如果你不能自动定位项目，请向我询问项目路径。如果 OpenUPM registry 无法访问，请向我询问应使用的代理或镜像配置，例如 HTTP_PROXY 和 HTTPS_PROXY。
```

包名是 `com.txcombo.unity-puer-exec`。

## Usage

CLI 二进制会随包一起发布，位于包内的 `CLI~/unity-puer-exec.exe`。你的 Agent 应该通过在 Unity 项目中搜索包名 `com.txcombo.unity-puer-exec` 来定位它，而不是把完整的 `Library/PackageCache/...@<version>/` 路径硬编码进流程里。

建议先让 Agent 通过 `--help` 和各子命令帮助自行发现 CLI 的工作流，而不是凭记忆假设命令语法。

示例提示词：简单场景操作

```text
请使用 unity-puer-exec 在当前打开的 Unity 场景里添加一个 Sphere。先通过 help 自行发现合适的 CLI 工作流，再在已安装的包里找到 unity-puer-exec 二进制，执行修改，并告诉我你改了什么。
```

示例提示词：改代码、编译并验证

```text
请使用 unity-puer-exec 新增一个 Unity Editor 菜单命令，用来输出当前选中资源的 GUID。先通过 help 了解 CLI 工作流，再在 com.txcombo.unity-puer-exec 包里找到二进制，完成代码修改，处理过程中遇到的编译周期，执行验证流程，并告诉我验证结果。
```

## Solidifying Skills

用过几次之后，通常会出现一个明显模式：Agent 会一遍遍重新发现同样的 `unity-puer-exec` 工作流，而那些 JavaScript 片段也开始显得可以复用。

这时就应该把这套重复流程沉淀成一个 skill，而不是把每次会话都当成一次全新发明。

可以用下面这段 opening prompt 开始和 Agent 讨论设计：

```text
我们刚才跑过的 unity-puer-exec 命令以后还会经常用到，那些 JS 脚本也可能值得复用。你能不能想办法把这些整理成一个 skill？我们先讨论设计。
```

## 维护者 Release 准备

维护者 release 准备流程及本地 `tools/release_openupm.py` helper 的用法，参见 [openspec/specs/openupm-release-pipeline/how-to-run.md](openspec/specs/openupm-release-pipeline/how-to-run.md)。

## License

MIT

英文版：[README.md](README.md)
