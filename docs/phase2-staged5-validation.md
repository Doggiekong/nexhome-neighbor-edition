# Phase 2 Stage D.5 — Product Identity & Documentation Cleanup

## A. Product identity

- 中文名：NexHome 滨融府友邻加强版。
- 技术名：NEXhome Neighbor Edition。
- 独立产品版本：0.1.0（内部验证，未发布）。
- 上游基线：NexHome official Home Assistant integration v1.1.16。
- 产品不是官方新版、官方后续版本或已获官方授权版本。

## B. Version migration

新增 runtime product.json 与 artifact schema2，独立记录 product_id、product_version、upstream_base_version、version_scheme。manifest/const/App 显示0.1.0；artifact revision 使用固定 Git commit；owner marker 与 transaction 保留产品身份。历史 schema1/dev1–dev4、历史 journal/验证报告不重写。

已验证归属的旧 NEIGHBOR_INSTALLER Candidate 才允许跨旧编号→独立产品线；未知版本/来源停止。新产品内正常比较，NO_OP仍需相同文件，同版本不同文件拒绝，降级拒绝。官方1.1.16不是 Neighbor1.1.16；HACS分类依赖source/hash/marker，官方安装通过显式渠道交接迁移，不跨来源盲目比大小。HACS自身标签降级/正式来源切换仍不能假设自动兼容；本轮没有发布任何tag/channel。

schema2元数据、manifest、product.json必须一致并由固定hash校验；禁止含product.json的产物剥除身份降回schema1。回滚恢复原代码/marker，保持历史语义。App和Terminal复用相同bundle，诊断同时包含产品/上游版本；旧编号仅在技术历史和迁移识别中保留，普通更新页显示“早期内部 Candidate”。

## C. README

完全重写为住户优先：这是什么、原来/现在改善对照、适合用户、安装前准备、环境入口、安装完成步骤、手机、远程访问、安全隐私、FAQ。技术内容通过分隔线后置，仍覆盖 timeout/scheduler/coordinator/chunking/freshness/pending/readback/NSDP/semantic/migration/ownership/rollback 等。

明确已有HA是产品起点，不负责安装NAS/PVE/Docker主机或家庭网络。公开入口/命令尚未分发；Linux Docker Terminal原型不代表所有NAS。Credits保留官方仓库、v1.1.16与commit来源；未擅自增加许可证或声称官方授权。当前无LICENSE文件，不推定发行许可，后续分发前仍需核实。

## D. UI / documentation wording

manifest与中英文title使用正式品牌；App/Terminal显示友邻版本与独立上游基线。技术详情保留build commit与历史installed version。当前架构/安装/隐私/兼容/身份/开发说明加入当前版本导航；新增 docs/product-versioning.md，解释历史Stage A/B/C/D版本边界，历史validation文件保持不动。

本轮没有启动或部署App/Terminal到VM，也没有操作真实设备；UI结果为源码/离线接口测试，不冒称新版本现场浏览器验收。

## E. Tests

本轮最终实际全量 **280 PASS**，Ruff **PASS**。组成：runtime127、原installer103、launcher及版本回归50。相较StageD264增加16个版本场景；历史264不是本轮测试数。首次全量274PASS/2FAIL为旧测试预期（devrelease/旧展示编号），更新为独立版本契约后全部通过；保留此说明，不隐藏初次失败。

新增覆盖：dev1–dev4显式迁移、0.1.0 NO_OP/0.1.1升级/失败回滚/降级拒绝、新产品拒绝旧target、官方版本非Neighbor、未知lineage停止、官方HACS fixture显式交接、Community HACS ownership不被越权、owner身份篡改拒绝、artifact身份校验及禁止剥离schema、App/Terminal文件和marker一致、双版本diagnostics和runtime metadata/history一致。现有runtime生命周期诊断断言也已更新。

真实Git commit构建包检查通过：schema2、manifest/product/App版本一致，上游1.1.16独立，24部署文件（新增product.json）。固定产物/hash/revision见artifact-check.json。仅构建到Work outputs，不部署、不Release。

## F. Git

分支 phase2/existing-ha-installer；logical commits和final HEAD见git-final.json。要求push PRIVATE、clean、main保持158221843e2d32165e015f5307fff7ec0958b0cb。不force-push，不改历史，不创建Release/tag，不HACS/Beta/Pilot。

## G. Remaining risks / Stop

0.1.0尚未现场部署；VM201仍保留上一轮dev4安全基线，本轮未修改VM201或VM200、未发现/访问真实Hub。正式HACS渠道的版本排序/来源迁移仍需后续独立授权验证；版权许可与公开分发未完成；多平台/物理手机/长期多户稳定性边界保留。

本轮完成后停止，未进入Stage E/Release/Pilot。
