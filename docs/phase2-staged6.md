# Phase 2 Stage D.6 — Installation Completion & User Manual

PRIVATE 开发验证；产品0.1.0，上游基线1.1.16；没有Release、公开仓库、Pilot或Stage E。

## A. Installation Definition

COMMITTED仅证明部署事务提交。新边界：DEPLOYED → CONFIGURED → CONTROL_VERIFIED → 用户确认知道控制入口 → READY。Core管理员只读WebSocket报告已加载entry、可用实体和一次命令真实读回证明；Launcher本地保存“已找到控制入口”的显式确认。退出码0、实体创建或乐观pending均不独立构成READY。无可确认状态的命令不产生控制证明。

## B. Product Flow Changes

本轮增加Core完成证据、首次确认持久化、只读检查、App确认按钮和Terminal `--verify-completion`。保留同一installer core、身份迁移策略和rollback边界。安装器不发送设备命令来自动凑足READY，不自动创建Dashboard。

Fresh：部署后“开始连接NexHome”直接打开HA原生 `/config/integrations/dashboard/add?domain=nexhome`。用户可能先确认HA标准设置提示，再核对Hub并提交。唯一Hub无需手填IP/SN；多Hub由原生flow选择；零Hub明确未找到，手动添加集成仅备用。没有实现强行自动弹窗、后台静默entry创建或平行Hub网页。

Existing：原entry保留；原生user flow在discovery前检测已有entry并终止重复添加，设备入口指向现有集成。正常升级不重新discovery。修复现有无效endpoint不属于本轮。

## C. Native Discovery

zero/single/multi行为在本轮full regression实际覆盖。VM201/VM400新建流程使用Core内临时lab替换发现结果为一个合成Hub，之后GatewayClient真实HTTP访问本机模拟网关；不是实际UDP discovery现场复测。实际HA2026.10.2前端源码和浏览器确认原生路由；旧猜测路由未继续使用。

## D. VM201 / E. VM400

VM201：App浏览器check/preview/deploy、原生配置按钮、Hub提交、5个模拟设备、灯光ON/OFF和真实模拟回包、check_setup、显式确认READY均实际验证。重载后entry/entity/device身份与控制证明保留；重复user flow拒绝且发现调用仍1次。

VM400：C0→临时C1，固定官方HA2026.10.2镜像中的Python3.14执行同一Terminal SDK；部署与 `--verify-completion` 均返回成功。原生flow创建一个合成entry，5个实体，模拟ON/OFF和读回、重载、重复添加保护实际通过。App/Terminal部署25个文件及schema2/版本/owner metadata相同，只有独立transaction ID不同。

VM400已恢复C0，归档hash有效、测试容器stopped、临时包/网关/授权文件清理；原有4个服务ID/启动时间/端口/网络、全部Docker网络和data-root保持不变。VM201已恢复StageD-BeforeLauncher：Core2026.10.2/Supervisor healthy，dev4的23个文件hash匹配，唯一原合成entry disabled、active0；本轮App、临时lab和路径均不存在，原COMMITTED事务保留。

## F. Real Hub

本轮没有真实Hub discovery、登录、属性读取或设备控制；没有VM200 disable/restart/handover/代码或配置写入。模拟E2E足以验证新增完成状态与原生衔接，既有Phase1真实协议结果只作为历史背景，不计入本轮现场通过。

## G. Manual / H. Beginner Guide

[安装与使用指南](安装与使用指南.md)覆盖准备、安装类型、App/Terminal、原生连接、首次操作、Dashboard、房间/灯组、观影场景、时间/工作日/日落/回家与全家离家示例、官方手机App、Home/定位、通知、家庭语音与各语音平台、家外访问分类、安全和故障边界。README仅保留判断适用性和指南入口，手机只提官方Home Assistant App。

截图为当前HA2026.10.2隔离测试UI及官方Companion下载页；IP裁切/打码，不含真实SN、凭据或家庭成员。共18张图，图源清单与hash见 `manual-images/provenance.json`。手机章节不引入虚构的另一个App概念。辅助元素/群组/灯组、地点、原生确认、场景实时编辑与预览模式均按实际UI修正文案。

## I. Verification Boundaries

| 范围 | 结论 |
|---|---|
| Full runtime/installer/launcher regression | OFFLINE VERIFIED |
| VM201实际HA/App/原生单Hub流程/模拟控制读回/READY | VM201 VERIFIED |
| VM400实际HA/Terminal/模拟控制读回/READY/C0恢复 | VM400 VERIFIED |
| 本轮真实Hub / 真实UDP广播 | NOT VERIFIED，本轮未执行 |
| 手机实机、定位变化、通知发送、语音、家外访问 | NOT VERIFIED |
| 房间/灯组/场景/自动化编辑UI | UI VERIFIED，不等于生活场景实际运行验收 |
| 其他NAS、跨VLAN、多户长期运行 | NOT VERIFIED |

## J. Tests

本轮最终实际执行286 PASS：runtime129、installer103、launcher54；较D.5增加6项。Ruff检查PASS。覆盖新完成边界、已有entry不重复发现、真实HA fixture读回/重载、Terminal显式确认，以及既有NO_OP/身份保护/渠道/rollback恢复回归。历史280PASS不是本轮结果。

## K. Git

当前分支 `phase2/existing-ha-installer`；逻辑代码提交3fb159b、e35143d、9826524。最终文档提交、HEAD、PRIVATE推送与clean核对见Work最终报告。main不改，不tag/Release/public/HACS/Beta/Pilot。

## L. Remaining Risks

原生直接配置按钮是有意采用的授权fallback，不承诺自动弹出。READY证明一次读回及用户已找到入口，不证明所有设备/能力永久健康。私有包还没有面向住户的正式下载/一条命令分发；指南不虚构公开安装源。Terminal需受支持Python3.14环境，本轮使用固定官方HA镜像，不要求升级主机Python。语音平台、手机、远程访问与其他NAS须后续单独授权验证。当前发行许可仍需公开前核实。本轮完成即停，不进入下一阶段。
