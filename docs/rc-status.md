# NexHome 滨融府友邻加强版 0.1.0 — RELEASE CANDIDATE

| 项目 | 当前定义 |
|---|---|
| Product | NexHome 滨融府友邻加强版 / NEXhome Neighbor Edition |
| Version | 0.1.0 |
| Status | **RELEASE CANDIDATE** |
| Git baseline | **main**（RC 分发分支通过验收后仅允许 fast-forward） |
| Repository | PRIVATE |
| Phase 2 Stage E | COMPLETE_STOPPED |
| Technical assessment | RELEASE_CANDIDATE_READY |
| License / publication authorization | **USER MANAGED / OUTSIDE TECHNICAL GATE** |
| Public | NO |
| GitHub Release | NO |
| Tag | NO |
| HACS publication | NO |

Stage E 的 runtime 与 Installer/Controller 行为核心继续冻结于 `c9246a1bce8fa087f2b590667d683fa1f47d4964`。RC Distribution Bootstrap 增加普通用户下载/检测/菜单前端及官方 App repository；模板构建路径作兼容调整，运行与迁移行为核心不变。精确本轮 HEAD 和环境恢复证据见 Work 最终审计。

本轮实际执行 94 个 distribution/launcher 相关测试及 Ruff，VM201/VM400 使用相同 60022-byte 固定包，通过隔离原生流程与模拟读回到 READY；没有重跑历史 runtime Stage E，也没有访问 VM200 或真实 Hub。[分发验证与来源边界](rc-distribution-bootstrap.md)。

License / publication authorization 仍为 USER MANAGED / OUTSIDE TECHNICAL GATE；不调查许可、不新增 LICENSE、不作法律判断。历史报告保留原文。

## 仍需保留的能力边界

- 内部RC验证不是所有型号、NAS、语音平台、手机与远程访问或长期可靠性的保证。
- HAOS App与Terminal二选一；当前没有公开分发入口。
- Terminal 已有一条完整下载命令、环境检测与方向键菜单；本轮实机限 Linux Docker bind mount。公开 Release 尚未创建，私人等价源验收不代表任意住户现在可匿名下载。
- Edge 内嵌页重开曾停在 Loading；独立浏览器内嵌 READY 已通过。没有认定具体浏览器故障原因。
- 安装以设备可见、首次控制真实读回、用户确认READY为完成边界；已有entry沿用。
- 无位置窗帘保持unknown；滨融府大平层原配家庭语音中控和列出的语音平台仍NOT YET VERIFIED。
- 代码回滚不等于完整逆转registry/schema；历史恢复边界保持。

完成main整合后停止；这不是正式发布、公开仓库、tag、Release、HACS/Beta或邻居Pilot的授权。
