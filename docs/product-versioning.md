# 产品身份与独立版本（Stage D.5）

正式中文名 NexHome 滨融府友邻加强版；技术名 NEXhome Neighbor Edition。不是官方新版或官方后续版本。

## 数据模型

runtime 的 product.json 是文件哈希覆盖的身份声明：product_id=nexhome-neighbor-edition、product_version=0.1.0、upstream_base_version=1.1.16、version_scheme=neighbor-independent-v1。HA manifest.version 与 const.PRODUCT_VERSION 是产品版本；const.VERSION 为兼容别名，UPSTREAM_VERSION 为上游别名。HA manifest.name/翻译 title 使用产品名。

Artifact schema2 记录上述四字段，version 保留为 product_version 的兼容别名，revision 是不可变 Git commit；校验 metadata、manifest、product.json 一致，pin 与文件哈希仍必需。schema1 仅用于读取历史 Candidate/fixture，不能把新产品回切成历史编号。Owner marker 保存同样字段，transaction 保存完整 artifact；回滚恢复原 marker 与文件，不原地重写历史 journal。

## 比较规则

先识别 source/owner/hash，后比较版本，不拿官方版本与 Neighbor product version 作大小比较。官方 HACS→Installer 仍走显式 ownership transfer，不以 1.1.16 高于 0.1.0 为由阻止合法迁移；版本本身不是来源证明。

已验证 NEIGHBOR_INSTALLER 的历史 schema1 dev1–dev4 → schema2 独立产品是显式 lineage transition；不使用数值降级判断。仅依赖版本字符串、MANUAL_UNKNOWN、其他未知内部版本均不足以跨 lineage。新产品之间按 packaging.version 比较；同文件 NO_OP，同版本不同文件拒绝覆盖，降级拒绝。新产品→旧 schema1 target 拒绝；显式 transaction rollback 仍按原备份恢复。

HACS 自身可能按标签进行版本排序；未来正式渠道必须显式切换并清除旧源更新责任，不能把同一旧源标签序列直接递增或假设 HACS 会自动接受 0.1.0。当前正式 Release/tag 为 v0.1.1；HACS 发布仍未进行。HACS owner分类依据 source/tree/证据，不取决于版本数值。

## 显示与诊断

App/Terminal 显示友邻加强版产品版本和独立官方基线；普通更新页把旧编号称为“早期内部 Candidate”。技术详情保留历史 installed version；runtime diagnostics 和 launcher diagnostics 同时显示 product_version/upstream_base_version。构建 revision 保留追溯，不写入自身 Git commit 以避免自引用。固定 build 命令仍必须 pin 完整 commit。

## Stage D.5 历史验证边界

以下保留 Stage D.5 当时事实，不代表当前发布状态。当时仅本地源码与隔离离线测试，不部署 VM201/VM200，不 discovery/control，不修改既有 owner 状态文件。实际用户环境的旧 marker 将在明确授权升级时由新代码读取；不是本轮已迁移现场。历史 Stage A/B/C/D 验证文档保留原版本与原测试事实。本轮新测试数量见 D.5 报告，未正式发布。

历史入口：[Stage A](phase2-installer.md)、[Stage B](phase2-stageb.md)、[Stage C](phase2-stagec.md)、[Stage D](phase2-staged-validation.md)。这些文档中的版本/测试数字均为当时事实，不代表当前产品版本或本轮新测试结果。
