# 设备兼容性与证据边界

> 技术与历史设计记录；其中阶段状态保留当时事实。当前版本与安装方法请看 [项目首页](../README.md) 和 [安装与使用指南](安装与使用指南.md)。

> 当前产品：NexHome 滨融府友邻加强版 0.1.0；上游基线独立为官方 v1.1.16。不是官方新版。当前入口与边界以 [README](../README.md) 和 [版本规则](product-versioning.md) 为准；下文阶段记录保留当时事实。


版本：Community Candidate `1.1.17.dev3`，Based on upstream NEXhome v1.1.16。2026-10-21 受控测试环境的本轮证据与此前生产补丁历史证据分开记录。

**Candidate 已在隔离测试 HA 中连接真实 Hub，完成有限代表性现场测试；未安装到生产 HA。** FIELD_VERIFIED 只指当前 Candidate 本轮明确列出的能力，不代表整类型、整户或长期稳定性验收。原生产补丁的历史成功不再混入下表的 Candidate 现场状态。

| 状态 | 含义 |
|---|---|
| FIELD_VERIFIED | 当前 Candidate 本轮实测通过的代表性能力，严格受下表范围限制 |
| IMPLEMENTED_NOT_FIELD_VERIFIED | 有代码、公共协议目录或离线测试，没有该型号现场验收 |
| UNSUPPORTED / UNKNOWN | 没有可靠型号定义；不凭设备名称猜测，也不生成猜测实体 |

| NEXhome type | HA domain（fresh） | 状态 | 能力与限制 |
|---|---|---|---|
| 1 | light | FIELD_VERIFIED（代表性开关灯） | 原生 light、明确/重复 ON与OFF、真实读回、外部轮询收敛；不代表所有 type1 通道都是灯，不按名称自动推断特殊用途，迁移仍未现场验证 |
| 2 | light | FIELD_VERIFIED（代表性调光灯） | 原生 light、开关、一次中间亮度设定与读回及物理效果；0–255 未跨型号重新标定，色温未测 |
| 51 | light | IMPLEMENTED_NOT_FIELD_VERIFIED | 亮度/色温需实际读到属性；不伪造默认色温 |
| 3 | climate | FIELD_VERIFIED（本轮所列能力） | 制冷模式、设温、风速、numeric `0` OFF及一次ON恢复，均有真实读回与现场确认。其他模式、外部变化、故障恢复未现场验证 |
| 11 | climate | FIELD_VERIFIED（只读 availability） | 原生 climate、缺可选室温时仍可用；控制动作仍 IMPLEMENTED_NOT_FIELD_VERIFIED |
| 35, 73, 100, 101, 102, 107 | climate | IMPLEMENTED_NOT_FIELD_VERIFIED | 保留协议映射；模式/风速/摆风范围不能冒充现场结果 |
| 6 | cover | FIELD_VERIFIED（有限） | 有 Location 的代表样本：中间定位、关闭、打开及实际位置；正确方向的位移/读回。无 Location：仅只读可用及诚实 unknown；控制未测。Stop、外部同步和人为反方向故障均未本轮现场验证 |
| 30, 108 | cover | IMPLEMENTED_NOT_FIELD_VERIFIED | 30 开关；108 开关停。均不提供虚构位置 |
| 10 | fan | FIELD_VERIFIED（仅只读） | 原生 fan、可用性/状态；开关及预设控制仍 IMPLEMENTED_NOT_FIELD_VERIFIED |
| 75, 133 | fan | IMPLEMENTED_NOT_FIELD_VERIFIED | 仅声明并实际读到的风速可展示，不发明百分比 |
| 14 | sensor | FIELD_VERIFIED（仅读取链路） | 原生传感器及真实更新；没有参考仪器校准，精度及故障恢复未现场验证 |
| 5, 8, 12, 13, 15, 16, 59, 60, 61, 62, 110 | sensor | IMPLEMENTED_NOT_FIELD_VERIFIED | 按公共目录属性生成；过期/缺失字段 unknown 或 unavailable，不填零 |
| 132 | switch | IMPLEMENTED_NOT_FIELD_VERIFIED | 真实 switch 语义，不按中文名称猜成灯 |
| 其他/未知 | 无猜测实体 | UNSUPPORTED / UNKNOWN | 保留未知型号边界 |

完整型号/字段目录见 `custom_components/nexhome/catalog.json`；测试检查目录中所有 sensor device class 是否被目标 HA 接受。目录不包含设备实例、家庭名字、地址或生产配置。

## 可用性、可选属性和读回

- light / fan / switch：PowerSwitch 必需。附加调光/色温/风速功能需要型号定义且至少读到过有效属性；暂时过期返回 unknown，不保留旧值作为新鲜值。
- climate：PowerSwitch、TemperatureSet 必需，空调还需 WorkMode；地暖不强求 WorkMode。Temperature、Windspeed、WindDirection 是可选状态，不拖累整机 availability。可选控制若无法读回，服务报未确认，不永久预测成功。
- cover：有效 Location 或新鲜核心控制字段可以维持可用；Open/Close/Stop 固定 `1` 只能说明核心字段可读，**不是真实开合**。无位置设备的成功反馈明确为 `core_readback_only`，不能证明运动或最终停止。
- 所有属性 15 秒新鲜度，pending 5 秒。命令前旧查询不能覆盖命令后状态；新真实读回具有权威性。缺字段不会更新时间戳。
- 可选属性缺失保留缺失计数和独立过期信息，不把整轮 coordinator 判失败；必需字段或所有替代核心字段集合均缺失时才报告 UpdateFailed。HTTP/解析故障仍明确失败。
- 默认 3 秒共享轮询，但网关变慢、大属性集合、失败超时或负载会延长完整周期，**不承诺任何规模都在 3 秒内收敛**。超过新鲜度应如实 unavailable。

## 发现与 UDP

当前 Candidate 的未知 IP/SN 广播、真实回包解析、单 Hub confirm 为 FIELD_VERIFIED，限定当前 LAN/Hub/固件。dev2 的空 MODEL 分隔段拒绝缺陷已在 dev3 修复；见 [B2](b2-discovery-diagnostic.md)。0 Hub/multi Hub、VLAN与其他固件未现场验收。

UDP refresh fast path：有解析、来源/属性校验、合并与 debounce 离线测试；只触发 HTTP 读回，不直接相信 UDP value。**本轮外部变化窗口未收到 UDP，因此 hint、dedup及其directed read仍未现场验证**；轮询最终同步已实测。listener 被占用时保留轮询。

Fresh registry 的重复检查、reload/重启 identity 稳定及不猜 Area 已在测试环境核对。可选字段缺失未导致整轮失败、分片共享轮询及命令后 directed readback 有短时现场证据；HTTP stall/故障恢复、并发命令乱序保护和反向运动拒绝主要仍是离线证据。该范围不代表长稳或压力验收。

多 Hub、其他固件、跨 VLAN、复杂多网卡、长期多户稳定性与实际升级迁移仍待下一阶段验证。没有 HACS/Installer/生产发布声明。
