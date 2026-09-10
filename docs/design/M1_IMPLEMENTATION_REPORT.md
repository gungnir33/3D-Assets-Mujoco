# R3 契约修订与 M1 实施证据

日期：2026-09-10。只实施第二阶段；没有 push，没有调用第一阶段生成。
R2 的18章、10项任务保留；本文区分实际通过、保守拒绝和未验证。

## 六项契约对照

| 审核项 | 原章节 | 修订与实现 | 测试/状态 |
|---|---|---|---|
| physics not_applicable | 13、任务1 | 明确枚举，VISUAL_ONLY 序列化与聚合 | test_contracts 通过 |
| static 惯量可空 | 4、9、任务1 | static 可省略；free 强制正质量及策略 | test_contracts 通过 |
| 分离容差、0.13m、uniform | 6、9、任务1–2 | 目标2%+1e-7m；几何1e-6/1e-7m；惯量1e-8/1e-12；单一最小二乘比例 | test_scene_transform、test_inertia 通过 |
| 当前资产物理证据 | 13、任务7 | 当前包资源哈希、具体碰撞geom对、逐步仿真；修改资产使旧证据失效 | test_m1_real_asset、test_cli 通过 |
| 人工审查持久化 | 13–14 | appearance_review.json、图片与包哈希、历史、每次 report 重算 | test_review 通过；真实人工审核 pending |
| 平面零尺寸和范围 | 5、16 | 平面可进入编译判定；非空三维碰撞另检查；任务8孔洞属已规划后续 | 平面变换及真实编译矩阵通过 |

## 仓库与环境

- root：/home/mcl/workspace/3D-Assets-Mujoco
- origin：https://github.com/gungnir33/3D-Assets-Mujoco.git
- Python/package/env：3.10.21 / asset_mujoco / asset_mujoco
- 转换验证 MuJoCo：3.4.0；锁文件 requirements.lock.txt。
- 未安装 torch，不 import local_3d_agent，测试确认与第一阶段环境隔离。
- 第一阶段 HEAD c78d96ea41a692917918af3d9ce4d3821be64f2b、工作区干净；三份源 GLB 哈希前后不变，见 environment_baseline.json。
- 本地分阶段提交：4dcbe12、caabc62、71d186b、bb3c5d7、4d780d2、a496608、9146b62、7e54c95；最终文档提交另见 git log。

## 实施范围

| 任务 | 本轮证据 |
|---|---|
| 1 | 独立仓库/Conda、配置契约、状态与审核哈希、锁版本、忽略规则与冻结基线 |
| 2 | 原始GLB预检、资源越界检查、Scene展开、轴向/yaw/尺度；不支持特性明确拒绝 |
| 3 | 四类网格×默认/shell，在转换环境与两处宿主库真实编译+forward，JSON矩阵归档 |
| 4 | 不焊接视觉网格的OBJ/PNG导出、UV保留、纯色纹理与factor测试、EGL四色探针 |
| 5 | 全部原始顶点凸包、box惯量、supplied惯量校验与真实张量重建 |
| 6 | static/free XML、同盘staging和禁止覆盖原子发布、迁移重载、非默认宿主冲突测试及最小合并示例 |
| 7 | 当前资产接触、能量/autoreset/每步状态、独立渲染、M1真实资产测试、CLI及分层报告 |
| 8–10 | 未开展复杂策略、HTTP串联与三份真实资产全面验收 |

这不是宣称所有输入类型或 R2 所列全部扩展用例均已覆盖。当前已测试支持面以本报告和测试为准；例如显式 minFilter/magFilter 暂时拒绝，非默认UV/扩展PBR也不支持，不静默降级。

## 任务3：版本分层结果

见 visual_mesh_compatibility.md 与 compile_*.json。
3.4.0平面默认体积检查失败，shell可编译；3.2.3平面默认可编译但shell属性语法不支持。
单三角形不足4顶点，两版失败，尚未实施细分适配，绝不加厚/删面。
编译矩阵不代表渲染或接触效果已验证。

## M1 当前真实输出

源：/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb

输出：/home/mcl/workspace/3D-Assets-Mujoco/outputs/penguin_m1_1fd1864a5e55

参数：source_up=y、yaw_deg=180、scale=0.5、static+hull、validation_level=full。
资产实际为举 HY3D 标牌的企鹅，不是机器人。0.5是演示比例，并非测得真实尺度。

实际命令：

```bash
env PYTHONPATH=src /home/mcl/anaconda3/envs/asset_mujoco/bin/python -B \
  -m asset_mujoco.cli convert \
  /home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb \
  --output /home/mcl/workspace/3D-Assets-Mujoco/outputs \
  --name penguin_m1 --source-up y --yaw-deg 180 --scale 0.5 --validation-level full
```

实际 stdout：

```json
{"status":"PHYSICS_VALIDATED","compile":"passed","physics":"passed","render":"passed","appearance_review":"pending"}
```

| 独立验收层 | 结果与证据 |
|---|---|
| 自动编译 | model.xml、scene.xml真实编译及mj_forward通过 |
| 当前资产物理 | 1000步，dt=.002，time=2.0000000000000013；具体pair=asset_collision/probe |
| 接触 | 48次，首次第144步，最大穿透0.001190423480125262m；warning全部0 |
| 原生渲染 | EGL通过，front/side/iso/collision四张512²预览 |
| 贴图保留 | 源与导出2048×2048 RGB贴图逐像素相同；顶点/面数保持 |
| 可移植性 | test_m1_real_asset复制整个包到另一个目录，两份XML再次加载通过 |
| 人工外观 | pending，未填写approved，不能FULLY_VALIDATED |
| 候选宿主编译 | 3.2.3及3.4.0，两份XML都compile+forward通过，见m1_host_compile.json |
| 实际宿主集成 | pending：用户尚未指定最终ACS场景；未改宿主、未在真实宿主执行物理/渲染 |

本次持久化输出耗时2.337689268984832秒（conversion.log），不是GPU生成耗时；未采集峰值GPU显存，不捏造该指标。
M1自动闭环已跑通；自动、人工和宿主集成结果必须分开引用。

## 数值与失败证据

- 默认接触参数曾产生约13.5mm的箱体探针穿透、约11.8mm的真实资产探针穿透，均失败而未发布。
  调整的是独立验证fixture的solref=[.004,1]、solimp=[.99,.99,.001]，原阈值未放宽；这些参数写入physics_evidence.json。
  这不保证任意宿主接触参数也满足相同穿透界限。
- 512像素渲染初次超过480默认帧缓冲，回归失败后在自建scene.xml显式设置512；不修改宿主。
- 非对角fullinertia重建误差约1.52e-7。显式特征分解输出diaginertia+quat后通过原1e-8/1e-12重建阈值。
  COM未重复变换，见test_supplied_compiled_tensor。
- OSMesa探测失败：OpenGL加载时NoneType.glGetError。EGL通过，未安装OSMesa系统依赖。

## 测试证据与未验证范围

```text
python -B -m pytest -p no:cacheprovider -q -rs
56 passed, 1 skipped in 4.78s
git diff --check
exit 0
```

跳过仅OSMesa后端。真实资产测试当前已执行；其他机器没有输入时该测试会明确skip，不能据此声明M1通过。

尚未验证/实现：

- 人工审核、真实目标宿主场景合并后的物理和渲染。
- OSMesa可用性、非默认纹理过滤器、所有材质组合的跨版本原生渲染。
- 体积质量积分、CoACD、supplied碰撞代理、真实孔洞探针路径（hole_validation=not_tested）。
- HTTP串联和三份资产的任务10全面验收。
- 项目自身LICENSE仍待选择；不更改任何上游许可证。

下一步是检查现有预览并明确目标宿主，不能把当前结果称为FULLY_VALIDATED或全部第二阶段部署完成。
