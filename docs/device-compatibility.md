# 设备兼容性与证据边界

版本：Community Candidate `1.1.17.dev1`，Based on upstream NEXhome v1.1.16。

**本候选代码只完成离线验证，没有安装到生产 HA，没有重新操作真实设备。** 下表的 FIELD_VERIFIED 指此前本地修复的有限现场证据，不代表这一重构版本已经现场验收。

| 状态 | 含义 |
|---|---|
| FIELD_VERIFIED | 同类核心行为有既有现场证据；具体范围见下表 |
| IMPLEMENTED_NOT_FIELD_VERIFIED | 有代码、公共协议目录或离线测试，没有该型号现场验收 |
| UNSUPPORTED / UNKNOWN | 没有可靠型号定义；不凭设备名称猜测，也不生成猜测实体 |

| NEXhome type | HA domain（fresh） | 状态 | 能力与限制 |
|---|---|---|---|
| 1 | light | FIELD_VERIFIED | 明确开关、读回、外部状态收敛有既有证据；原生语义实体/迁移只离线验证 |
| 2 | light | FIELD_VERIFIED | 开关、调光灯状态修复有既有证据；原始亮度量程沿用上游 0–255，未跨型号重新标定 |
| 51 | light | IMPLEMENTED_NOT_FIELD_VERIFIED | 亮度/色温需实际读到属性；不伪造默认色温 |
| 3 | climate | FIELD_VERIFIED | 开关、温度、模式、风速与外部变化有既有证据；OFF 必须 numeric `0` |
| 11 | climate | FIELD_VERIFIED（仅 availability/basic model） | 仅核心/可选字段分离的可用性模型；不宣称地暖动作已验收 |
| 35, 73, 100, 101, 102, 107 | climate | IMPLEMENTED_NOT_FIELD_VERIFIED | 保留协议映射；模式/风速/摆风范围不能冒充现场结果 |
| 6 | cover | FIELD_VERIFIED（有限） | 有 Location：真实位置/定位/外部同步；无 Location：开关停入口、位置与开合 unknown。**中途 Stop 未完整现场验收** |
| 30, 108 | cover | IMPLEMENTED_NOT_FIELD_VERIFIED | 30 开关；108 开关停。均不提供虚构位置 |
| 10, 75, 133 | fan | IMPLEMENTED_NOT_FIELD_VERIFIED | 正确 fan domain；仅声明并实际读到的风速可展示，不发明百分比 |
| 5, 8, 12, 13, 14, 15, 16, 59, 60, 61, 62, 110 | sensor | IMPLEMENTED_NOT_FIELD_VERIFIED | 按公共目录属性生成；过期/缺失字段 unknown 或 unavailable，不填零 |
| 132 | switch | IMPLEMENTED_NOT_FIELD_VERIFIED | 真实 switch 语义，不按中文名称猜成灯 |
| 其他/未知 | 无猜测实体 | UNSUPPORTED / UNKNOWN | 保留未知型号边界 |

完整型号/字段目录见 `custom_components/nexhome/catalog.json`；测试检查目录中所有 sensor device class 是否被目标 HA 接受。目录不包含设备实例、家庭名字、地址或生产配置。

## 可用性、可选属性和读回

- light / fan / switch：PowerSwitch 必需。附加调光/色温/风速功能需要型号定义且至少读到过有效属性；暂时过期返回 unknown，不保留旧值作为新鲜值。
- climate：PowerSwitch、TemperatureSet 必需，空调还需 WorkMode；地暖不强求 WorkMode。Temperature、Windspeed、WindDirection 是可选状态，不拖累整机 availability。可选控制若无法读回，服务报未确认，不永久预测成功。
- cover：有效 Location 或新鲜核心控制字段可以维持可用；Open/Close/Stop 固定 `1` 只能说明核心字段可读，**不是真实开合**。无位置设备的成功反馈明确为 `core_readback_only`，不能证明运动或最终停止。
- 所有属性 15 秒新鲜度，pending 5 秒。命令前旧查询不能覆盖命令后状态；新真实读回具有权威性。缺字段不会更新时间戳。
- 默认 3 秒共享轮询，但网关变慢、大属性集合、失败超时或负载会延长完整周期，**不承诺任何规模都在 3 秒内收敛**。超过新鲜度应如实 unavailable。

## 发现与 UDP

NSDP 未知 IP 广播、LOCATION、MODEL.sn 与 HA 所需身份一致已有单一 LAN/Hub/固件的既有 Core 现场证据。候选 config flow 的 0/1/多 Hub 分支只离线验证。

UDP refresh fast path：有解析、来源/属性校验、合并与 debounce 测试；只触发 HTTP 读回，不直接相信 UDP value。**尚没有完整真实 payload 格式矩阵**。listener 被占用时保留轮询。

多 Hub、其他固件、跨 VLAN、复杂多网卡、长期多户稳定性与实际升级迁移仍待下一阶段验证。没有 HACS/Installer/生产发布声明。
