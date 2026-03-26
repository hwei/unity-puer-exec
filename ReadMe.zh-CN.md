[English](ReadMe.md) | [中文](ReadMe.zh-CN.md)

[![OpenUPM](https://img.shields.io/npm/v/com.txcombo.unity-puer-exec?label=openupm&registry_uri=https://package.openupm.com)](https://openupm.com/packages/com.txcombo.unity-puer-exec/)
[![Agentic AI Project](https://img.shields.io/badge/Agentic%20AI-Project-0a7ea4)](https://github.com/hwei/unity-puer-exec)

# Unity Puer Exec

这是一个 Unity 包和 CLI，用于让 AI Agent 通过 [PuerTS](https://github.com/Tencent/puerts) host 驱动 Unity 工作流。

## Vision

目标状态很直接：由人描述意图，由 AI Agent 执行 Unity 工作。

这意味着，默认工作方式不再是人类反复点击 Unity Editor、不再是每次迭代都手动驱动 IDE，也不再是那种“先复制这段脚本，再运行那个工具”的脆弱流程。`unity-puer-exec` 的存在，就是为了让 Agent 能通过一个 CLI-native 的接口操作 Unity，让人把注意力放在意图、评审和方向上。

## Design Philosophy

`unity-puer-exec` 有意保持精简。

- 接口是 CLI-native 的，因此 Agent 可以通过 `--help` 自行发现能力、选择命令，并在遇到非成功状态时做分支处理，而不是依赖仓库外很难沉淀的隐性知识。
- 核心能力面保持最小化：围绕 ready、exec、observe、recover 提供少量基础原语，而不是堆很多一次性的高层命令。
- 重复出现的高层工作流应该沉淀成 skill。当你和 Agent 都发现某个模式反复出现时，就该把它固化下来，而不是每次都重新解释一遍。

## Requirements

- Unity 2022.3 或更高版本
- [com.tencent.puerts.core](https://github.com/Tencent/puerts) 3.0.0

## Installation

把下面这段提示词直接交给你的 Agent：

```text
请把 Unity 包 com.txcombo.unity-puer-exec 从 OpenUPM（registry: https://package.openupm.com）安装到我的 Unity 项目里。如果你不能自动定位项目，请向我询问项目路径。
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

## License

MIT

英文版：[ReadMe.md](ReadMe.md)
