# NexHome 滨融府友邻加强版

## 项目简介

一个基于 NexHome 官方 Home Assistant 组件改进、专为滨融府小区住户打造的社区增强版本。

**产品版本 0.1.0，当前状态 RELEASE CANDIDATE；上游基础为官方 v1.1.16。** 已完成内部 Release Candidate 验证，尚未正式公开发布。本项目不是 NexHome 官方新版，也不代表官方团队或官方合作关系。

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

- 滨融府住户，使用开发商原配 NexHome。
- 已经有正常可用的 Home Assistant，并有管理员权限。
- 希望将 NexHome 更稳定地接入 Home Assistant，包括已有官方组件的用户。

本项目的边界从 **已经有 Home Assistant** 开始，不负责替您部署 HA、NAS、PVE、Docker Host、路由器或家庭公网。

## 安装前置条件

- 已经能正常打开 Home Assistant，并以管理员身份登录。
- Home Assistant 与 NexHome 中控可以在家庭网络中通信。
- 建议先保留一次 HA 备份。
- 手机端使用官方 Home Assistant App。

典型单中控环境通常不需要预先知道 Hub IP、IOTID 或 SN。

## 开始安装

**[开始安装 →《NexHome 滨融府友邻加强版：安装与使用指南》](docs/安装与使用指南.md#choose-route)**

先在 HA 的“系统信息”查看安装类型，再二选一：

| 您的 HA 类型 | 选择的入口 |
|---|---|
| Home Assistant OS | [A：App 安装](docs/安装与使用指南.md#route-a) |
| Container / Docker / NAS / Linux 等其他环境 | [B：Terminal 安装](docs/安装与使用指南.md#route-b)，先核对本机运行环境 |

**只选一种。App 和 Terminal 是两个安装入口，不是前后两个步骤。** 两者都进入同一组件、HA 原生连接、设备可见和首次控制确认流程。当前没有公开下载入口；内部固定包与本机执行环境须先由维护者准备，不要寻找第三方替代脚本。

## 安全和隐私

设备发现和控制主要在自己的 HA 与家庭网络中完成，不默认上传设备状态或家庭使用历史。无需把 HA 密码、Wi-Fi 密码或中控编号发给维护者。

先检查和备份；已有安装保留名称、隐藏、禁用、房间和引用，不自动整理 Dashboard、自动化或家庭成员。遇到来源冲突或无法安全恢复的情况会停止，不能把“换回代码”等同于恢复全部 HA 设置。项目不自动修改路由器或开放公网。

## 常见问题 Q&A

**这是官方软件吗？** 不是，是以官方组件为基础的住户社区增强版本。

**两条安装路线都要做吗？** 不用。HAOS 选 App，其他适合的已准备环境选 Terminal；连接和首次使用步骤相同。

**要手填 IP、IOTID 或 SN 吗？** 已验证的典型单中控网络通常不用。多中控需选择，网络隔离需单独检查。

**已有自动化会被重建吗？** 正常升级优先沿用原身份和设置，不删除重建；不能保证任何第三方环境都零风险，请先备份。

**没有 Home Assistant 可以用吗？** 需要先有正常可用的 HA；本项目不负责安装 HA 主机。

**需要 HACS 吗？** 不是必需。同一安装只由一个工具负责更新；已有 HACS 来源要按受支持流程交接。

**为什么有的窗帘显示“未知”？** 部分原设备只支持开、关、停，没有位置反馈。仍可明确操作，不应伪造百分比。

**现在已经公开发布了吗？** 没有。当前是 PRIVATE 仓库中的 0.1.0 Release Candidate；没有公开下载、GitHub Release、tag 或 HACS 发布。

## 致谢

### NexHome 官方

感谢 [NexHome 官方 Home Assistant integration](https://github.com/nexhome-org/nexhome-homeassistant-component) 提供原始开发基础。本项目基于 **v1.1.16** 改进，保留上游来源与贡献说明。

### 邻居 Neil

感谢邻居 Neil。[Neil-UWA/nexhome-homeassistant-component](https://github.com/Neil-UWA/nexhome-homeassistant-component) 的项目和实现思路，为部分问题分析与修改方向提供了参考和启发。本致谢不表示 Neil 为本项目背书或是共同作者，也不表示官方合作。

## 技术说明

普通住户可跳过本节。

- [当前 RC 状态与 main 基线](docs/rc-status.md)
- [安装与使用指南](docs/安装与使用指南.md) · [来源与致谢说明](NOTICE.md)
- [独立版本体系](docs/product-versioning.md)：产品 0.1.0 与上游 1.1.16 分开。
- [架构](docs/architecture.md) · [隐私](docs/privacy-and-safety.md) · [兼容矩阵](docs/device-compatibility.md)
- [身份与迁移](docs/identity-and-migration.md)：USER INTENT WINS。
- [Stage E 历史验证](docs/phase2-stagee-validation.md) · [Stage D.6](docs/phase2-staged6.md) · [Stage C](docs/phase2-stagec.md) · [Installer 核心](docs/phase2-installer.md)

技术实现包括明确 HTTP 超时、共享串行分片轮询、控制公平排队、待确认状态与真实读回、旧查询保护，以及必需/可选属性区分。App/Terminal 使用同一固定包，来源不明和渠道冲突不强行覆盖，回滚与 RECOVERY_REQUIRED 分开说明。

License / publication authorization: **USER MANAGED / OUTSIDE TECHNICAL GATE**。由用户负责，不作为技术 Gate、RC 或 main 整合阻断；不表示任何官方授权。历史报告保持原文，当前状态以 [RC 状态](docs/rc-status.md) 为准。
