# RC Distribution Bootstrap 验证

> 历史设计/验证记录：保留当时事实。当前已公开的 v0.1.0 与安装入口以[发布状态](rc-status.md)和[使用指南](安装与使用指南.md)为准；下文旧 PRIVATE/未发布描述不代表当前状态。

2026-10-29：先实现、再实机验证、最后修订指南。Product 0.1.0 RELEASE CANDIDATE，仓库 PRIVATE；没有 tag、Release、HACS 发布或住户部署。

## 当前来源边界

GitHub 项目保存真实官方 App repository 结构：根 repository.yaml + nexhome_neighbor/config.yaml/Dockerfile。同仓库承担 integration、installer、docs 和 App，无需第二个仓库。

本轮使用明确授权的 **local equivalent distribution fixture**：Supervisor 通过实际 HTTP Git smart protocol 浅克隆仓库，不向本机预复制 App；Terminal 从网络下载 Bootstrap，未预复制源码。没有宣称已验证匿名访问 PRIVATE GitHub，也没有把将来的 Release 写成当前可用下载。

官方添加机制：[My Home Assistant](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FDoggiekong%2Fnexhome-neighbor-edition)，结构依据 [官方 App 仓库文档](https://contributors.home-assistant.io/apps/guides/repository/)。本轮实际添加使用 Supervisor 正常 store add API；没有因为截图重复提交。公开源开放、权限与发布由用户另行决定。

<a id="actual-command"></a>
## 实际执行的唯一命令

**仅本轮隔离 VM400 验收记录，不是其他住户的安装地址。** 临时源测试结束后关闭，不能把该私网地址复制到另一户；这不是需要用户替换的占位符。实际执行时这一整行没有任何修改：

```sh
sh -c 'd=$(mktemp -d); trap '"'"'rm -f "$d/start.sh"; rmdir "$d"'"'"' EXIT; curl -fsS http://192.168.0.40:18779/assets/start.sh -o "$d/start.sh" && echo "9ee729ad1672753ed9a8f2626b3461eecba89d80116f8af43a0c1c80f4402e16  $d/start.sh" | sha256sum -c - >/dev/null && sh "$d/start.sh" --fixture-source http://192.168.0.40:18779/assets'
```

该命令与源页面一同提供；一次复制、六次 Enter、用户名/隐藏密码两个认证字段。不是四条维护者 CLI，不需要提前 cd、clone、下载 zip、指定配置目录或环境变量。

## 信任链

固定 Bootstrap SHA-256：`9ee729ad1672753ed9a8f2626b3461eecba89d80116f8af43a0c1c80f4402e16`。

固定 frontend SHA-256：`1445ccae9faf1ed01ded39822e94c096dff6eae7a087f152c581bde23a2d878e`。

HAOS/Terminal 相同 archive：60022 bytes，SHA-256 `9c689161a068d840d1be66f88f1673fca2b5f4866a04b93237fe6b8b8679b093`；bundle manifest SHA-256 `f6102c029ee3c27f65beafc68a5cbf22639df2a3a2dc713e0131f84144e390e1`。

对应既有冻结源码 c9246a1bce8fa087f2b590667d683fa1f47d4964。解包拒绝不安全路径和链接；SDK 的 Artifact.open 再次校验。没有 main.zip。

`distribution/start.sh` 普通入口锁定 `/releases/download/v0.1.0`，只接受 HTTPS 与受限跳转；显式 fixture 模式只允许本地字面 IP。当前该 Release **未创建**；拒绝 401/403/404 时不会换装其他版本。未来由发布操作放置同名固定文件，不需要改写 Installer Core。

## 同一个安装核心

Frontend 负责下载、检测 Docker/配置卷/本机网页地址、箭头菜单和当前会话认证；随后在所选已存在 HA 镜像中运行原冻结 SDK。主机 Python3.13 与镜像 Python3.14 不混用、不升级。source/ownership/identity/backup/preview/transaction/health/rollback/recovery 继续由原 Installer/Controller 负责。只修改 neighbor_launcher/package.py 的模板来源兼容路径，不改变行为核心。

## 实际验证

- 94 个 distribution + launcher 相关测试通过；Ruff 通过。不是重跑历史 runtime Stage E。
- VM400：C0、无 Neighbor 源码 → 完整一条命令 → 下载校验 → 自动检测（发现 LAN-only 端口问题并修复）→ 菜单/预览/部署 → 单一模拟中控原生配置 → 五实体/模拟控制读回 → READY。C0 已精确恢复、验证健康后主动停止；四个原服务和 network/data-root 均未变。
- VM201：Supervisor 真正从等价 Git 仓库浅克隆 → App 可见/安装/启动 → 固定包 → 浏览器预览/部署 → 模拟原生确认/五设备 → 模拟开关读回 → 用户完成确认 → READY。独立浏览器正常内嵌通过；Edge 重开曾停在 Loading，同一授权 Ingress 单独打开正常。现场同时看到扩展错误，但未证明因果，不把 Edge 说成全面稳定。
- 最终 App 包装补测：固定文件 hash 与 97b387f 一致，实际 start → stop → start，冻结解包目录 pyc 为 0。Docker ENV 原本也已禁用缓存；新增 sys 标志是额外防护。测试夹具默认分支曾未同步，已修正并核对 Supervisor checkout 与运行文件，未把旧包装当作新包装通过。
- VM201 已再次恢复本轮前快照；VM400 已恢复 C0 并停止；临时分发服务关闭。
- 两条路径均未访问真实 Hub，未操作真实设备；VM200 本轮未访问。

## 边界

本轮实机是 amd64 HAOS、Linux Docker bind mount。多候选箭头选择通过真实 PTY 测试；命名卷、自定义 TLS、其他 NAS/架构/非 Docker 平台不冒称实机通过。PRIVATE GitHub 认证克隆、公开 Release CDN 跳转仅有边界/单测，没有正式发布 E2E。官方添加按钮机制已核对，未把浏览器的既有默认 HA 目标当作测试目的地自动访问。

License / publication authorization：USER MANAGED / OUTSIDE TECHNICAL GATE。
