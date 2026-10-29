# NexHome 滨融府友邻加强版

## 项目简介

一个基于 NexHome 官方 Home Assistant 组件改进、专为滨融府大平层住户打造的社区增强版本。

**正式发布版本 [v0.1.0](https://github.com/Doggiekong/nexhome-neighbor-edition/releases/tag/v0.1.0)；上游基础为官方 v1.1.16。** 本项目不是 NexHome 官方新版，也不代表官方团队或官方合作关系。

## 主要改善

| 原来可能遇到的问题 | 友邻加强版的改善 |
|---|---|
| 中控异常时一直等待，拖慢 Home Assistant | 为等待设置明确上限，避免请求长期占住系统 |
| 灯、风扇、空调、窗帘都像普通开关 | 新接入时尽量显示为合适类型；已有用户优先保留原来的控制入口和设置 |
| 要自己找中控 IP、IOTID 或 SN | 已验证的典型单中控家庭网络可自动查找，最后由您确认 |
| 升级后担心名字、隐藏、房间或自动化被打乱 | 优先保留用户设置；不能确认安全时停止，不删除重建 |
| 文件装好了，却不知道怎样找到设备 | 继续进入 HA 原生连接，直到设备可见、首次控制读回成功，并确认知道控制入口 |

有限现场验证不代表所有型号、网络和长期使用场景都已覆盖。

## 适合谁

- 滨融府大平层住户，使用开发商交付的 NexHome 智能家居系统。
- 设备组合与当前实测大平层环境相近。
- 已经有正常可用的 Home Assistant，并有管理员权限。
- 希望将 NexHome 更稳定地接入 Home Assistant，包括已有官方组件的用户。

当前设备识别、兼容性和现场验证主要基于滨融府大平层实际交付的 NexHome 中控与设备组合。其他户型或不同设备组合可能也能使用，但目前不作为完整已验证范围。

本项目的边界从 **已经有 Home Assistant** 开始，不负责替您部署 HA、NAS、PVE、Docker Host、路由器或家庭公网。

## 安装前置条件

- 已经能正常打开 Home Assistant，并以管理员身份登录。
- Home Assistant 与 NexHome 中控可以在家庭网络中通信。
- 建议先保留一次 HA 备份。
- 手机端使用官方 Home Assistant App。

典型单中控环境通常不需要预先知道 Hub IP、IOTID 或 SN。

## 开始安装

**两种方式只需要选择一种。** 不必预先复制源码或准备维护者环境变量。

### Home Assistant OS

**[添加到 Home Assistant](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FDoggiekong%2Fnexhome-neighbor-edition)** → [HAOS 详细教程](docs/安装与使用指南.md#route-a)

### NAS / Docker / Container / Linux

**[Terminal 安装](docs/安装与使用指南.md#route-b)** → 一条完整命令、自动检测和方向键菜单。

安装包从本项目的固定 [v0.1.0 Release](https://github.com/Doggiekong/nexhome-neighbor-edition/releases/tag/v0.1.0) 取得并校验。两条路线都进入同一个安装核心；已有安装优先保留，不能安全确认来源时停止。当前主要实测平台为 amd64 HAOS 和 Linux Docker，其他平台不冒称已完整验证。

## 安全和隐私

设备发现和控制主要在自己的 HA 与家庭网络中完成，不默认上传设备状态或家庭使用历史。无需把 HA 密码、Wi-Fi 密码或中控编号发给维护者。

先检查和备份；已有安装保留名称、隐藏、禁用、房间和引用，不自动整理 Dashboard、自动化或家庭成员。遇到来源冲突或无法安全恢复的情况会停止，不能把“换回代码”等同于恢复全部 HA 设置。项目不自动修改路由器或开放公网。

## 常见问题 Q&A

**这是官方软件吗？** 不是，是以官方组件为基础的住户社区增强版本。

**两条安装路线都要做吗？** 不用。HAOS 选 App，已验证的 Linux Docker 环境选 Terminal；连接和首次使用步骤相同。

**要手填 IP、IOTID 或 SN 吗？** 已验证的典型单中控网络通常不用。多中控需选择，网络隔离需单独检查。

**已有自动化会被重建吗？** 正常升级优先沿用原身份和设置，不删除重建；不能保证任何第三方环境都零风险，请先备份。

**没有 Home Assistant 可以用吗？** 需要先有正常可用的 HA；本项目不负责安装 HA 主机。

**需要 HACS 吗？** 不是必需。同一安装只由一个工具负责更新；已有 HACS 来源要按受支持流程交接。

**为什么有的窗帘显示“未知”？** 部分原设备只支持开、关、停，没有位置反馈。仍可明确操作，不应伪造百分比。

**现在已经公开发布了吗？** 是，正式版本为 [v0.1.0](https://github.com/Doggiekong/nexhome-neighbor-edition/releases/tag/v0.1.0)，仓库和 Release assets 可公开访问。HACS 发布尚未进行；不要把公开 GitHub 仓库等同于已经上架 HACS。

## 致谢

### NexHome 官方

感谢 [NexHome 官方 Home Assistant integration](https://github.com/nexhome-org/nexhome-homeassistant-component) 提供原始开发基础。本项目基于 **v1.1.16** 改进，保留上游来源与贡献说明。

### 邻居 Neil

**特别感谢邻居 Neil，他的 NexHome Home Assistant 项目为本项目提供了不少参考和启发。**

技术参考项目：[Neil-UWA/nexhome-homeassistant-component](https://github.com/Neil-UWA/nexhome-homeassistant-component)

## 技术说明

普通住户可跳过本节。

- [当前发布状态与 main 基线](docs/rc-status.md)
- [安装与使用指南](docs/安装与使用指南.md) · [来源与致谢说明](NOTICE.md)
- [独立版本体系](docs/product-versioning.md)：产品 0.1.0 与上游 1.1.16 分开。
- [架构](docs/architecture.md) · [隐私](docs/privacy-and-safety.md) · [兼容矩阵](docs/device-compatibility.md)
- [身份与迁移](docs/identity-and-migration.md)：USER INTENT WINS。
- [Stage E 历史验证](docs/phase2-stagee-validation.md) · [Stage D.6](docs/phase2-staged6.md) · [Stage C](docs/phase2-stagec.md) · [Installer 核心](docs/phase2-installer.md)

技术实现包括明确 HTTP 超时、共享串行分片轮询、控制公平排队、待确认状态与真实读回、旧查询保护，以及必需/可选属性区分。App/Terminal 使用同一固定包，来源不明和渠道冲突不强行覆盖，回滚与 RECOVERY_REQUIRED 分开说明。

License / publication authorization: **USER MANAGED / OUTSIDE TECHNICAL GATE**。由用户负责，不作为技术 Gate 或发布阻断；不表示任何官方授权。历史报告保持原文，当前状态以 [发布状态](docs/rc-status.md) 为准。
