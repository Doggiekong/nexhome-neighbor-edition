# NexHome 滨融府友邻加强版 v0.1.0 — 正式发布版本

| 项目 | 当前定义 |
|---|---|
| Product | NexHome 滨融府友邻加强版 / NEXhome Neighbor Edition |
| Version | 0.1.0 |
| Status | **正式发布版本 v0.1.0** |
| Git baseline | **main**（tag v0.1.0 指向正式发布提交） |
| Repository | PUBLIC |
| Phase 2 Stage E | COMPLETE_STOPPED |
| Technical assessment | RELEASE_CANDIDATE_READY |
| License / publication authorization | **USER MANAGED / OUTSIDE TECHNICAL GATE** |
| Public | YES |
| GitHub Release | [v0.1.0](https://github.com/Doggiekong/nexhome-neighbor-edition/releases/tag/v0.1.0) |
| Tag | v0.1.0 |
| HACS publication | NO |

Stage E 的 runtime 与 Installer/Controller 行为核心继续冻结于 `c9246a1bce8fa087f2b590667d683fa1f47d4964`。RC Distribution Bootstrap 增加普通用户下载/检测/菜单前端及官方 App repository；模板构建路径作兼容调整，运行与迁移行为核心不变。精确本轮 HEAD 和环境恢复证据见 Work 最终审计。

本轮实际执行 94 个 distribution/launcher 相关测试及 Ruff，VM201/VM400 使用相同 60022-byte 固定包，通过隔离原生流程与模拟读回到 READY；没有重跑历史 runtime Stage E，也没有访问 VM200 或真实 Hub。[分发验证与来源边界](rc-distribution-bootstrap.md)。

License / publication authorization 仍为 USER MANAGED / OUTSIDE TECHNICAL GATE；不调查许可、不新增 LICENSE、不作法律判断。历史报告保留原文。

## 仍需保留的能力边界

- 内部RC验证不是所有型号、NAS、语音平台、手机与远程访问或长期可靠性的保证。
- HAOS App 与 Terminal 二选一；正式仓库和固定 Release assets 公开提供。
- Terminal 已有一条完整下载命令、环境检测与方向键菜单；本轮实机限 Linux Docker bind mount。正式命令使用固定 v0.1.0 公网 Release 路径，源码与包均须校验。
- Edge 内嵌页重开曾停在 Loading；独立浏览器内嵌 READY 已通过。没有认定具体浏览器故障原因。
- 安装以设备可见、首次控制真实读回、用户确认READY为完成边界；已有entry沿用。
- 无位置窗帘保持unknown；滨融府大平层原配家庭语音中控和列出的语音平台仍NOT YET VERIFIED。
- 代码回滚不等于完整逆转registry/schema；历史恢复边界保持。

v0.1.0 Public Cutover 与公网 smoke test 完成后停止。不自动开展 HACS/Beta、邻居 Pilot 或下一版本。

## 正式发布入口

[GitHub 仓库](https://github.com/Doggiekong/nexhome-neighbor-edition) · [v0.1.0 Release](https://github.com/Doggiekong/nexhome-neighbor-edition/releases/tag/v0.1.0) · [安装与使用指南](安装与使用指南.md)。

历史 Stage E / RC Bootstrap 的提交、测试数字和 PRIVATE 状态保留当时事实，不当作今天的产品状态。对外 App 页脚由分发包装提供正式版本文案；冻结 runtime/SDK 包不重打。
