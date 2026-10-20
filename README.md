# NEXhome Neighbor Edition

**Status: Phase 1 Community Integration Candidate — 1.1.17.dev1**

为使用 NEXhome 的住户开发更稳定的 Home Assistant 接入方案。本分支包含 Community integration 候选代码和隔离离线测试，**未部署生产、未发布正式 Community Release、没有 Installer**。

## 希望解决的问题

在有限真实环境的排查中，现有集成出现过请求超时不足、网关异常拖慢 Home Assistant、状态更新不可靠、设备 domain 不够合理等问题。手工填写中控参数、包装灯光实体和维护升级，对普通用户也不够友好。这些观察不代表所有版本、所有设备都存在相同问题。

## 项目目标

- 本地优先：设备仍由您自己的 Home Assistant 和家庭网络控制。
- 零参数 Hub discovery：正常情况下不要求填写 NEXhome IP、SN/IOTID。
- 安全升级：先备份、明确更新来源、可恢复已有配置。
- 正确的 light / fan / climate / cover 语义，同时尊重旧用户实体和自动化。
- 面向普通住户的中文向导，减少不必要的技术操作。
- 不建立第三方远程控制通道，不默认上传家庭设备状态。

“零参数”不意味着跳过 Home Assistant 管理员授权或首次账号设置，也不意味着静默调整房间、页面和自动化。

## 当前完成到哪里

已有架构设计、有限真实环境中的本地可靠性修复与 NSDP discovery 证据。本分支将这些经验重组成独立 Candidate，加入有界异步传输、共享协调器、语义实体、保守迁移、diagnostics 和离线测试；这次重组代码尚未现场验收。

已验证：Home Assistant Core 可在不知道 Hub IP/SN 的前提下，通过 UDP1912 NSDP 广播取得 LOCATION 和 MODEL.sn；发现的 SN 与当前集成所需配置逐字符一致。

边界：多 Hub、跨 VLAN、其他型号/固件及长期多户稳定性尚未全面验证。已有验证不等于统一安装器、所有设备映射或迁移工具已经完成。

## 更新归谁管理

一个 HA 实例中的 NEXhome **只能有一个更新所有者**：官方 HACS、Community HACS、Neighbor Installer，或待识别的手工来源。

不允许官方 HACS 继续覆盖本地 Community 补丁；Community 由 HACS 管理时，Installer 不另行替换文件。没有 HACS 也可以设计直接安装路径，HACS 不是运行前提。首版计划由用户确认每次升级，不后台静默更新。

## 文档

- [隐私与安全原则](docs/privacy-and-safety.md)：数据在哪里、谁能访问、如何授权和恢复。
- [总体架构](docs/architecture.md)：分层、平台矩阵、状态机、更新所有权、回滚与公开门槛。
- [未来安装流程](docs/installation-flow.md)：三类用户的预期体验与目前边界。
- [Phase 1 开发与离线验证](docs/development.md)
- [设备兼容矩阵与现场边界](docs/device-compatibility.md)
- [Identity 与保守迁移](docs/identity-and-migration.md)
- [上游逐文件对照](docs/upstream-changes.md)
- [Phase 1 验证记录](docs/phase1-validation.md)

候选代码基于上游 NEXhome v1.1.16，不包含家庭配置、日志、备份、真实设备标识或生产部署脚本。仓库保持 PRIVATE；只有完成 Public Readiness Review 并经项目发起人明确决定后，才考虑公开。开发分支不得作为生产安装指引。
