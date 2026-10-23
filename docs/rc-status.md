# NexHome 滨融府友邻加强版 0.1.0 — RELEASE CANDIDATE

| 项目 | 当前定义 |
|---|---|
| Product | NexHome 滨融府友邻加强版 / NEXhome Neighbor Edition |
| Version | 0.1.0 |
| Status | **RELEASE CANDIDATE** |
| Git baseline | **main**（与 `phase2/existing-ha-installer` fast-forward 后完全相同的提交和 tree） |
| Repository | PRIVATE |
| Phase 2 Stage E | COMPLETE_STOPPED |
| Technical assessment | RELEASE_CANDIDATE_READY |
| License / publication authorization | **USER MANAGED / OUTSIDE TECHNICAL GATE** |
| Public | NO |
| GitHub Release | NO |
| Tag | NO |
| HACS publication | NO |

本基线在本轮 `main` fast-forward、远端核对完成后生效；精确提交可通过 `main` 与保留的开发分支查询，本轮Work审计另存最终hash。没有普通merge或新的程序组合。

Stage E已验证的程序内容不变，固定runtime/SDK来源为 `c9246a1bce8fa087f2b590667d683fa1f47d4964`。本轮只改文档、截图引用和状态，不重建artifact、不改版本或schema，不重跑287 tests、不操作VM/真实设备。Stage E历史报告与历史数字不改写。

本轮调整仅将当前许可/发布授权责任明确为用户管理，不进行许可调查或法律判断，不新增LICENSE，也不暗示官方授权。旧报告中不同的历史定位不作为当前RC或main整合Gate。

## 仍需保留的能力边界

- 内部RC验证不是所有型号、NAS、语音平台、手机与远程访问或长期可靠性的保证。
- HAOS App与Terminal二选一；当前没有公开分发入口。
- Terminal复制步骤以维护者已准备本机环境和参数为前提，现有CLI不具备通用主机自动检测。本轮没有通过新脚本伪造这一能力。
- 安装以设备可见、首次控制真实读回、用户确认READY为完成边界；已有entry沿用。
- 无位置窗帘保持unknown；原家庭语音中控和列出的语音平台仍NOT YET VERIFIED。
- 代码回滚不等于完整逆转registry/schema；历史恢复边界保持。

完成main整合后停止；这不是正式发布、公开仓库、tag、Release、HACS/Beta或邻居Pilot的授权。
