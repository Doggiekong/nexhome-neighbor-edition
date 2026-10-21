# Phase 2 Stage C — HACS 与唯一更新所有权

状态：**Stage C 完成（有明确 PRIVATE source 实测边界）**。VM201 已完成真实 HACS lifecycle 和 Official → Installer 移交。
不进入 Stage D。生产 VM200 未修改，未使用真实 Hub。

## HACS 事实与边界

本轮取得稳定版 HACS 2.0.5，源 tag commit
`c0dfd8b44297c3673c21973e2539375a53687a9c`。
官方 release 的 hacs.zip 本地 SHA256：
`97be6b824a4f38e683728cc6dd72367f6b8bad0a43428b1b3b987a3087adf413`。
公开 GitHub API 遇到限流，改用官方 latest release 页面重定向与正常资产下载；
没有声称完成独立的 GitHub asset digest 校验。

- [官方配置流程](https://www.hacs.dev/docs/use/configuration/basic/)：HA config flow、GitHub device OAuth、完成配置。
- [官方仓库界面](https://www.hacs.dev/docs/use/repositories/dashboard/)：正常 Download / Remove；移除文件不等于删除 HA config entry。
- [PRIVATE 限制](https://www.hacs.dev/docs/faq/private_repositories/)：HACS 不支持 PRIVATE 仓库。
- [发布布局](https://www.hacs.dev/docs/publish/integration/)与 [hacs.json](https://www.hacs.dev/docs/publish/start/)：
  本项目保留 custom_components/nexhome，新增根 hacs.json；没有公开仓库、Release 或 HACS 发布。

未发现官方承诺稳定的自动 source-switch 管理接口。因此 source 释放、添加和下载采用正常 HACS UI，
不调用私有 mutation API，不写 `.storage/hacs*`。这些是需要用户明确执行/确认的最小步骤。

`neighbor_installer.hacs` 只读适配 2.0.5 `utils/data.py` / `utils/store.py` 的存储格式：
主 `hacs.repositories` ID 映射，以及为空时的 `hacs.data` category-list fallback。
提取 domain、installed、full_name、version_installed。此格式属于内部实现，**不是稳定公共 API**；
未知格式/版本不能建立可信 HACS 所有权，默认拒绝写入。适配器从不返回原始 storage/凭据。

## 所有权证据

| 分类 | 证据及规则 |
|---|---|
| NONE | 没有 NEXhome 文件、安装 claim 或 marker |
| OFFICIAL_HACS | 单一官方 installed claim、HACS 存在、可信官方源 tree hash 一致、无 Installer marker |
| COMMUNITY_HACS | 单一 Community installed claim、可信 Community tree hash 一致、无 Installer marker |
| NEIGHBOR_INSTALLER | 文件 hash、owner marker、对应 COMMITTED transaction 的 artifact/来源/revision 一致 |
| MANUAL_UNKNOWN | 现有文件缺乏充分来源证明，或 HACS schema 无法可靠理解 |
| OWNERSHIP_CONFLICT | HACS+Installer 双 marker、多 installed claim、已知源 hash 不符、stale Installer marker 等矛盾 |

版本号本身不证明 owner。HACS 存在但未管理 NEXhome，不改变 Installer owner。
已知仓库的 tree hash 必须由审核过的固定源/artifact 事先取得；没有可信 hash 只能诊断、不能猜测所有权。
CLI 支持 `--trusted-trees` 本地来源→tree-SHA256 catalog；不据 HACS 自报 metadata 自动建立信任。

HACS owner 下 apply、update、文件 rollback/recovery 都拒绝；activation 前后再次检查是否新出现 HACS claim。
HACS 不共享 Installer 文件锁，所以这不能成为对任意并发 HACS 操作的原子互斥保证。
实际移交必须先通过正常 UI 释放旧 owner，并避免并发更新；不确定时 RECOVERY_REQUIRED。

## 移交事务

SDK `Transfer`：preview → 精确 proposal SHA256 确认 → BACKUP → SOURCE_RELEASED →
DEPLOY → ACTIVATE/HEALTH_CHECK → VERIFY_OWNER → COMMITTED。
transfers journal 与普通 deploy journal 分开；未完成移交阻止其他 Installer 写操作。

- Official → Installer：先备份，正常 HACS UI Remove，验证 installed claim 消失；才允许固定 artifact 部署。
- Official → Community：先备份，正常 UI 释放旧源/安装新源，验证 Community hash/owner，重启与健康/身份验证。
- Installer → Community：备份且确认后只移除**自己**的 owner marker；HACS UI 接手。未完成 journal 阻止 Installer 重入。
- NONE → Installer：沿用 Stage A apply。NONE → Community：UI 安装后验证。
- MANUAL_UNKNOWN：展示 hash、精确确认、备份；有 HACS claim/schema 不确定时不能借手工确认绕过。
- CONFLICT：先解决矛盾，不能直接开始移交。

SDK 不做 HACS source mutation；CLI/最终 Launcher 向导仍是后续工作，本轮不开发 Stage D UI。
同 owner 的重复完成为 NO_OP；中断后 resume 只报告安全下一步，不猜测继续。

## 更新与恢复

`update.preview_update/apply_update` 对 Installer owner 显示当前/目标版本、来源、revision、固定 artifact manifest pin，
精确确认且 preview 未过期后调用既有 deploy engine。没有后台静默更新或周期下载。
Community HACS 更新由 HACS 负责，Installer 连 update preview 也拒绝进入写流程。

| 边界 | 承诺 |
|---|---|
| FILE_ROLLBACK | 只有当前未被 HACS 接管、文件/backup/marker 可验证时，沿用现有 engine 恢复 |
| OWNER_ROLLBACK | 释放前可取消，不改 integration 文件；释放后不能假装还由旧源管理 |
| HACS_SOURCE_ROLLBACK | 不自动改 HACS storage，需要正常 UI 恢复源并复核 |
| REGISTRY_RECOVERY | 沿用 Stage B；不删除重建 config entry 或 registry，不声称文件回滚逆转 schema |
| 中断/外部源变更 | 保留 journal、backup，明确 RECOVERY_REQUIRED；不默默放行双写/无人管理 |

移交保存 identity fingerprint，检查 config entry、registry 和引用文件没有变化。
本轮自动移交通路不默认放宽为新的 registry migration；若发生合法但 forward-only schema 变化，
仍需单独 Stage B migration preview 和人工 review，不能宣称完整自动回滚。

## 当前验证级别

本轮最终实际全回归 230 PASS：runtime 127 + installer 103；Ruff PASS。
Candidate 的 23 个部署文件没有变化（仍 dev4）；这不是新的真实设备现场验收。

| 路径/场景 | 当前级别 |
|---|---|
| Official → Installer | **ACTUALLY_VERIFIED**：正常 HACS UI 释放源，Installer dev4 COMMITTED |
| Official → Community | FIXTURE_VERIFIED；PRIVATE 仓库真实安装 BLOCKED |
| Installer → Community | FIXTURE_VERIFIED；PRIVATE 仓库真实安装 BLOCKED |
| HACS 配置完成 + Installer NEXhome | VM201 **ACTUALLY_VERIFIED**，HACS installed claim 为 0，Installer owner 不变 |
| 官方/Community owner、冲突、unknown、禁止双写 | FIXTURE_VERIFIED |
| 中断、释放前取消、释放后 recovery required、HACS-owned 文件回滚拒绝 | FIXTURE_VERIFIED |

VM201 保留 `StageC-BeforeHACS` 与 `StageC-InstallerWithHACS` 两个本轮 checkpoint。
HACS 2.0.5 实际安装、重启、GitHub 正常 device OAuth 和 HA onboarding 已完成。
OAuth 界面显示已有 public information read-only 权限，没有扩大到 PRIVATE 仓库访问。

实际 C1：HACS 配置完成、NEXhome 文件暂移到受控备份、owner NONE（原 synthetic entry 保留禁用）。
实际 C2/C3：正常 HACS 下载官方 v1.1.16、重启；OFFICIAL_HACS 正确识别，Installer 覆盖被拒绝。
HACS 对该固定 tag 的部署文件采用 LF，而 git blob 为 CRLF；从固定 tag 独立生成已知 LF 部署 variant，
22 个实际文件原始 SHA256 exact match。未根据未知目标自签信任，也未放宽运行时 hash 比较。

正常 HACS Remove 在 entry 存在时显示 configured 警告。2.0.5 前端提供 IGNORE → REMOVE 路径，
已通过源码与真实 UI 确认其可保留 config entry；没有删除 entry，没有改 HACS storage。
释放 installed claim 后，固定 dev4 artifact 部署、restart、health、owner verify、identity verify 均 COMMITTED。

最终保留 1 个 user-disabled/not_loaded synthetic entry，active=0；12 个 NEXhome registry entities、10 个 devices、
9 份用户引用配置与迁移前完全相同。用户名、entity_id、unique_id、USER/integration hidden、Area、
wrapper/manual metadata 和引用保持。HACS 自己的 update entity 生命周期被排除于用户身份 fingerprint，
其余用户身份及引用继续受保护。重复 Installer apply 为 NO_OP。

最终 owner NEIGHBOR_INSTALLER，HACS 保留配置但不管理 NEXhome；无 pending deploy/transfer。
临时 companion、实验目录、原先暂存副本、runner token env、device code 文件已清理；
备份和 journal 保留。Disposable 管理员凭据仍在 repo 外受限目录，HACS OAuth 凭据仅由 VM201 自己保存，
待 VM201 销毁时一起删除；未写入 Git、报告或截图。

HACS 目前不支持 PRIVATE source，因此 Community HACS 实际安装及两个涉及 Community HACS 的 source transfer
仍仅 fixture 验证并标记 BLOCKED。没有为本轮公开仓库或建立 Release。
正式 HACS 更新、其他 HACS 版本、断电/并发外部 updater 的广泛实机覆盖仍是边界。
Owner/source rollback 不能由代码恢复代替；transfer 之后的 file rollback 保守进入 RECOVERY_REQUIRED。

只建议下一轮另行授权 Stage D。本轮已停止，不自动开始。
