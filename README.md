# NexHome 滨融府友邻加强版

一个基于 NexHome 官方 Home Assistant 组件改进、专为滨融府小区住户打造的社区增强版本。

它基于官方组件，主要改善稳定性、安装和使用体验。**这是住户社区版本，不是 NexHome 官方新版、官方后续版本，也不代表官方团队或官方授权。**

> 当前仍是私有开发验证版本 **0.1.0**，尚未正式发布，也未开放住户试用。下面介绍产品的使用方向；正式安装入口和命令会在分发准备完成后补齐，请勿把开发分支当作生产安装教程。

## 主要改善了什么

| 原来可能遇到的情况 | 现在的改善 |
|---|---|
| 中控异常时，组件长时间等待，甚至影响 HA 响应 | 请求有明确超时和恢复机制，中控出问题时尽量让 HA 本身保持正常 |
| 灯、风扇、空调、窗帘等被显示成普通开关 | 尽量显示为合适的设备类型；已使用的旧设备和手工设置保守处理 |
| 安装需要填写中控地址和设备编号 | 在已验证的典型滨融府单中控家庭网络里可以自动查找，通常不用填写 |
| 升级可能影响设备名称、隐藏状态、房间和自动化 | 优先保留您修改过的内容；无法安全判断时停止，不强行覆盖 |
| 安装步骤复杂 | HA OS 可使用 Home Assistant 安装助手；部分已有 HA 环境可使用一次性 Terminal 安装，两者安装同一个产品 |

以上改善已在隔离测试和有限现场中验证，不保证所有型号、网络和长期场景都已覆盖。

## 适合哪些用户

- 滨融府住户，使用开发商原配 NexHome 系统；
- 已经有一套可以正常使用的 Home Assistant；
- 希望更稳定、方便地接入设备；
- 或已经使用官方 NexHome HA 组件，想迁移到友邻加强版。

本项目从“您已经有可用的 Home Assistant”开始。不替您自动安装 Home Assistant、NAS、PVE、Docker 主机、软路由、家庭网络或公网访问。没有 HA 的住户，需要根据自己的设备环境另行选择安装方式。

## 安装前准备

至少需要：一套能正常打开的 Home Assistant、管理员权限，以及 HA 与 NexHome 中控可以互相通信的家庭网络。

**通常不需要提前知道中控 IP、IOTID 或 SN。** 自动查找依赖家庭局域网可达；多个中控或网络隔离时可能需要额外确认。

| 您的环境 | 预期安装方式 | 当前边界 |
|---|---|---|
| Home Assistant OS | 推荐 Home Assistant 安装助手（HA 应用） | amd64 测试环境已验证；正式应用来源尚未发布 |
| HA Container / NAS / Linux 等 | 一次性 Terminal 安装，完成后退出 | 当前只验证已有 Linux Docker、可写配置目录及管理员授权；其他 NAS/封装不保证支持 |

具体入口和命令在正式分发时补齐。升级前请保留自己的 HA 备份。已有 HACS 安装会先检查由谁负责更新，不能让两个工具同时替换同一份组件。

## 安装完成以后

1. 回到 Home Assistant。
2. 打开 **设置 → 设备与服务 → 添加集成 → NexHome 滨融府友邻加强版**。
3. 系统自动查找 NexHome 中控。
4. 核对并确认后完成。

典型单中控环境通常不用填写 IP、IOTID 或 SN。已有集成升级时优先沿用原条目，不要自行删除重建。安装助手只是帮助部署组件，完成后设备仍由 HA 本身管理。

## 手机怎么用

安装后，NexHome 设备就是 HA 里的普通设备。iPhone 和 Android 用户继续使用**官方 Home Assistant App**，连接自己的 HA。友邻加强版不需要单独的手机 App。

## 人在家外怎么用

先让 Home Assistant 本身支持远程访问，就可以在外使用。常见选择包括 Home Assistant Cloud、自己的域名加 HTTPS、NAS 反向代理、Tailscale / WireGuard / VPN、Cloudflare Tunnel，或您自己的方案。

不同家庭网络差异很大，这部分不属于友邻加强版的自动配置范围；本项目不会替您改路由器或打开公网入口。

## 安全和隐私

- 设备发现和控制主要发生在您自己的 HA 和家庭网络中。
- 不默认上传灯光、空调、窗帘状态，也不默认上传家庭使用记录或自动化历史。
- 不要求您把 HA 密码、Wi-Fi 密码或 NexHome SN/IOTID 发给维护者。
- 安装前先检查、备份；安装失败时尽量恢复。恢复无法安全完成时会明确停止，不能保证所有变化都能自动还原。
- 您改过的名称、隐藏状态、房间和自动化优先保留；无法判断时不强行覆盖。
- 不自动修改 Dashboard、Area、Automation、家庭成员、路由器或家庭网络。

安装需要您在自己的环境中授权管理员权限。不要把密码贴到聊天、工单或公开日志。软件获取、HA 自身更新及您选择的远程访问服务可能使用互联网；这不等于本项目上传设备使用数据。

## 常见问题

**这是 NexHome 官方软件吗？** 不是。这是基于官方 Home Assistant 组件改进的滨融府住户社区版本。

**需要填写 NexHome IP / IOTID 吗？** 典型单中控网络通常不需要，会自动查找；网络隔离和多中控环境仍有边界。

**会把现在的自动化弄坏吗？** 安装器优先保留已有设置，不能确认安全时停止。任何第三方软件升级都建议先保留 HA 备份，不能承诺绝无风险。

**没有 Home Assistant 能直接用吗？** 不能，起点是已经有可用的 HA。

**需要单独手机 App 吗？** 不需要，继续使用官方 Home Assistant App。

**人在外面能用吗？** 只要您的 HA 本身已支持远程访问即可；本项目不自动配置远程访问。

**HACS 是必须的吗？** 不是。可按环境选择安装助手或一次性 Terminal；目前尚无公开安装包。

---

# 技术说明

以下内容主要面向 Home Assistant 高级用户、开发者和维护人员。普通用户可以跳过。

## 独立版本与上游基线

| 信息 | 当前值 |
|---|---|
| Technical name | NEXhome Neighbor Edition |
| Product ID | nexhome-neighbor-edition |
| Product version | **0.1.0**（未发布开发验证状态） |
| Upstream base | NexHome official integration **v1.1.16** |
| Version scheme | neighbor-independent-v1 |
| Build / commit | 固定 artifact 的 revision；源码对应 Git commit |

0.1.0 是独立产品线起点，不是官方 1.1.16 的降级版或下一版。以后产品按 0.1.x / 0.2.x / 1.0.0 演进，上游基线独立记录。早期内部 Candidate 编号 1.1.17.dev1–dev4 只保留作开发历史和验证证据，不再递增为产品版本。版本体系变更不等于发布。

## 可靠性与设备语义

使用异步 HTTP，设置 connect/read/total timeout；网关共享 scheduler/coordinator、串行有界请求与属性分片。控制优先但给轮询机会，避免饥饿；同设备命令有序。pending 是短期待确认意图，authoritative HTTP readback 才是最终依据；拒绝命令前旧查询覆盖新意图。freshness 按属性有效回包计时，失败不刷新。UDP1912 hint 用于触发读回，不把命令字段当真实状态。

NSDP 广播可在已验证的单 Hub 网络里获取地址与本地认证编号；跨广播域/VLAN、多 Hub、其他固件未全面验证。semantic light/fan/climate/cover 按型号能力生成。climate 区分必需与可选属性；cover 无真实位置时不伪造百分比或开合状态。

## 身份、升级与恢复

USER INTENT WINS：保留 config entry、entity/device identity、用户 rename/hidden/disabled/Area 及引用。旧 switch 保留兼容，明确手工 wrapper 或用户隐藏时保守跳过 semantic duplicate；不扫描重写所有模板。

一个安装只有一个更新 owner：OFFICIAL_HACS、COMMUNITY_HACS 或 NEIGHBOR_INSTALLER。MANUAL_UNKNOWN 默认停止；HACS adapter 仅识别已验证格式，渠道切换需要正常 HACS UI 与显式确认。Installer 使用 preview、backup、持久 transaction、health check；可逆代码变化与 forward-only registry migration 区别处理，必要时 RECOVERY_REQUIRED，不能把代码恢复称为全量自动回滚。

App 与 Terminal 使用同一固定 artifact 和安装核心。App 通过管理员 Ingress，无公开端口、Docker socket 或关闭保护模式。Terminal 只在明确的现有 Linux Docker 配置 bind 上使用本地 Unix API；需要宿主权限与临时 HA 授权，完成后退出。首次配置统一回到 HA native config flow。

## 验证与文档

Stage D 实际验证包括 official-like migration、fresh App/Terminal、一致的部署文件与 ownership、NO_OP、App 停止/卸载独立性。该轮 runtime 为早期内部 Candidate dev4；新 0.1.0 的身份/文案与版本迁移在 D.5 本地全量回归，**未重新部署 VM 或复测真实设备**。有限真实设备基线仍是内部 dev3，不将历史 PASS 当成本轮重新执行。

- [版本体系与迁移规则](docs/product-versioning.md) · [Stage D.5 本轮验证](docs/phase2-staged5-validation.md)
- [隐私与安全](docs/privacy-and-safety.md) · [架构](docs/architecture.md) · [安装流程](docs/installation-flow.md)
- [设备兼容矩阵](docs/device-compatibility.md) · [身份与迁移](docs/identity-and-migration.md)
- [Stage A](docs/phase2-installer.md) · [Stage B](docs/phase2-stageb.md) · [Stage C](docs/phase2-stagec.md)
- [Stage D 入口](docs/phase2-staged-entry-decision.md) · [Stage D 验证](docs/phase2-staged-validation.md)
- [Phase 1 验证](docs/phase1-validation.md) · [上游逐文件对照](docs/upstream-changes.md)

项目仍 PRIVATE，无 Release/HACS/Beta/Pilot。HA2026.10.2/amd64 是当前隔离生命周期基线；物理手机、其他平台、多户长期运行、正式分发尚未验收。

## Credits / Upstream

感谢 [NexHome 官方 Home Assistant integration](https://github.com/nexhome-org/nexhome-homeassistant-component)。本项目以上游 v1.1.16、commit `bfcc161d7287770651113207cab511f848766fdb` 为基线进行增强和重组。

保留上游来源与原始项目贡献声明；不声称来自官方团队或已获官方授权。当前仓库没有独立 LICENSE 文件，不能据此推定上游或重组代码已有某种开源许可证；后续分发前仍需核实版权/许可，未擅自新增或改写许可。详见上游对照文档。
