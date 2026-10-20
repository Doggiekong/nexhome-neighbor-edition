# Phase 1 Review Gate

日期：2026-10-20。被审查 commit：`b3eb66943303698c61c9b9181ce2749fbfe139ff`。修复候选版本：`1.1.17.dev2`。仅 PRIVATE 开发分支，不 merge main，不创建 Release。

这是新一轮逐模块复审及离线复验，不是第三方安全审计，也不是 Candidate Field Validation。

## 发现与修复

| 级别 | 真实缺陷 | 修复与测试 |
|---|---|---|
| P1 | optional 缺值仍使共享 coordinator 每轮 UpdateFailed，与 required/optional 目标不一致 | EntitySpec 显式定义必需属性替代集合；仅必需集合不满足时失败；cover Location 或完整开关停字段二选一；同地址不同 sensor 各自要求不能被 OR 吞掉；可选缺值仍计数且不刷新 freshness |
| P1 | cover 任意方向位置变化都可能被判 command confirmed | 只接受接近目标或向目标方向运动；反向移动不确认。仍不宣称完成最终行程 |
| P2 | 极深异常 JSON 可抛 RecursionError，未转成统一 GatewayError | 捕获并使用固定脱敏异常；深嵌套响应回归覆盖 |

另新增取消 command 后 pending/锁/队列计数清理与后续命令恢复测试。没有把 transient HTTP 故障伪装为成功，没有放宽 required freshness，没有改任何生产配置。

文档复核同步修正 architecture/privacy 的历史“当前仅整理文档”状态说明：Phase 1 已有离线 Candidate，Installer/Profile 仍是规划；未来 installation-flow 继续明确不可当作当前安装教程。

## Review 覆盖结论

| 范围 | 结论 |
|---|---|
| API / scheduler / coordinator 分层 | HTTP 校验与调度独立，所有实体共享数据及控制链路，无逐实体独立轮询 |
| HTTP 与并发 | connect/read/total 有界，body 有界；1 inflight、32 队列、control burst 3 后给 poll 机会；同设备顺序；无无限 SyncWorker |
| 失败 / 取消 / shutdown | 失败不重发控制，pending 清理；shutdown 可重复；队列取消不发送；已发请求取消的实际设备结果仍可能未知，以后续读回为准 |
| 状态 | 15s freshness、5s pending、定向读回、命令前旧查询拒绝；新真实值权威。optional 不污染全局失败，required/transport 仍失败并可恢复 |
| discovery / flow | 0/1/多 Hub、显式确认、manual、重复与身份不匹配保护；有限接口广播，不扫描、不单播 fallback；不日志 SN |
| entity semantics | type + 实际属性决定能力；type3 numeric OFF=0；无 Location 不造百分比/开合；旧固定命令值不当真实状态 |
| legacy / registry | 旧 switch 保留可控；用户隐藏/改名/元数据与可靠 wrapper 链接保守跳过；owned marker + registry 配合复用；重载幂等；不重写 Area/Group/UI/automation |
| diagnostics / privacy | allowlist、局部匿名标签、无 raw SN/IP/设备名/属性值；不上传；仓库扫描及上下文复核通过 |
| 文档 | 首版 107 tests 记录保留历史标识；当前为 112 tests；既有 FIELD_VERIFIED 与 Candidate 离线结果分开 |

## 复验

真实 HA **2026.10.2**、Python **3.14.4** 隔离环境，**112 tests passed**。Ruff lint/format、compileall、JSON/manifest、secret/privacy 与 diff whitespace 检查通过。pytest 阻断 TCP/UDP socket，全部协议交互 synthetic。

## Gate 与剩余边界

**未发现 fundamental architecture BLOCKER。** 可继续建立空白 Reference HA，但不安装 Candidate、不做 Hub discovery、不做真实控制。

多 Hub/VLAN、完整 UDP payload、不同型号与长期负载仍未现场验证。任意 template wrapper 和仅改 entity_id 的人工痕迹不能保证识别。无位置 cover 只能确认核心字段可读，不能确认物理行程/中途停止。这些边界未被本轮测试消除。
