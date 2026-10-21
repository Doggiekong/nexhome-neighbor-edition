# Stage D 入口选择与最新授权收敛

正式名称：NexHome 滨融府友邻加强版。技术名称 NEXhome Neighbor Edition。
起点是已有、能正常使用且有管理员权限的 Home Assistant；不建设 HA 安装/网络平台。

| 入口 | HA OS | Container | HACS/SSH/文件 | 常驻与权限 | 恢复与维护 |
|---|---|---|---|---|---|
| 临时本地 Web | 仍缺 HA 文件写入通道 | 需配置目录及生命周期授权 | 不必 HACS；仍需 bootstrap | 需额外认证及主机适配 | 本身不能凭 HA 登录安装文件 |
| 桌面启动器+Web | 仍需授权 companion | 同左 | 安装桌面程序、跨平台负担 | 凭据与宿主机权限复杂 | 手机无法独立首次启动 |
| HA 应用/Add-on | **可行，选用** | 无 Supervisor，不支持此入口 | 无需 HACS/SSH；普通用户由应用商店安装/打开 | HA 登录+Ingress；只申请配置目录与 Core 生命周期 API | 独立于 Core，重启期间安装核心仍运行 |
| HACS custom source | 可安装 integration，不能代替文件事务向导 | 同左 | 需要 HACS；PRIVATE不支持 | HACS 管理自己的更新 | 不能与 Installer 双写 |
| 现有临时 companion 包装 | 工程上可行 | 独立 Linux Docker bind 原型已验证（见下文） | 人工 transport 不能当普通用户入口 | 加入标准 Add-on 容器最自然 | 直接复用 A/B/C core |
| 只做 HA integration/panel | 不能安全替换正在运行的自身代码 | 同左 | 无外部写入通道 | 重启时安装进程消失 | 不选，避免削弱恢复模型 |

## 选择

以 Add-on/应用 + Ingress 响应式向导为第一条真实支持路径。复用 neighbor_installer，
前端只显示、确认、调用。无公开端口、无 Docker socket、无 host network、无保护模式关闭，
无 HA 密码或长期浏览器 token。管理员身份由 HA/Supervisor 原生 Ingress 验证；
应用只接收 Supervisor 内部地址和带用户身份的 Ingress 请求，并增加逐用户防跨站确认。

公开依据：[应用配置](https://contributors.home-assistant.io/apps/reference/configuration/)、
[内部 API 代理](https://contributors.home-assistant.io/apps/guides/communication/)、
[Ingress](https://contributors.home-assistant.io/apps/guides/ingress/)。
Supervisor 2026.10.2 实际源码也确认 panel_admin 会拒绝非管理员，而不只是隐藏导航。

最低权限：homeassistant_config:rw（只能在程序中收窄写入 NEXhome及其安装备份）；
homeassistant_api 与控制 Core 所需 Supervisor role；其权限是平台级授予，不能虚称只有 NEXhome 的细粒度 token。
不默认上传任何家庭数据。

## 本轮分发边界

仓库保持 PRIVATE，未发布应用商店源或 Release。VM201 使用从固定源码生成的本地 DEV/TEST 应用包，
开发者仅负责把包放入 disposable 环境；实际 App 界面中的检查/确认/部署无需终端；部署完成统一跳转 HA 原生配置，不再维护平行配置表单。
普通住户通过“应用商店添加来源→安装→启动→打开界面”的正式分发入口，要留到另行授权的发布准备阶段。
不能把这个受限分发边界描述成已经可以交给真实邻居安装。

最新授权新增 Terminal bootstrap：复用同一固定安装包和 Controller/Installer，部署后即退出，后续配置回到 HA 原生界面。ContainerLifecycle 只操作用户明确指定的现有 Docker HA 容器，核对 /config 的可写 bind mount 与选定目录完全一致，拒绝 Supervisor 管理的容器。不会安装 HA、创建容器、配置网络或挂载 Docker socket 到 Web 服务。需要现有宿主机的 Docker 管理权限及临时 HA 授权。其他 NAS 封装/非 Docker 环境尚未验证，应停止并给出明确边界，不能笼统宣称所有 NAS 可一键运行。

## 验证边界

VM201 先独立 checkpoint，再用现有 synthetic fixture 验证已有用户；fresh 场景使用干净 snapshot。
连接步骤仅使用 VM201 的临时 fake gateway/明确替换的测试 discovery，不向真实 LAN 广播、不联系真实 Hub。
不测试灯光/空调/窗帘控制。结束恢复预期 VM201状态，清理应用测试服务和 fake；生产 VM200只读。

## 两阶段模型

多个部署入口 → 同一 neighbor_installer 和固定 artifact → 同一 NEIGHBOR_INSTALLER 元数据 → HA 原生配置。App 无发现/选择中控 API；Terminal 不提供长期管理界面。独立安装产生不同 transaction_id 属于正常审计差异，版本、文件哈希、归属和语义元数据必须一致。

终端原型：在已核验来源和固定哈希的开发包中执行 `python -m neighbor_launcher.bootstrap --config ... --package ... --container ... --ha-url ... --confirm`。授权由隐藏输入读入内存，密码/token 不放命令行。当前 PRIVATE 开发包不提供 curl 管道脚本或公开下载地址。分发签名/正式链接不在本轮范围内。
