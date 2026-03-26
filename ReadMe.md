# Unity Puer Exec

Unity Editor package for driving a [Puerts](https://github.com/Tencent/puerts) host from an external CLI.

## Requirements

- Unity 2022.3 or later
- [com.tencent.puerts.core](https://github.com/Tencent/puerts) 3.0.0

## Installation

Add the package via the Unity Package Manager using the git URL:

```
https://github.com/hwei/unity-puer-exec.git?path=packages/com.txcombo.unity-puer-exec
```

In Unity: **Window > Package Manager > + > Add package from git URL...**

## Usage

`unity-puer-exec` consists of two parts that work together:

- **Unity package** (`com.txcombo.unity-puer-exec`) — installed into your Unity project, exposes a Puerts host that listens for external commands
- **CLI** (`unity-puer-exec`) — runs outside Unity, sends exec requests and observes results

Detailed usage documentation is forthcoming.

## License

MIT
