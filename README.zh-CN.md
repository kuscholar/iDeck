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

当前最新实验预发布为 **[v0.1.3-alpha.6 · Build 145](https://github.com/kuscholar/iDeck/releases/tag/v0.1.3-alpha.6)**。
下载 IPA 和 `SHA256SUMS`；同一发行页附带源码、Steam64 兼容组件源码、许可证与重链接材料。
IPA 需要使用你自己的开发签名才能安装。

**少一点找按钮，多一点 Steam。** 新启动器把安装整理成四步瀑布流程，Steam64 下载和
配对按钮就在对应步骤里，完成后自动打勾。安装器从 Valve 下载并校验匹配文件，保留旧环境，
并提供修复／回退入口。

> **仍是实验版：** 第三次退出游戏回 Steam 后仍可能冻结。本版改善安装体验，
> 不代表这个稳定性问题已解决。用户反馈 Build144 的安装流程可以完成；Build145 新界面已完成
> 编译、签名、真机安装和启动，但新版完整首次配置／游戏循环尚未独立验证。
> 详见 [Build145 测试记录](docs/release/BUILD145_RESULTS.md)。

IPA 包含本地运行时和带许可证的**源码构建开源兼容组件**，不包含 Valve 的 Steam 客户端／
libcef、游戏或账号数据。Steam 由启动器下载，登录和 Steam Guard 由你在 Valve 界面中完成。
目前固定使用经过匹配的旧客户端／CEF，存在兼容性与安全限制，并不是最新 Steam／Chromium。

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
   **不包含 Valve 的 Steam 客户端／libcef、游戏或已登录账号**；请从启动器下载 Steam。
   安装成功不等于 JIT 已启用。
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

## 打开 Steam 前：四步出发

跟着高亮步骤操作即可。启动器自动检查设备，已完成的项目打勾，并滚动到下一步，
不用再去页面底部找安装按钮。

| 步骤 | 要做什么 |
| --- | --- |
| 1 · Install Steam | 点 **Install Steam64**。自动下载安装并校验 Steam／浏览器，同时准备运行时。保持 App 前台，完成后按提示完全关闭并重开。 |
| 2 · Connect LocalDevVPN | 打开 LocalDevVPN，点 Connect，再返回。已连通会自动打勾。 |
| 3 · Pair this device | 点 **Pair in iDeck**，本步骤会直接显示配对指引和验证码。iOS 设置里的配对主机仍叫 **Madeira**；通常只需配置一次。 |
| 4 · Enable JIT | 点 **Enable JIT**，完成后返回。完全关闭 App 后的新进程需要重新启用 JIT。 |

所有必要检查通过后，点 **Launch Steam Big Picture**。签名、虚拟地址／原生预留和运行时文件
仍会检查，只是不再要求用户把这些自动检查当成单独操作。**Check again** 可重新检查。
iOS26 使用配对文件导入入口；直接在设备上配对需要 iOS27。

**Advanced options（高级选项）**里保留 Steam64 校验／修复、回到原环境、其他 JIT 方法／
配对文件导入、账号切换和自动启动设置。原 `wine` 环境保留，Steam64 使用独立的 `wine-steam64`；
账号缓存、游戏和存档不会自动迁移。请通过 Steam 自己的登录／Steam Guard／换账号流程操作，
不要复制他人的登录缓存，也不要为了切换环境卸载 App。

Steam64 **不会扩大设备虚拟地址空间**。不支持的设备／签名布局仍可能失败，32位游戏或辅助进程
也仍可能受限。容量、固定版本、下载与回退说明见 [Steam64 配置与修复](docs/STEAM64_SETUP.md)。
配置检查通过，不等于所有游戏能正常运行。

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
Alpha.6 保留准确的 FEX131 补充源码／构建材料，并新增独立的 Chromium／CEF、Crashpad
兼容组件源码附件。请用 `tools/stage-steam64-compatibility.py` 准备固定哈希的开源组件，
详见 [Build145 重建记录](docs/release/BUILD145_RESULTS.md#source-and-relink-materials)。

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
