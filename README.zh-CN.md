[English](README.md) · [简体中文](README.zh-CN.md)

<p align="center">
  <img src="docs/assets/ideck/icon.png" width="156" alt="iDeck">
</p>
<h1 align="center">iDeck</h1>
<p align="center"><strong>iDeck brings the SteamOS experience to iOS</strong><br>让你的 iPhone，也有掌机的打开方式。</p>
<p align="center">
  <a href="https://discord.gg/aQdsaJyTM"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fdiscord.com%2Fapi%2Finvites%2FaQdsaJyTM%3Fwith_counts%3Dtrue&query=%24.approximate_member_count&suffix=%20members&label=Discord&logo=discord&logoColor=white&color=5865F2&style=for-the-badge" alt="加入 iDeck Discord 社区"></a>
</p>

把手柄接上，打开 Steam 游戏库，给积灰的游戏一个住进兜里的机会。
iDeck 通过 **Madeira、Wine、FEX 和 Metal**，在 iPhone / iPad 本地运行
Valve 真正的 Windows Steam Big Picture，以及部分兼容的 PC 游戏，无需从电脑串流。

产品方向受到 [DroidDeck](https://github.com/Droid-Deck/DroidDeck) 启发，
运行基础来自 [Will Faust 的 Madeira](https://github.com/willfaust/Madeira)。

> **SteamOS 的体验，iOS 的底子。** 这里运行的是 Windows Steam 的大屏幕模式，
> 并非安装 Linux SteamOS，也不是把所有游戏变成 ARM 原生 iOS App。

<p align="center">
  <img src="docs/assets/ideck/demo-landscape-ccw90-1.5x.gif" width="831" alt="iPhone 本地启动 Steam 与 PC 游戏的演示，1.5 倍速">
  <br><sub>真机演示 · 1.5 倍速 · 实验版本</sub>
</p>

## 安装 Alpha，一起测试

当前最新实验预发布为 **[v0.1.3-alpha.5 · Build 143](https://github.com/kuscholar/iDeck/releases/tag/v0.1.3-alpha.5)**。
从该版本下载 IPA 和 `SHA256SUMS`，同页提供对应源码、许可证和重链接材料。
IPA 需要使用自己的开发签名后侧载。

> **已知问题：第三次退出游戏后，Steam 仍可能卡住。** 测试 iPhone 上的 Steam
> 菜单可用、浏览更流畅，Hot Roads 能三次进入并退出，但第三次返回后 Steam 卡住。
> 这是供测试的预发布版，不代表可以长期稳定游玩。

本次64位 Steam 实测使用预先准备的独立 Steam64／CEF 环境。IPA 不附带 Steam
文件或已登录配置，**尚未验证全新设备上的64位 Steam 可以一键配置成功**。
具体证据与限制见 [Build 143 测试记录](https://github.com/kuscholar/iDeck/blob/v0.1.3-alpha.5/docs/release/BUILD143_RESULTS.md)。

1. **下载并校验。** 对照 `SHA256SUMS` 检查 IPA 的 SHA-256。Mac 可运行
   `shasum -a 256 下载的文件.ipa`。
2. **自己签名并侧载。** 可使用 [Sideloadly](https://sideloadly.io/) 或
   [AltStore Classic](https://faq.altstore.io/altstore-classic/your-altstore)，
   按工具的官方流程使用自己的 Apple ID。普通免费开发签名也是一种选择，需遵守
   工具和账号的安装数量、有效期及续签限制。维护者不需要你的 Apple 密码。
   **保留 `MadeiraJITHelper.appex` 扩展并签名所有嵌套代码**，App 与扩展的标识符、
   开发描述文件必须匹配；JIT 需要允许调试的 `get-task-allow` 权限。
   这些工具是安装选项，并非已经逐一验证的兼容名单。
3. **信任并打开。** 连接设备并完成“信任此电脑”、开发者模式或开发者信任等系统提示
   （如有）。升级前备份存档；卸载 App 可能同时删除本地 Steam 数据、游戏和存档。
4. **准备 Steam 与 JIT。** 按下方流程逐项完成。IPA 包含本地运行时，
   **不包含 Steam/CEF 客户端、游戏或已登录的 Steam 账号**。安装成功不等于 JIT 已启用。
5. **分阶段测试。** 启动器检查 → 进入真正的 Steam 并自行完成 Steam Guard →
   浏览 Library → 启动一个兼容游戏 → 返回 Steam → 重开 iDeck 检查登录是否保留。
   分别测试触控、键盘和手柄，记录卡在哪一步。

目标为 **iOS 26+**，通过 Madeira 现有的授权配对/调试流程启用 JIT，无需越狱。
目前的真机证据来自 **iPhone 15 Pro Max（A17 Pro）**，iPad 尚未验证。
签名细节见 [IPA 安装说明（英文）](docs/INSTALL_IPA.md)，
源码准备见 [Getting started（英文）](docs/GETTING_STARTED.md)。

### JIT 提示无法确定快捷指令输出的目标 App？

旧版在更换 Bundle ID 重签后可能生成错误的回跳地址。可先关闭可选的
**Madeira JIT shortcut**，手动连接 **LocalDevVPN**，返回后点击 **Enable JIT**。
当前版本会读取实际注册的回跳信息；更新 App 后，还需从 App 内重新导入
签名快捷指令并替换旧副本。App 升级不会自动替换已导入的快捷指令。
详见 [JIT 排错说明](docs/JIT.md#shortcut-destination-errors-after-re-signing)。

## 打开 Steam 前：逐项点亮检查清单

打开当前版本的 iDeck，点击
**Check all prerequisites（检查全部前置条件）**，按从上到下的流程处理提示：

| 步骤 | 要做什么 |
| --- | --- |
| 1 · Local runtime（本地运行时） | 点击 **Prepare runtime** 初始化本地 Windows 环境，保留已有文件。 |
| 2 · Steam & browser files（Steam 与浏览器文件） | 在选中的 iDeck 环境中放入完整、架构匹配的 Windows Steam 与 CEF 文件。旧版客户端提供 **Repair Steam files** 入口，准备方法见下文。公开 IPA 不包含 Steam。 |
| 3 · Development signing（开发签名） | 使用允许调试的开发签名；若提示缺少权限，需要重新签名。 |
| 4 · JIT setup（JIT 配置） | 打开设置，使用内置 StikJIT 并配置本设备的配对文件，或使用支持的外部 StikDebug 流程。配对授权由你自行完成。 |
| 5 · Device connection（设备连接） | 按提示连接 LocalDevVPN，使本地调试连接可达；返回 iDeck 后重新检查。 |
| 6 · JIT for this session（本次会话 JIT） | 点击 **Enable JIT**，完成后返回。App 新进程需要重新启用 JIT；已有或已消耗的运行时会话可能需要重新打开 App。 |
| 7 · 32-bit address space（32位地址空间） | 如被阻止，打开 **View diagnostics** 查看。JIT 启用不代表32位子进程有足够虚拟地址空间，运行时启动时还会检查。 |

检查按钮只检查当前状态，不会自动签名、启用 JIT 或启动 Steam。
返回 App 或完成 JIT 操作后会重新检查；每一步都有状态和相应处理入口。
当前显示的检查项全部就绪后，可手动点击 **Launch Steam Big Picture**。
检查通过只说明前置条件满足，不保证登录、画面或某个游戏一定正常。

进入 Valve 自己的 Steam 窗口输入账号并自行批准 Steam Guard。登录保存、账号认证和
游戏许可由 Steam 处理。需要换账号时，使用启动器的
**Sign in / Change Steam account**，它会打开 Steam 自己的账号流程。
可在 iDeck 设置中调整自动启动；即使开启自动启动，新 App 进程仍需要 JIT。

**Steam 客户端准备仍面向技术测试者。** 旧版路径使用较旧的32位 Windows Steam。
Build 143 也包含独立的实验性 Steam64 路径，真机结果依赖
[发行记录](https://github.com/kuscholar/iDeck/blob/v0.1.3-alpha.5/docs/release/BUILD143_RESULTS.md) 所述的预先配置环境，不能视为全新设备配置已经通过，
也不要混用两套客户端环境。

旧版客户端请阅读 [源码与资源准备](docs/GETTING_STARTED.md) 和
[客户端准备记录](tests/steam-ui/README.md)，通过合法渠道获取完整软件。
客户端应位于 `wine/drive_c/Steam32BundleLab` 或 `wine/drive_c/Steam32Lab`
其中一个目录，不能拼凑不同安装的零散文件。可在 `iDeck/Steam32OfficialRepair`
放入完整兼容客户端后使用 **Repair Steam files**，详见
[Steam 修复说明](docs/IDECK_STEAM_RECOVERY.md)。不要复制他人的登录缓存，
也不要通过卸载 App 来切换环境。

## 口袋里的掌机，有些什么？

- **真正的 Big Picture。** Steam 自己的界面、账号和游戏库。
- **本地运行。** 兼容的 PC 游戏通过 Madeira 运行，无需另一台游戏电脑串流。
- **手柄、触控、虚拟按键。** 已实现相关输入集成，具体路径仍在逐项验证。
- **随手可用的悬浮按钮。** 可拖动，提供键盘、虚拟手柄、布局设置、Steam 菜单及正常退出游戏的入口。
- **保留 Steam 登录。** 登录状态留在 Steam 自己的本地环境中，iDeck 不代填或转移密码、令牌。

## 游戏支持有限，实验还在继续

**不是整个 Steam 库都能玩。** 游戏可能无法启动、画面异常、崩溃，或需要不同的设置。
请参考 [Madeira 官方 Discord](https://discord.gg/4t5mNjwCn7) 和
[Madeira GitHub 兼容性反馈](https://github.com/willfaust/Madeira/issues?q=is%3Aissue%20compatibility)。
[上游 README](https://github.com/willfaust/Madeira#readme) 没有单独发布支持游戏表；
这些是上游报告来源，并非 iDeck 的支持承诺。Madeira 能玩的游戏，也不保证经过 iDeck
大屏幕模式启动后一定正常，结果取决于设备、系统、运行时与设置。

测试 iPhone 上已观察到真实 Steam 登录、保存登录、大屏幕模式和游戏库浏览；
有 PC 游戏在本地启动，并收到测试者实际游玩的反馈。文字输入与悬浮菜单的 Steam 操作
也收到正面反馈。Build 143 的菜单和浏览有所改善，但第三次返回 Steam 后仍可能
卡住，启动和登录后跳转也仍可能卡住。蓝牙手柄、稳定返回 Steam、
长时间游玩与 iPad 仍需验证；系统枚举出手柄不等于游戏一定响应，日志出现
`BrowserReady` 也不等于界面可以操作。不承诺广泛游戏或反作弊兼容性。

进展与证据：[技术说明](docs/IDECK.md)、[POC 结果](docs/BIG_PICTURE_POC_RESULTS.md)、
[登录与跳转记录](docs/IDECK_LOGIN_TRANSITION_EVIDENCE.json)。

## 从源码构建

```sh
git clone --recurse-submodules https://github.com/kuscholar/iDeck.git
cd iDeck
```

重建某个发行版时，请检出对应 tag 并使用同版源码／重链接附件。
Build 143 的源码附件还包含其运行时使用的 FEX 组件补充源码和构建说明。

阅读 [Getting started](docs/GETTING_STARTED.md)、[构建说明](docs/BUILDING.md) 和
[JIT 设置](docs/JIT.md)。公开 Git 仓库不包含预编译运行时资源，尚非一条命令即可完成的
全新环境构建；Release 的源码、许可和重新链接材料另行提供。

Xcode 工程仍为 `app/Madeira.xcodeproj`，scheme 为 `Madeira`；App 显示为 **iDeck**，
使用蓝色 **iD** 图标。选择自己的开发团队与唯一标识符，源码默认
`com.kuscholar.ideck.steamui`，与原有 Madeira 安装和数据分开。
分发构建前请阅读 [分发要求](docs/DISTRIBUTION.md)。

## 反馈与贡献

<p align="center">
  <a href="https://discord.gg/aQdsaJyTM"><b>加入 iDeck Discord 社区</b></a>
</p>

### Discord 社区

iDeck Discord 服务器是供测试者和爱好者交流的非正式空间，用于分享体验、讨论兼容性、反馈测试发现，并偶尔获取项目更新。

iDeck 是我利用业余时间开发的个人、非商业兴趣项目。项目没有专门的支持团队，不保证回复时间，也不承诺持续维护、修复问题或开发新功能。

参与完全自愿，项目更新和回复仅在时间与兴趣允许时提供。

### 问题反馈

欢迎 [提交 Issue](https://github.com/kuscholar/iDeck/issues)，附设备、系统、构建号、
复现步骤和脱敏诊断。说明实际看到的界面，以及安装、JIT、登录、游戏库、游戏运行中的
哪一步失败。不要上传密码、令牌、Steam Guard 信息、配对文件或账号标识。
贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

**Madeira 是 iDeck 的基础。** Will Faust 与 Madeira 贡献者完成了这里所依赖的大量
运行时、图形与设备集成以及构建系统工作。iDeck 增加启动器体验、Steam UI 集成、输入、
诊断和兼容性实验，不将底层成果据为己有。

感谢 Wine、FEX-Emu、DXMT、StikJIT/StikDebug、idevice 及其他上游贡献者，
以及 [deezhizyu/madeira](https://github.com/deezhizyu/madeira) 的历史 CEF 研究。
[DroidDeck](https://github.com/Droid-Deck/DroidDeck) 启发了产品方向与 README 的清晰结构；
iDeck 使用 Madeira 的 iOS 运行时，并非 DroidDeck 的 Android/ARM64 Proton 实现。
此源码快照没有导入 DroidDeck 的代码或美术资源。

完整署名：[CREDITS.md](CREDITS.md)、[NOTICE](NOTICE)、
[第三方声明](THIRD-PARTY-NOTICES.md)、[组件来源与精确版本](docs/PROVENANCE.json)。

## 许可与商标

iDeck 自行编写的新增部分使用 **GPL-3.0-or-later**；现有
[Madeira Converter Exception](LICENSE-EXCEPTION.md) 仅适用于相应权利人授权的作品。
上游文件保留各自 LGPL、MIT、BSD、MPL 等许可及版权声明，详见 [COPYING](COPYING)。
公开源码并不自动满足所有二进制分发义务，对应源码、重新链接与专有库要求见
[docs/DISTRIBUTION.md](docs/DISTRIBUTION.md)。

Steam、SteamOS、Steam Deck 为 Valve 商标；iPhone、iPad、iOS、Metal 为 Apple 商标。
iDeck 为独立项目，不隶属于 Valve、Apple、Madeira 或 DroidDeck，也未获得其背书。


## 早期更新

[Build 67 · v0.1.3-alpha.3](https://github.com/kuscholar/iDeck/releases/tag/v0.1.3-alpha.3)
加入 Steam 文件修复、64位游戏安装识别和 JIT 重签名回调修复。
更新后需重新导入旧的 JIT 快捷指令。TLS 恢复仅经本地故障模拟验证，
不保证解决所有 VPN 或加速器问题。详见 [Steam 修复说明](docs/IDECK_STEAM_RECOVERY.md)。
