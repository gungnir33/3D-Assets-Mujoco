# 任务 9 实施记录

2026-09-21–22，工程 main，origin `https://github.com/gungnir33/3D-Assets-Mujoco.git`。任务 9 起点 `b8e4f25`（8A 文档阶段）；全部工作起点 `b0419beb8e86a3663bd5ee09df755c861f99d6e7`。

提交：`f12b501` 请求预检，`d8b2f1b` 本机 HTTP，`9461519` 可恢复编排。未 push。

模块：chain_contracts.py 独立 schema/严格 JSON/文件预检；chain_http.py 标准库无代理、无重定向、单次 POST；chain.py 编排与来源恢复；scripts/chain.py 薄入口；cli.py 仅抽取现有错误退出分类。

第一阶段实际 schemas/app 已只读复核：text.prompt、image.image、texture.mesh/condition_image，成功 job_id/file/type/metadata，metadata 为路径。没有 import 第一阶段或调用生成 POST。

## 测试证据

- B1：19 RED→19 GREEN；新增 1e999、未实现 decompose/watertight 预检 3 RED→GREEN；全量 249 passed,1 skipped，44.53 s。
- B2：18 RED→18 GREEN；全量 267 passed,1 skipped，47.82 s。临时 loopback 随机端口，422/503/非 JSON、307、不完整/超限响应、1800 秒参数、超时不重试、代理隔离、localhost 检查。
- B3：9 RED→9 GREEN；额外 I/O 原异常保留 1 RED→GREEN；全量 286 passed,1 skipped，56.93 s。真实合成 compile/full 转换、preserve 物理失败保留、恢复无 POST、包外记录、迁移、dry-run 零网络/零目录、错误码 2/3/4/5/7。
- B4：安装包模式全量 **294 passed,1 skipped，63.74 s**；两个入口 × 三种端点真实 HTTP 契约，supplied 配置相对路径组合，原生 XML forward、EGL、迁移与证据核对。
- 唯一 skip：OSMesa 的 OpenGL loader 不可用；不改驱动，EGL 可用。没有用 skip 隐藏原生验收失败。
- pip check：No broken requirements found。25 个安装源模块逐字节匹配仓库。

解释器 `/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild_8a9_20260921_5Ibcv05j/bin/python`；Python3.10.21/MuJoCo3.4.0/trimesh4.7.4/numpy2.2.6/scipy1.15.3/pydantic2.11.7，锁文件未改。安装命令 `python -m pip install --no-deps --no-build-isolation .`；全量 `env -u PYTHONPATH python -B -m pytest -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs`，退出0。

执行日志暂存 `/tmp/task8a9-5Ibcv05j/`，b1/b2/b3-suite.log、b4-installed.log。所有 HTTP 测试仅模拟第一阶段，不将这些结果称作 Hunyuan3D GPU E2E。人工外观 pending、宿主 pending、机器人安全 not_validated；default preserve/full 未改变。

## 使用与边界

完整命令见 [CHAIN.md](../usage/CHAIN.md)。未开展 CoACD、复杂质量积分、孔洞专项、真实宿主接入、新服务或参数扫描。工程候选仍仅 static+hull；第二阶段失败保持第一阶段成功来源，超时结果 unknown，不自动再次生成。

本轮最终整体审核与保护核对在同轮总验证记录补充；此报告不会给历史包或真实生产资产写人工 approved。
