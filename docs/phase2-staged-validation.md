# Phase 2 Stage D 完成报告

本轮为 DEV/TEST Installer / Launcher 验证，不是发布或邻居部署。正式名称：NexHome 滨融府友邻加强版。范围止于 Stage D。

## A. 入口与架构

HA OS 使用 HA App（原 Add-on）与原生 Ingress；已有 Linux Docker HA 使用一次性 Terminal bootstrap。两个入口复用同一 Controller、Stage A/B/C installer、固定 Candidate 1.1.17.dev4；安装结束统一进入 HA 原生配置。没有第二套 Hub 选择/配置表单。App 不是运行时依赖。

App 原型实际运行于 VM201 HA OS18.3、Core/Supervisor2026.10.2、amd64。受限 PRIVATE 开发包由维护者放入本地 App 源；普通住户的公开商店来源/签名/分发尚未实现。Terminal 原型仅支持已有 Linux Docker、明确容器名及可写 /config bind，需本地 Docker Unix socket 权限和 HA 授权。它不会安装 HA、创建容器或配置网络；不需要 Hub IP/SN。不能宣称全部 NAS/桌面平台适用。

## B. 流程

已实现检查、预览、确认、备份、部署、健康检查、完成与原生 HA 入口；同版本 NO_OP；来源不明/归属冲突默认拒绝覆盖。HACS 官方源交接使用正常 HACS UI 的移除并保留配置流程，不直接写 HACS storage。中断重开、单次确认和并发操作保护复用持久 journal。回滚失败保留 RECOVERY_REQUIRED，不声称代码回滚可逆转全部 registry mutation。

## C. 浏览器与界面

实际 Edge 验证桌面、390px 窄屏、可见键盘焦点、默认折叠技术详情、实际导出脱敏诊断。窄屏无横向溢出。物理手机未实测。HA 重启后 Ingress 有时需要重新打开；页面已明确提示，不宣称无缝自动重连。最终完成页只有一个“打开 Home Assistant”入口；点击并正常重新登录后实际进入 NEXhome 原生页面，显示 dev4、无条目及“添加条目”。原生集成仍名为 NEXhome Community Candidate/Community，本轮没有修改 runtime 品牌字段。

## D. 文案与配置

面向用户使用中文任务式说明，无伪造进度百分比；诊断详情可展开。不存在长期 Terminal Web 管理台，也不存在平行 Hub 配置 API。

## E. 核心与产物

Candidate runtime 23 文件未修改。App 与 Terminal 实际部署文件哈希完全相同，版本与 NEIGHBOR_INSTALLER 语义归属一致；独立 transaction_id 不同是正常审计行为。固定 runtime commit ec3ca097d976409d86644a32cdd1e6a5b3638f82；artifact manifest SHA256 83ae45e291b9e1cb5dd9b3b04d18acac9eb69d14feae47d70c0f2f9585ba8af4。

## F. 权限与隐私

App 无公开端口、无 host network、无 Docker socket、保护模式保持开启；原生 HA 管理员 Ingress 验证，逐用户确认及请求边界。Supervisor 配置写入/Core 生命周期权限是平台级授权，不能声称细粒度仅限 NEXhome。Terminal 使用本地 Unix API，不依赖宿主 Docker CLI；拒绝 Supervisor-managed Core 和错误 mount。密码/token 不进入 URL、命令行参数、Git 或报告。实际下载的诊断文件秘密字段检查为0。

## G. HACS

实际官方 v1.1.16（22个已知 LF 文件）→ App 引导正常 HACS 移除交接 → dev4，部署与 ownership transfer 均 COMMITTED。固定 HACS2.0.5 的 storage version 字符串“6”已兼容，未知格式仍 fail closed。PRIVATE Community HACS 发布不在本轮范围。

## H. 实际验证与隔离验证

| 场景 | 结果与证据边界 |
|---|---|
| 已有官方迁移 | VM201 实际浏览器完成；身份摘要前后 exact，原 synthetic entry/registry/引用保持 |
| Fresh App | 实际部署 COMMITTED，23文件、NEIGHBOR_INSTALLER；App 停止后 Core 正常 |
| App 删除独立性 | 实际停止并卸载 App 后 Core/集成文件/身份仍正常 |
| Fresh Terminal | VM201 内独立 HA Docker 实际 COMMITTED；进程退出后原生配置入口可用 |
| 双路径一致性 | 实际文件与语义元数据 exact；审计 transaction_id 独立 |
| Terminal 再执行 | 实际 latest/NO_OP，无重复部署 |
| 原生配置进入 | App 浏览器和 Container API 均进入原生 flow；使用空结果离线 discovery，未访问真实 Hub，未创建新 entry |
| 失败/恢复/unknown/冲突/中断页面 | 实际浏览器渲染隔离只读样例，无安装权限；不是 VM201 真实故障注入 |
| rollback/recovery/幂等/请求边界 | 离线 fixture 测试，不冒称全部现场失败注入 |

Terminal 首次尝试因宿主 Docker CLI 动态加载器不兼容在部署前停止，无 transaction；改用本地 Docker Unix API 后成功，保留首失败证据。

## I. VM201 与清理

最终恢复点为 StageD-BeforeLauncher；另保留 StageD-ExistingUI-Validated 现场验证快照和脱敏证据。独立 Container 会话已撤销，新建临时凭据已删除，测试 Container 已移除，Windows loopback UI fixture server 已停止。最终恢复后健康/文件/entry/临时路径结果见 final-environment-audit.json。原有 repo 外受限 disposable 管理员凭据按既定生命周期保留至 VM201 销毁，不擅自删除。不会把安全保留的 disabled synthetic entry 或 checkpoint snapshot 视为故障。

## J. Git

继续 PRIVATE 分支 phase2/existing-ha-installer，基线26c72a312db65fa24a6bb1263e16f9a28729ae74。最终 commits/HEAD/clean/push/main 核对见 current-state.json 和 git-final.json。未 merge main、未 Release、未 public、未 HACS/Beta 发布。

## K. 测试

本轮最终实际全量运行264 PASS：runtime127、installer103、launcher/bootstrap34；Ruff PASS。final-tests.txt / final-ruff.txt 为原始结果。此前255等中间计数、Stage A53/Stage B74/Stage C230仅为历史/中间基线，不另计成本轮新增通过。测试完成后仅文档/报告更新，无 runtime 修改。

## L. 生产安全

VM200 未修改、未 disable、未 restart；未访问真实 Hub、无设备命令、无生产 Area/Dashboard/registry/config entry 变更。原生 discovery 在 Core 内被明确替换为无网络空结果，审计 calls=1/network=false；没有双真实 active client。VM200 Observer 只读最终健康核对见审计。

## M. 尚未验证

物理手机、macOS/Windows Docker、其他 NAS 封装与非 Docker 平台；正式分发、签名、应用商店安装来源；本轮真实 Hub 自动连接/真实设备控制；长期运行；所有失败的真实 VM 注入。Terminal 仍是需要现有管理员权限的原型，不能宣传零权限一键安装。

## N. 建议与停止

Stage D DEV/TEST 验证完成后停止。只建议下一轮单独授权 Stage E；本轮不实施发布、正式 launcher 分发、邻居部署或生产迁移。
