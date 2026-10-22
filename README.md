# NexHome 滨融府友邻加强版

一个基于 NexHome 官方 Home Assistant 组件改进、专为滨融府小区住户打造的社区增强版本。

**不是 NexHome 官方新版、官方后续版本或官方授权产品。** 目前产品版本0.1.0，上游基线独立为官方v1.1.16；仍处于私有开发验证阶段，未正式发布、未开放住户试用。

## 开始安装

**[开始安装 → 阅读《NexHome 滨融府友邻加强版：安装与使用指南》](docs/安装与使用指南.md)**

指南覆盖安装准备、连接中控、第一次控制，以及房间、分组、场景和简单自动化。手机端使用官方 Home Assistant App。

## 主要改善

| 原来可能遇到的问题 | 友邻加强版的改善 |
|---|---|
| 中控异常时长时间等待，影响HA响应 | 明确超时、有界排队与恢复机制 |
| 灯、风扇、空调、窗帘被当作普通开关 | 按实际能力显示合适类型，保留旧用户兼容 |
| 手填中控地址和设备编号 | 已验证的典型单中控局域网里自动查找，保留确认 |
| 升级影响名称、隐藏状态、房间或自动化 | 用户设置优先，无法安全判断时停止 |
| 部署文件后不知道下一步 | 统一进入HA原生连接、找到设备和完成首次控制 |

有限现场和隔离测试不代表所有型号/网络/长期场景都已覆盖。

## 适合谁

滨融府住户、使用开发商原配NexHome、已有正常可用HA和管理员权限，希望更稳定接入，或从官方组件迁移。HA与中控需在可通信的家庭网络里，通常不用预先知道IP/IOTID/SN。

项目从“已经有可用的Home Assistant”开始，不负责安装HA/NAS/PVE/Docker主机或配置家庭网络。HA OS使用安装助手；已验证的Linux Docker环境使用一次性Terminal。具体操作和当前PRIVATE分发限制见指南。

## 安全和隐私

设备发现和控制主要在自己的HA与家庭网络中完成，不默认上传设备状态或家庭使用历史。不要求把HA密码、Wi-Fi密码或中控编号发给维护者。先检查和备份，失败尽量恢复；不能安全逆转时明确停止。保留已有名称、隐藏、禁用、房间和引用，不自动改Dashboard/Area/Automation/家庭成员/路由器。升级前仍请自行保留HA备份。

## 常见问题

**官方软件吗？** 不是，是基于官方组件的住户社区增强版本。

**要手填IP/IOTID吗？** 典型单中控网络通常不用。多中控需选择，网络隔离需排查。

**会影响已有自动化吗？** 优先保留身份和用户设置，无法判断安全时停止；不能保证所有第三方升级都零风险。

**没有HA可以用吗？** 需要先有正常可用的HA。

**HACS必须吗？** 不是；但同一安装只能由一个工具负责更新。

**现在能给邻居安装吗？** 当前无公开发行入口，不是正式发布或Pilot。

---

# 技术说明

以下面向高级用户和维护者，普通用户可跳过。

- [独立版本体系](docs/product-versioning.md)：product0.1.0与upstream1.1.16分开；dev1–dev4仅历史编号。
- [架构](docs/architecture.md) · [隐私](docs/privacy-and-safety.md) · [兼容矩阵](docs/device-compatibility.md)
- [身份与迁移](docs/identity-and-migration.md)：USER INTENT WINS，保留entry/entity/device身份、rename/hidden/disabled/Area/wrapper和引用。
- [Stage D.6 完成边界与验证](docs/phase2-staged6.md)：COMMITTED只等于DEPLOYED；CONFIGURED/CONTROL_VERIFIED/用户确认的READY分开。
- [Stage D.5](docs/phase2-staged5-validation.md) · [Stage D](docs/phase2-staged-validation.md) · [Stage C](docs/phase2-stagec.md) · [Stage B](docs/phase2-stageb.md) · [Installer核心](docs/phase2-installer.md)

异步HTTP使用connect/read/total timeout；共享scheduler/coordinator，串行分片轮询与控制公平排队；pending/readback/stale-query保护。freshness失败不刷新，climate/cover分离必需与可选字段，无位置不伪造状态。UDP1912仅提示真实读回；NSDP确认后使用本地认证。App/Terminal同artifact/schema2/owner，渠道冲突停止，rollback与RECOVERY_REQUIRED明确区分。历史验证报告不改写，当前测试数见本轮报告。

## Credits / Upstream

感谢 [NexHome 官方 Home Assistant integration](https://github.com/nexhome-org/nexhome-homeassistant-component)。基于v1.1.16、commit `bfcc161d7287770651113207cab511f848766fdb` 增强重组；保留原始来源和贡献说明，不声称官方授权。当前无独立LICENSE文件，不推定已具备某种发行许可，公开前仍需核实。见[上游对照](docs/upstream-changes.md)。
