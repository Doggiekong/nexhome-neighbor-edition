# 上游基线与重组记录

Based on upstream **nexhome-org/nexhome-homeassistant-component v1.1.16**，commit `bfcc161d7287770651113207cab511f848766fdb`。

开发前已对上游 18 个 Python 文件与既有本地修复备份做完整逐文件 diff 和 hash 对照。14 文件存在行为修改，4 文件一致。完整原始 diff 属于私有参考证据，不提交本仓库；下表记录每个文件的目的，不能把私有部署代码原样复制为发行代码。

| 上游/本地文件 | 对照结果 | Candidate 去向/处理 |
|---|---|---|
| header.py | 已改 | api.py + scheduler.py：native async HTTP；connect/read/total timeout；HTTP/JSON/业务校验；有界请求与公平串行 |
| nexhome_coordinator.py | 已改 | coordinator.py：网关合并、64 属性分片、逐字段 freshness、真实 readback、旧查询保护 |
| coordinator_manager.py | 已改 | __init__.py：每身份唯一 shared coordinator；entry ownership 与清理 |
| nexhome_entity.py | 已改 | entity.py：共用控制与状态，registry 用户信息优先 |
| __init__.py | 已改 | entry 生命周期、可选 shared UDP listener、失败清理、迁移框架 |
| nexhome_discover.py | 已改 | discovery.py：有限广播、严格解析、UDP 仅提示 HTTP 刷新 |
| light.py | 已改 | 显式 ON/OFF、附加参数校验、共享读回，无假默认色温 |
| fan.py | 已改 | native fan、真实可见速度能力、无虚构百分比 |
| climate.py | 已改 | required/optional 分离，type3 numeric OFF=0，其他型号保留未现场验证标记 |
| cover.py | 已改 | type6 Location 可选，固定命令值不是 state，无位置不造百分比 |
| switch.py | 已改 | 保留 legacy 控制，新增 semantic 时只隐藏不禁用 |
| sensor.py | 已改 | 逐字段有效值/过期处理，使用目标 HA 可接受的 device class |
| number.py | 已改 | 不机械迁入 synthetic 默认场景入口；当前真实型号目录没有 number entity |
| select.py | 已改 | 不机械迁入 synthetic 默认场景入口；当前真实型号目录没有 select entity |
| config_flow.py | 一致 | 新建广播发现/选择/确认/高级手动流程；不照搬旧手填界面 |
| const.py | 一致 | 只保留通用常量，删除示例主机/身份/default scene 等私有或合成实例 |
| nexhome_device.py | 一致 | 纯公共型号元数据整理成 catalog.json + models.py；删除 synthetic default scene |
| utils.py | 一致 | 旧通用辅助不机械携带；identity/capability/校验分到对应模块 |

## 主动重组的理由

同步 requests 改为 HA 共用 aiohttp session，不借助外层协程 timeout 掩盖阻塞线程，也不建立每设备 SyncWorker 轮询。网关请求最多 1 inflight，队列上限 32，最多连续 3 条控制后让轮询得到机会。同设备 command FIFO；多属性控制承认可能部分生效，不盲目重发。

所有模型共用 coordinator 数据。失败与缺值不刷新时间戳；必需字段缺失的 partial poll 在 coordinator 层报告失败，可选缺失单独记录，实体 availability 按各自 required 字段判断，避免可选字段让整台空调/窗帘 unavailable。

新增 migration.py、diagnostics.py 与离线 tests，是 Community 的保护机制；不是生产目录的临时补丁。移除所有临时诊断入口、调试 print、家庭实例、设备名称、生产地址、凭据和本地路径。

HA 2026.10 兼容调整：旧 CO2/VOC sensor device class 映射到当前枚举；HCHO 无对应正式 class 时仅保留单位，不发明 enum。Device registry 使用当前 `async_get_devices` API，避免已弃用的全局唯一假设。

SN→MD5 authentication header 仍是公开上游本地协议，不表示密码学安全增强。集成只连用户确认的局域网 endpoint；无 telemetry、云 relay、项目方管理通道、自动更新或 Installer。
