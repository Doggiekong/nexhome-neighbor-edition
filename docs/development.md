# Phase 1 Candidate 开发与验证

开发版本 `1.1.17.dev3`；manifest 使用合法 PEP 440 dev version，不伪装官方 `1.1.16`。dev3 仅修复 NSDP MODEL 空分隔段兼容性，受控现场范围见 [B2 诊断](b2-discovery-diagnostic.md)。

本分支只含 Community integration。没有 Installer、部署脚本、HACS ownership 切换器、LICENSE 决策、Release 或 Beta 邀请。main 仍保持原架构文档基线。

## 隔离离线测试

目标验证环境：Python **3.14.4**、真实 Home Assistant **2026.10.2**、`pytest-homeassistant-custom-component==0.13.373`。这不是家里的 HA。其他 HA/Python 版本尚未形成矩阵。

在独立 Python 3.14 虚拟环境安装 `requirements-dev.txt`，然后运行：

```text
pytest -q
ruff check .
ruff format --check .
python -m compileall -q custom_components tests
```

pytest 默认阻断 TCP/UDP socket，只放行测试框架本身需要的 Unix socket。HTTP、NSDP、Hub、时间与现场设备均是 synthetic fake/fixture；测试不得读取真实 HA、凭据文件或家庭网络。

覆盖 HTTP 错误/分段/超限、事件循环隔离、有界公平队列、分片、命令顺序、旧查询拒绝、pending 到期、directed readback、失败恢复、UDP 解析/去重、0/1/多 Hub、手动/重复/错误身份配置、fresh domain、用户隐藏/改名/wrapper、ownership 与实际 HA registry setup/reload、additive migration 和 diagnostics 脱敏。

## 可靠性参数

HTTP connect 3s、read 8s、total 11s，单次响应最多 1 MiB。网关 scheduler 队列 32、1 inflight；最多 3 条 control 后让 queued poll 执行。同设备 command queue 同样有界，不无限堆积。参数目前是候选默认值，未做多户压力标定。

轮询 3s、属性 64 个/块、freshness 15s、pending 5s、UDP address debounce 150ms。climate/cover 最多 6 次读回、间隔约 0.8s、读回预算约 5s；单个已经开始的 HTTP 请求仍受其自身 11s 上限约束，不能把 5s 误解为整个服务的硬截止。

控制部分失败不会撤销已经发生的动作或自动重发；异常明确提示未确认，清理 pending，后续 poll 读取真实状态。不做“失败后猜反向动作”。

## 审查重点与未验证项

- dev3 已在专用测试 HA 中完成有限现场验证；当前 Candidate 与旧生产补丁的证据分开，范围见兼容矩阵，不代表全型号或长期验收。
- 多 Hub、复杂网卡、VLAN、其他固件、真实 UDP payload 全集及长时间压力需后续受控验证。
- wrapper 推断仅限可靠显式链接；不能证明所有用户模板的来源。见 identity 文档。
- type3 外 climate、fan、sensor 多数型号只是 CODE SUPPORTED；type11 未验收动作，中途 cover Stop 未完整验收。
- 本轮测试端已停用、原生产 client 已恢复；未把 Candidate 安装到生产 HA。任何后续生产迁移仍须另行批准、备份和验收。
- 隐私检查是静态规则与人工上下文复核，不等于第三方安全审计。SN 本地配置/运行内存必需，但不写入仓库、日志或 diagnostics。

相关说明：[兼容矩阵](device-compatibility.md)、[identity/迁移](identity-and-migration.md)、[上游对照](upstream-changes.md)。
