# M1.1 验收补强与接触穿透诊断报告

日期：2026-09-11。范围严格限于本轮用户审核的四项补强，未重做上一轮八项修复，未进入任务8/9。

## 1. 结论与版本

**软件修复/诊断完成，真实资产自动验收未通过。**

| 独立结果 | 本轮实测 |
|---|---|
| 软件回归 | 安装包模式107 passed、1 skipped，13.49 s，退出0 |
| benchmark异常隔离专项 | 7 passed，2.89 s，退出0 |
| 真实资产验收 | failed，命令退出5；compile/render/migration通过，native失败 |
| 受控benchmark | passed，仅独立诊断，不决定physics |
| 控制变量诊断 | 8组全部完成；命令退出0仅表示实验执行完成 |
| 人工外观审核 | pending |
| 真实宿主集成 | pending，未在真实ACS场景运行 |

起始提交：66bd6bcdf1a310e3d531436435c85db1a8c39eac，分支main。
远端：https://github.com/gungnir33/3D-Assets-Mujoco.git。
本轮最终生产代码：5409a3d7b70bb14e3bf26e139e87c4b74cd51936；其后仅文档/机器证据提交，最终交付HEAD见终端最终报告，避免在提交内循环引用自身SHA。

环境：/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild。
Python3.10.21；asset-mujoco0.1.0；MuJoCo3.4.0；trimesh4.7.4；numpy2.2.6；Pillow11.3.0；pydantic2.11.7；scipy1.15.3；pytest8.4.1。
无依赖升级。起始默认导入旧site-packages，开发显式PYTHONPATH=仓库/src；最终仅用pip --no-deps --no-build-isolation重新安装本项目。以python -I核对安装目录的全部16个.py文件与源码SHA256一致，排除运行旧代码。

机器证据：[M1_1_CONTACT_DIAGNOSIS_EVIDENCE.json](M1_1_CONTACT_DIAGNOSIS_EVIDENCE.json)，含版本/保护快照、测试原文、真实验收结果、8组诊断摘要和输出哈希核对。旧报告不改写。

## 2. benchmark隔离：复现、修复和测试矩阵

起始实现先运行native、再运行benchmark，最后才返回结果供pipeline保存；benchmark异常会丢失native独立结果。新增5项初始回归全部失败后修复，另补两种证据I/O测试。

新顺序：native运行 → physics_native_evidence.json → 独立physics层哈希 → validation_report → benchmark运行/异常记录 → benchmark_evidence.json → physics_evidence.json汇总。
新physics层仅绑定编译资源、native fixture（如已生成）及native结果；context.native_evidence指定独立文件。汇总和benchmark文件不参与新native哈希，旧包仍按已有绑定核对，不重签。
可恢复异常记录stage/type/message/已有diagnostic_files。native异常形成失败证据，不能由benchmark修复；benchmark异常不改变native状态或原始失败原因，后续full渲染仍执行。
证据写入/哈希读取I/O错误为EVIDENCE_IO_ERROR，阻止发布。已持久化的native通过仍是有效的局部事实，但不等于整个包成功发布；二次failure.json写失败不遮蔽原I/O错误。

| 故障矩阵 | 测试（tests/integration/test_benchmark_isolation.py） | 实测断言 |
|---|---|---|
| A native passed + benchmark异常 | test_benchmark_exception_keeps_native_and_render[True] | benchmark启动前已可校验；native passed保持，异常单列，render passed |
| B native failed + benchmark异常 | 同上[False] | 保留原penetration原因，physics failed，render passed |
| C native failed + benchmark passed | test_normal_benchmark_does_not_cover_native_failure | physics仍failed，不发布成功 |
| D native异常 | test_native_exception_keeps_compile_never_passes | native failed，compile/render保留passed，无伪造physics passed |
| E benchmark正常 | 正常组合及原native/layered_evidence回归 | 正常结果、hash核对无回归；benchmark文件后来改变不使新native证据失效 |
| native结果写入故障 | test_evidence_io_failure_is_not_physics_failure | EVIDENCE_IO_ERROR；没有成功目录，compile保留 |
| benchmark结果写入故障 | test_benchmark_persistence_failure_keeps_native_but_blocks_publish | native证据保留passed，但不发布 |
| hash读取故障 | test_hash_persistence_io_error_does_not_relabel_physics | 明确I/O错误，不将未保存物理层改算failed |

Mock仅在异常注入/调度边界使用；native通过测试仍调用真实引擎，仅在合成夹具指定温和起点。真实企鹅验收与下面实验没有使用这类测试替身或修改起点。

## 3. 回归与真实验收分离

原test_real_m1改名test_real_asset_native_failure_is_reported，继续验证已知超限时正确报错、编译/渲染/证据保留、不发布。该pytest通过只证明失败处理正确。

新增独立命令：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -B \
  -m asset_mujoco.acceptance \
  --output /home/mcl/workspace/3D-Assets-Mujoco/outputs/contact_diagnosis
```

默认输入为指定原始GLB，不读取已有OBJ冒充转换；可显式--input指向GLB。缺输入返回REAL_INPUT_UNAVAILABLE / not_executed / 退出2。正常验收直接要求compile/native/render通过、迁移重载和源哈希核对通过才退出0。捕获ValidationFailed仅保留路径以继续迁移诊断，不会改为成功；没有pytest.raises/xfail机制。

本轮安装包模式命令实际退出5，2.570671879919246 s。两份XML各在原目录和迁移目录执行MjModel.from_xml_path+mj_forward。EGL四图通过、migration passed、native failed，人工/宿主pending。
验收目录：outputs/contact_diagnosis/acceptance-jiw7b14f。
新诊断包：该目录下packages/.staging-svydizf5。
迁移副本：该目录下relocated_package。
包指纹：44557a9322ecd0c4a52f2cec700a5957f4cdde5743a785e04d5c002817b6306a。
先前源码模式acceptance-bu_h80uw同样保留，不覆盖。

最终软件回归命令（不是资产验收命令）：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -B -m pytest \
  -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs
```

结果107 passed, 1 skipped in 13.49s，退出0。唯一skip为OSMesa OpenGL loader glGetError不可用；EGL实际渲染通过。pip --no-cache-dir check退出0，No broken requirements found。未修改系统驱动。

## 4. 冻结基线与采样时刻

输入/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb，SHA256=12f1ed66a874efbdb3c350d819c1f6e076de469e7dc191d236de82073fdd2e12。
历史outputs/penguin_m1_1_20260911_final/.staging-396kwwx1只读；所有文件前后hash一致。诊断从本轮重新转换的包复制资源，历史目录未写入trace。

基线仍为source_up=y、yaw=180°、scale=.5、static+hull、Euler、dt=.002 s、1000步/2秒；probe质量.1 kg、半径.02494276911020279 m、起点[0,0,1.2221956863999368] m。
原始双方solref=[.02,1]、solimp=[.9,.95,.001,.5,2]、priority=0、solmix=1、摩擦[1,.005,.0001]、碰撞位1/1，未添加pair或override；5mm阈值不变。

追踪模块使用mj_step1缓存积分前qpos/qvel/energy、接触点/法向/Jacobian点速度，mj_step2得到该次求解qacc和mj_contactForce。只支持并明确检查本基线Euler路径，不悄悄改变积分器。积分后qpos_after/qvel_after/integrated_time单列，不追加mj_forward改变warm-start。
第k行step=k，sample_time=(k-1)dt；接触/法向相对速度/力属于此时间的同次求解，不使用积分后的速度冒充接触前速度。contact force为接触坐标系[法向,切向1,切向2]力/力矩，并记录转到世界系作用于geom2的力。相对法向速度=(v_geom2-v_geom1)·n，负数表示趋近。

| 基线事件 | 步 | 积分前采样时间(s) | 该步积分后时间(s) |
|---|---|---|---|
| 首次接触 | 144 | .286 | .288 |
| 首次超过5mm | 146 | .290 | .292 |
| 最大穿透11.795154509838177mm | 153 | .304 | .306 |

本轮重测70条目标接触记录；这是累计记录数，不是70次独立撞击。首次接触法向相对速度-1.8133971130670752 m/s；首次已进入1.190423480125262mm，之后继续压入至第153步最大值。峰值法向力19.033929188608848 N。
所有1000行都有状态/时间检查，即使无接触；qpos/qvel/qacc/energy均有限，warning8项全0。contact_exists=true、numerically_stable=true、threshold_passed=false，三者独立。

## 5. A–D控制变量实验

命令：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -B \
  -m asset_mujoco.contact_diagnostics \
  --package /home/mcl/workspace/3D-Assets-Mujoco/outputs/contact_diagnosis/acceptance-jiw7b14f/packages/.staging-svydizf5 \
  --output /home/mcl/workspace/3D-Assets-Mujoco/outputs/contact_diagnosis
```

本轮安装包实测目录：outputs/contact_diagnosis/diagnostic-qjpq4_fb（下表路径均相对此处）。源码模式diagnostic-9ge6nsg2亦保留，两次各组最大穿透完全一致。运行前保存experiment_plan.json，基线与新native结果在1e-10m内一致且首次接触步相同后才扫描；基线不一致测试证明会停止。
每组都有fixture.xml、experiment_config.json、contact_trace.jsonl、contact_summary.json、output_hashes.json。资源引用相对化；输入资源/配置/trace/summary全部哈希，末次逐文件重新核验全通过。全部组标记diagnostic，不能代替正式physics证据。

| 实验目录/唯一改动 | 步数 | 首次接触时间(s) | 首次超限/最大穿透步 | 最大穿透(mm) | 峰值法向力(N) | 诊断5mm |
|---|---:|---:|---|---:|---:|---|
| baseline：无改动 | 1000 | .286 | 146 / 153 | 11.795155 | 19.033929 | 未达标 |
| A_dt_001：dt=.001 | 2000 | .286 | 291 / 306 | 12.419782 | 17.973772 | 未达标 |
| A_dt_0005：dt=.0005 | 4000 | .2865 | 580 / 613 | 13.334978 | 18.815115 | 未达标 |
| B_tangent_plane：解析切平面 | 1000 | .286 | 146 / 153 | 11.795155 | 19.033929 | 未达标 |
| C_timeconst_01：仅solref[0]=.01 | 1000 | .286 | 148 / 148 | 5.085267 | 38.060718 | 未达标 |
| C_timeconst_006：仅solref[0]=.006 | 1000 | .286 | 无 / 146 | 2.376893 | 64.355655 | 仅诊断达标 |
| D_d0_095：仅solimp[0]=.95 | 1000 | .286 | 146 / 153 | 11.795155 | 19.033929 | 未达标 |
| D_dwidth_099：仅solimp[1]=.99 | 1000 | .286 | 146 / 153 | 11.768955 | 19.059291 | 未达标 |

各组总时长均2秒（浮点累积误差<2e-13秒）、数值稳定、warning全0；不是只保留最好的组。

A保持几何、质量、初态、接触配置一致。小dt没有消除超限，当前三点不足以证明严格收敛，但排除了“只减小dt就能解决当前5mm失败”的简单解释。

B将碰撞几何替换为经过基线首次接触表面点[-.0000035532580854,.0181243105705,.802828666832] m的解析无限平面，外法向[.0001495960921,-.763053504389,.646335305442]。同一probe/重力/起点，实测首次法向入射速度匹配至数值误差。峰值穿透与真实凸包差约1.9e-16m。无限平面不含有限轮廓/曲率，后续滑动接触累计207条而非70条，故只据此判断初次压入，不声称全程轨迹/几何等价。

C固定solimp和其余条件，双方geom只同时改变solref的timeconst；实际contact.solref分别为[.01,1]和[.006,1]。D固定solref=[.02,1]，实际contact.solimp分别为[.95,.95,.001,.5,2]和[.9,.99,.001,.5,2]。这样控制实际目标接触的单个参数，不使用强制pair；probe与后续ground的混合也可能改变，未来仍须检验二次接触。

参数语义/稳定性/混合规则来自锁定版[MuJoCo3.4建模说明](https://mujoco.readthedocs.io/en/3.4.0/modeling.html#solver-parameters)：正solref含时间常数和阻尼比；timeconst不宜小于2dt，refsafe保持启用。本轮最小.006>2×.002，不作无限减小搜索。同优先级采用solmix加权，故仅改资产一侧不保证实际解析值相同；更高priority的行为需另审。D仅改初始阻抗影响小与首次接触已超过.001m过渡宽度相符，但不据此宣布所有速度/尺度下solimp都不重要。
采样实现参照[目标版仿真循环](https://mujoco.readthedocs.io/en/3.4.0/programming/simulation.html#simulation-loop)及[接触力API](https://mujoco.readthedocs.io/en/3.4.0/APIreference/APIfunctions.html#mj-contactforce)，并以解析夹具逐步对照原mj_step得到相同最大穿透及事件步。

## 6. 诊断结论与待批准建议

证据最支持：该入射工况下的软接触响应是当前穿透的主要影响因素，时间离散影响数值但减小dt未改善；简单解析表面复现了相同峰值，不支持把本次超限归咎于网格损坏、坐标转换或碰撞检测完全失效。仍未排除其他姿态、边缘、多点接触、不同质量/尺度及宿主求解设置下的几何和离散影响，不声称唯一根因已完全确定。

5mm要求目前只对应：.1kg、半径约24.943mm球形探针、上述落点和斜面法向、约1.8134m/s法向入射、dt2ms、2秒观察窗口、当前摩擦/求解器和static凸包。它不是任意碰撞速度/尺寸下的普遍保证。

建议用户批准后才引入**显式、可选的工程接触配置**，保留原默认配置和历史失败记录。最小候选是目标接触实际solref=[.006,1]，solimp仍为[.9,.95,.001,.5,2]；目前仅单样例诊断证据，峰值法向力升至64.36N（约3.38倍），不能立即作为生产默认或真实材料参数。

下一阶段最低要求：

1. 先确定应用可接受的力峰值/冲量、反弹及穿透，增加不同入射速度、角度、探针质量/半径、解析几何与其他资产回归，包含自由刚体和二次ground接触；对候选再次做dt敏感性检查。
2. 配置显式写入交付XML和manifest，记录实际接触解析值及适用工况。只给资产geom填.006但另一侧保持.02/同priority，会混合为.013，不能沿用本轮双方.006的结论。
3. 在双方一致参数的集成契约与明确的资产priority策略之间做用户审核决策；后者还可能影响其他接触参数，不能悄悄修改宿主。未知宿主组合报告未验证/冲突，不承诺普遍兼容。
4. 原生验收测试交付配置，不在验证器覆盖、不加pair掩盖碰撞位错误。新配置创建新包、新hash和新证据；人工审核仍须用户提交。

本轮未新增profile，未改变正式solref/solimp、priority、solmix、摩擦、探针条件、阈值或mjcf.py。实验C通过不改算原始配置通过；等待用户批准再实施正式配置。

## 7. 保护核对、提交与文件

第一阶段前后HEAD=c78d96ea41a692917918af3d9ce4d3821be64f2b，git status均空。原始GLB hash相同；历史M1.1包全19文件hash逐项相同。没有调用第一阶段生成、修改权重/Skill/环境/驱动；未假称对全部权重重新做全量hash。
用户原有outputs/.gitkeep删除与未跟踪审核指令保留；历史报告、旧outputs、example_outputs均未改。新增输出仍ignored，不提交大trace/模型，也不push。

本地代码阶段：efd00fe（native立即持久化/benchmark隔离）；c88c075（独立验收与回归分离）；a512e37（hash I/O分类）；5409a3d（独立trace与8组诊断）。后续文档提交只更新本报告、机器证据、实施清单、README及受影响设计契约。
修改生产模块validation.py/pipeline.py/manifest.py，新增acceptance.py/contact_diagnostics.py；新增对应故障注入、验收入口、诊断测试，原真实资产回归只重命名。没有转换主体重构。
临时原始运行日志：/tmp/mujoco-contact-diagnosis-txK7uw；关键内容已汇入机器证据，临时目录以后可能被系统清理。

到此停止：软件修复/诊断完成，真实资产自动验收未通过；人工审核pending，真实宿主集成pending。等待用户确认是否开展正式接触配置。
