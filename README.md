# NexHome 滨融府友邻加强版

## 项目简介

一个基于 NexHome 官方 Home Assistant 组件改进、专为滨融府大平层住户打造的社区增强版本。

当前版本：**[v0.1.1](https://github.com/Doggiekong/nexhome-neighbor-edition/releases/tag/v0.1.1)**。本项目由住户社区维护，并非 NexHome 官方版本。

## 主要改善

| 原来可能遇到的问题 | 友邻加强版的改善 |
|---|---|
| 中控异常时一直等待，拖慢 Home Assistant | 限制等待时间，避免一直拖住 Home Assistant |
| 灯光、空调、窗帘等设备不容易找到合适的控制方式 | 新接入时尽量按设备类型显示；已有用户优先保留原来的控制入口 |
| 要自己找中控地址和识别信息 | 典型单中控家庭网络可以自动查找，由你确认 |
| 升级时担心名字、房间或自动化被打乱 | 优先保留原有设置，不能确认安全时先停止 |
| 文件装好了，却不知道设备能不能用 | 安装后引导你确认设备能够正常控制和同步状态 |

## 适合谁

使用开发商原配 NexHome 系统，已经有一套正常运行的 Home Assistant 的滨融府大平层住户。

当前主要根据滨融府大平层原配 NexHome 中控和设备进行开发与验证。其他户型或不同设备组合也可能可以使用，但目前没有完整验证。本项目不负责安装 Home Assistant 本身。

## 开始安装

**先确认自己使用的是哪一种 Home Assistant 安装方式。**

不知道的话，先看：**[如何查看 Home Assistant 安装类型](docs/安装与使用指南.md#choose-route)**。

**下面两种安装方式只需要选择一种，不要两种都做。**

安装前建议先保留一次 Home Assistant 备份，并准备自己的管理员账号。

> [!NOTE]
> **A · Home Assistant OS**
>
> <a href="https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FDoggiekong%2Fnexhome-neighbor-edition" target="_blank" rel="noopener noreferrer"><img src="https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg" alt="添加到 Home Assistant"></a>
>
> **建议右键上方蓝色按钮，选择“在新标签页中打开”，这样可以保留本指南，方便安装过程中随时回来查看。**
>
> [查看 Home Assistant OS 详细教程](docs/安装与使用指南.md#route-a)

> [!TIP]
> **B · NAS / Docker / Container / Linux**
>
> **[Terminal 安装](docs/安装与使用指南.md#route-b)** → 复制完整一行命令，按安装助手提示操作。

手机端使用官方 Home Assistant App。

## 安全与隐私

- 主要在家庭网络内工作，不默认上传家庭设备状态或使用记录。
- 不需要把密码交给维护者。
- 安装前建议保留 Home Assistant 备份；不能确认安全时会停止。
- 不自动修改你的仪表盘、房间、自动化或路由器，也不自动开放公网访问。

## 常见问题

**这是官方软件吗？** 不是，由住户社区维护，以官方组件为基础改进。

**我家适合用吗？** 主要面向滨融府大平层原配 NexHome 系统，其他组合还没有完整验证。

**两种安装方式都要做吗？** 不用，按自己的 Home Assistant 安装类型选一种。

**已经装过官方 NexHome 怎么办？** 从同一入口开始，助手会检查已有安装。请保留 Home Assistant 里的 NexHome 设备与设置，不要先删除。如果以前通过 HACS 安装过，按助手提示在 HACS 中完成相应操作。

**要自己填写中控 IP 吗？** 典型单中控家庭网络通常不用；有多个中控时需要选择，网络隔离时可能需要协助。

**原来的自动化会不会丢？** 正常升级优先保留现有设备名称、房间和自动化引用，不能确认安全时不会强行安装。仍建议先备份。

**为什么有的窗帘没有百分比？** 部分原配窗帘只提供开、关、停，没有位置反馈。仍可操作，但不会显示一个猜出来的位置。

## 致谢

### NexHome 官方

感谢 [NexHome 官方 Home Assistant 组件](https://github.com/nexhome-org/nexhome-homeassistant-component) 提供原始开发基础。

### 邻居 Neil

特别感谢邻居 Neil，他的 NexHome Home Assistant 项目为本项目提供了不少参考和启发。

技术参考项目：[Neil-UWA/nexhome-homeassistant-component](https://github.com/Neil-UWA/nexhome-homeassistant-component)

## 技术说明

普通用户安装和使用不需要阅读这一节。

- [当前发布状态](docs/rc-status.md) · [来源与致谢](NOTICE.md)
- [版本体系](docs/product-versioning.md)：产品版本独立于上游基础 v1.1.16。
- [架构](docs/architecture.md) · [隐私与安全](docs/privacy-and-safety.md) · [兼容矩阵](docs/device-compatibility.md)
- [身份与迁移](docs/identity-and-migration.md) · [安装核心](docs/phase2-installer.md)
- [Stage E 历史验证](docs/phase2-stagee-validation.md) · [Stage D.6](docs/phase2-staged6.md) · [Stage C](docs/phase2-stagec.md)

License / publication authorization: **USER MANAGED / OUTSIDE TECHNICAL GATE**。沿用既定策略，详细技术与历史验证记录保留原文。
