# Identity 与保守迁移

> 技术与历史设计记录；其中阶段状态保留当时事实。当前版本与安装方法请看 [项目首页](../README.md) 和 [安装与使用指南](安装与使用指南.md)。

> 当前产品：NexHome 滨融府友邻加强版 0.1.0；上游基线独立为官方 v1.1.16。不是官方新版。当前入口与边界以 [README](../README.md) 和 [版本规则](product-versioning.md) 为准；下文阶段记录保留当时事实。


最高原则：**User intent wins. Existing manual customization takes precedence over automatic semantic migration.**

## Fresh 与 compatibility

- 新 config flow 创建 `identity_mode=fresh`。实体按设备 type 和真实属性能力进入 light/fan/climate/cover/sensor/switch；不用名称或房间猜类型。
- 老条目默认 `compat`。Config entry schema `1.2` 仅增加 mode、必要时保留旧 `sn` 并补充 `sn_input`；不删除其他 data/options，不更新已有 flow unique_id，不隐式切换到 fresh。
- Fresh entity unique_id：`gateway-{SHA256(SN)前20位}:{address}:{catalog_key}`；device identifier：`gateway-{同一摘要}:{address}`。摘要只用于本地稳定 identity，**不导出 diagnostics**。
- Compat entity unique_id：`nexhome.{device_id}_{catalog_key}`；device identifier：原 device_id。保留上游公式与已有 registry entity_id。相同旧 device identifier 如已属于其他 config entry，拒绝静默合并，要求人工审查。
- 同一身份不能在一个 HA 实例加载两个 coordinator。多 Hub 的 fresh identity 有 namespace，仍需现场验证。

## Legacy switch → light/fan

必须先有当前 config entry 的确切 legacy switch registry 记录；不扫描用户 YAML，不靠名称关联。

1. 保留原 switch、unique_id、entity_id 与控制能力；不删除、不 disable。
2. 用户 hidden_by=USER、disabled、改名、图标、Area、标签、明确自定义别名或可靠 switch-as-X source link：跳过创建新 semantic entity。
3. 无法归属本集成的 integration-hidden 记录也保守跳过。
4. 无人工痕迹时，新 semantic unique_id 为 `{legacy_unique_id}:semantic:{domain}:v1`，设备关系不变，尽量继承 basename。
5. 新实体实际加入 HA registry 后，才用官方 API 将旧 switch `hidden_by=INTEGRATION`，并在本地 HA Store 写 ownership marker。**隐藏不改变旧自动化调用能力**。
6. 重载时只有 marker 和准确 semantic registry 记录同时存在才复用；不会把自己隐藏的记录误当人工隐藏，不重复生成实体。
7. 如果 semantic 已由本项目建立，其后用户改名/隐藏仍由 HA registry 保留；不删除已存在 semantic 来“恢复初始状态”。

HA 2026.10 的 computed-name alias sentinel 属于默认值，不等于用户自己写的字符串 alias。真实 HA registry 测试覆盖这一差异。

ownership metadata 存在 HA Store `nexhome.semantic.{entry_id}`，只在本地，不属于可分享 diagnostics。Diagnostics 用单次导出的 `entity-N` 关联展示 legacy/semantic，不暴露 identity。

## 明确边界

- 不重写 Area、Dashboard、Group、automation、用户模板或 wrapper。
- 只可靠识别 HA 的显式 switch-as-X 配置链接。任意 template light/fan 并不能总是可靠反向识别；无隐藏/自定义痕迹时仍有重复展示风险，diagnostics 提供迁移状态供审查。
- 用户只改 entity_id、却没有其他 registry 元数据痕迹时，无法总是证明其人工意图。保留旧 entity_id，不冒充“任意定制均可自动识别”。
- 原设备 address/id 或 Hub SN 改变涉及 identity 变化，本轮不实现跨身份合并或自动迁移。
- compat 中没有可证明旧 switch identity 的 type1 继续保守保持原 switch，不强制造另一套 light。
- 本轮只有隔离 HA setup/reload/migration 验证，**透明生产升级/回滚仍未验收**。不得把 Candidate 直接当升级器使用。
