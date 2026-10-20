# Phase 1 Candidate 验证记录

日期：2026-10-20。版本：`1.1.17.dev1`。分支：`phase1/community-integration-core`。

本页是首次 Candidate 的历史验证记录；当前 `1.1.17.dev2` 的复审、修复与 112 项测试见 [Review Gate](phase1-review-gate.md)。历史现场边界未扩大。

## 结果

- **107 tests passed**，Python 3.14.4 / 真实 Home Assistant 2026.10.2 / pytest-homeassistant-custom-component 0.13.373。
- `ruff check .`：通过；`ruff format --check .`：通过。
- Python compileall：通过；JSON/manifest/dev version 合约测试：通过。
- repo secret/privacy 静态扫描及命中上下文复核：通过。概念性的认证字段、安全文档和 synthetic fixture 不是实际凭据。只有测试网段、UDP bind、公开协议的 loopback body，未包含生产 IP、SN、房间实例、真实 entity_id 或私有路径。
- 未连接/修改生产 HA；未做新的实际 discovery、设备控制、部署或现场测试。

## 覆盖

| 分类 | 离线验证内容 |
|---|---|
| API | connect/read/total timeout、HTTP/JSON/业务错误、分段响应、大小限制、异常不回显内容 |
| 调度 | 1 inflight、有界队列、控制优先且 polling 公平、排队取消、event loop 不被阻塞 |
| 协调器 | 150 属性分片、共享读取、partial failure、缺值、失败恢复、旧查询拒绝、pending 到期 |
| 控制 | 同设备 FIFO、明确 ON/OFF 不跳过、directed readback、不盲目重发、失败清理 |
| UDP / discovery | 坏包、字段顺序/重复、来源校验、debounce、不直接应用 UDP value、广播无单播 fallback、0/1/多 Hub |
| Config flow | 确认、手动参数、旧条目去重、错误身份 reconfigure、认证失败关闭 client、非法索引 |
| 语义 | fresh light/fan/climate/cover/sensor/switch、30 个型号缺属性时的安全行为、sensor device class |
| 迁移 | 用户隐藏/禁用/改名/图标/Area、wrapper 显式关系、ownership、legacy 保留、重复迁移 |
| HA lifecycle | 真实 HA config entry/setup/reload/unload、registry identity 不重复、名称/隐藏保留、setup 失败释放网关 |
| 隐私 | diagnostics allowlist、额外敏感字段不泄漏、没有 raw SN/IP/设备名/值、运行代码没有 debug print |

pytest 以 `--disable-socket --allow-unix-socket` 运行，所有网络协议交互均为 fake。既有现场验证不是本轮 Candidate 的现场验证；细分边界见 [兼容矩阵](device-compatibility.md)。

## 审查与停止点

没有发现需要绕过的架构 BLOCKER；尚未解决的现场矩阵、任意 template wrapper 识别、用户仅改 entity_id 的识别、其他 HA 版本与长期多户压力明确保留为风险/后续验收项。

这是第一版可审查 Candidate，不是 Production Release。仅 push private 开发分支；不 merge main，不发布 Release，不实现 Installer，不安装家庭环境。分支对应实际 HEAD 以 Git commit 为准。
