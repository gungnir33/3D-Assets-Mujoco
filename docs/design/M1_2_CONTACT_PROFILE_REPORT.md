# M1.2 显式工程接触配置与受限验收报告

日期：2026-09-14。只实施第二阶段，不进入任务8、9，不自动push。

## 1. 结论与独立状态

软件实现与受限验证完成。**engineering_static_v1 仅在本文指定的企鹅资产—探针工况下通过自动验收；不代表全部接触过程或任意宿主达标。**

| 对象/配置 | 本轮结果 | 限定说明 |
|---|---|---|
| 软件回归 | 119 passed、1 skipped，退出0 | 安装包模式；OSMesa不可用，EGL通过 |
| preserve | compile/render/迁移通过；native失败，退出5 | 资产接触11.795155mm > 5mm，未发布成功包 |
| engineering_static_v1 | compile/native/render/迁移通过，退出0 | 资产接触2.376893mm < 5mm；配置双方一致 |
| candidate 后续ground接触 | failed | 8.960727mm > 5mm；不是基线资产接触门槛，不隐瞒失败 |
| 单方参数不匹配 | failed | 实际solref=.013，资产穿透7.082761mm |
| 人工外观审核 | pending | 未自动批准 |
| 真实宿主集成 | pending | 未修改、未在ACS等真实宿主验证 |
| 材料/机器人安全 | not_validated | application_force_limit=not_specified |

默认仍为preserve；候选没有成为全局默认。不能声称“M1.2全部通过”、真实材料已标定或机器人接触安全已验证。

## 2. 基线、提交与环境

- 仓库：`https://github.com/gungnir33/3D-Assets-Mujoco.git`；路径 `/home/mcl/workspace/3D-Assets-Mujoco`；main。
- 起始HEAD：`c8690d1fff45f57047f6402e6108f93c512b8594`。起始仅未跟踪 `PHASE2_M1_1_CODEX_FIX_INSTRUCTIONS.md`，一直保留、不提交。
- `00ddbb8`：可选双方接触配置与只读统计；`3c475ac`：显式验收及固定扩展实验。
- 最终受测源码：`cdf39ba9d131b735572a2a74767410c5e9d2ae2d`，包含诊断执行完整性修复；之后仅提交证据与文档。
- `cfa5e54`：本轮新输出与失败证据。最终文档提交位于该提交之后，可用 `git log -5` 核对；本文不尝试自包含自身提交SHA。
- 指定环境：`/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild`。Python3.10.21，MuJoCo3.4.0，trimesh4.7.4，numpy2.2.6，Pillow11.3.0，pytest8.4.1，pydantic2.11.7，scipy1.15.3。
- 本轮只以 `pip install --no-deps --no-build-isolation .` 重装项目，未升级依赖。19个源码模块与实际site-packages SHA256逐一一致。之前环境重建证据仍是历史证据；本轮没有声称又创建全新环境。

## 3. 实现契约

`ConversionRequest`、CLI及default.yaml一致：`contact_profile=preserve`。可选 `engineering_static_v1` 只允许static+hull，free/none等请求明确拒绝。

选定候选时，导出资产 `asset_collision` 显式 solref=[.006,1]、solimp=[.9,.95,.001,.5,2]。scene.xml中的ground采用同一公开约定；另导出 `contact_scene.xml`，含原条件probe并显式采用同参数。native只读取交付场景，生成的physics_native.xml不含pair，不开启override，不在运行时修改接触参数。没有改变摩擦、碰撞位、priority、solmix、基线探针、dt或阈值。

conversion_manifest声明配置来源、参数、使用对象和runtime_resolution_manifest。contact_result_manifest记录实际geom参数、接触解析值、接触统计、acceptance_scope和followup_ground，绑定physics证据。公开contact_scene及引用资源绑定compile层。benchmark仍独立且非强制，不能覆盖native失败。改场景或结果清单使相应旧证据失效，原样迁移不失效。

双方不匹配单元/集成实验：probe.solref=.02而资产=.006时，实际[.013,1]；probe.solimp的d0=.8而资产=.9时，实际d0=.85。native明确失败并记录实际值。未用priority强制覆盖。不得将model.xml放入默认宿主后直接宣称延续本报告的通过结论。

修改模块：contracts/cli/config、contact_profiles、mjcf/pipeline、validation/manifest、contact_statistics/contact_diagnostics、acceptance/profile_diagnostics及对应测试、必要文档。原18章设计和10项任务结构保留；未重做上一轮八项修复。

## 4. 测试与安装证据

先红后绿：新增配置测试最初6项失败（旧请求缺字段），统计测试缺application_force_limit失败，验收入口不认识--contact-profile退出2，扩展入口缺模块失败；随后分别修复并通过。新增范围断言最初缺acceptance_scope失败，修复后通过。独立只读审核未发现Critical/Important，发现诊断异常入口仍返回0及成功状态未回写的Minor；追加故障注入重现main返回None，修复为completed_with_errors/退出5，保留后续组并统一写入summary，复核通过。物理阈值未达标但执行正常仍退出0，二者不混淆。

| 测试文件 | 本轮覆盖 |
|---|---|
| test_contact_profiles.py（8项） | 默认/受限模式、公开参数、solref/solimp不匹配实际解析、碰撞位清零、碰撞体移走且探针不重新瞄准、两类新增证据篡改失效 |
| test_contact_statistics.py | 真实解析地面接触、逐记录Fn×dt独立求和、峰值力、分离速度、世界冲量、无应用力限 |
| test_acceptance_entry.py | 原失败入口保留；新增候选成功、三份XML迁移、范围、人工/host pending |
| test_profile_diagnostics.py（2项） | 执行错误非零退出、保留后续组、每组状态持久化；固定8组、2秒时长、dt步数、质量/半径对应惯量、实际混合、包哈希不变 |
| 原有回归 | benchmark异常隔离、失效证据、资源边界、法线、材质、真实失败处理等全部保留 |

全量初次出现的唯一失败是旧test_ignore_scope仍要求忽略outputs，与用户已经取消忽略的起始仓库状态冲突。只更新该断言并增加real_inputs/secrets/.env/envs/.venv排除断言，未修改.gitignore、删测试或放宽物理阈值。

最终命令（PY为上述环境的bin/python；从repo执行pytest，从/tmp执行其他-I命令）：

```bash
env PYTHONNOUSERSITE=1 "$PY" -m pip install --no-deps --no-build-isolation .
"$PY" -I -m pip check
env -u PYTHONPATH PYTHONNOUSERSITE=1 "$PY" -B -m pytest \
  -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs
```

实际：pip check退出0，`No broken requirements found.`；pytest退出0，`119 passed, 1 skipped in 24.56s`（命令墙钟24.758s）。OSMesa跳过原因：OpenGL loader的glGetError为None；EGL真实渲染通过。没有调整系统驱动。stdout/stderr分开保存在最终证据目录；freeze未混入警告，版本与起始快照一致，锁文件没有升级。

## 5. 正式包的本轮真实重测

只读原始GLB：`/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb`。

输入SHA256：`12f1ed66a874efbdb3c350d819c1f6e076de469e7dc191d236de82073fdd2e12`。

固定：source_up=y、yaw=180、scale=.5、static+hull，Euler dt=.002，1000步/2秒，5mm阈值。probe质量.1kg、半径.02494276911020279m、初始位置[0,0,1.2221956863999368]、初速度0；均与preserve相同。显式倍率不是实测尺寸，physical_scale_verified=false。

最终证据根：`outputs/m1_2_final_6im5gku8`（以下路径相对此根）。每个acceptance入口都重新读取原GLB，不复用诊断OBJ替代输入。

| 指标 | preserve | engineering_static_v1 |
|---|---:|---:|
| 命令退出码 | 5 | 0（仅既定资产工况） |
| 总命令耗时s | 3.426 | 3.645 |
| 资产首次接触步 | 144 | 144 |
| 首次超限步 | 146 | 无 |
| 最大穿透步 | 153 | 146 |
| 最大穿透mm | 11.795154510 | 2.376892611 |
| 峰值法向力N | 19.033929 | 64.355655 |
| 累计法向冲量N·s | .267321108 | .261378073 |
| 接触期间最大分离速度m/s | .218501725 | .156599028 |
| warning计数 | 8项全部0 | 8项全部0 |
| benchmark穿透mm（独立） | 1.190423480 | 1.190423480 |

first_contact时间为积分前t=.286s；preserve首次超限t=.290s、峰值t=.304s；candidate峰值t=.290s。数据采样为step1的积分前位置/速度/接触与同次step2求解的力，积分后状态单列。接触记录数不是撞击次数。法向冲量为2秒窗口中每条接触Fn×dt之和；世界矢量冲量作用对象为probe，不把含持续支撑阶段的冲量解释为单次撞击冲量。分离速度只描述接触过程中的法向反向运动，不推断材料恢复系数。

候选原生接触的实际solref=[.006,1]、solimp=[.9,.95,.001,.5,2]。摩擦、priority=0、solmix=1保持原值。没有应用力限，峰值增大不能解释为“更安全”。

两个正式XML均真实MjModel.from_xml_path及mj_forward通过；候选公开contact_scene亦通过。两配置均EGL front/side/iso/collision四视图成功。原包和relocated_package均编译及forward，fingerprint和checked_report相等，分层evidence_issues为空。候选实验完成后再次核对原包指纹不变。

- preserve失败包：`preserve/acceptance-k618ipak/packages/.staging-wyvumrco`；保留失败、不发布。
- preserve指纹：`9b24cd723207dbb21341ef54eaba82366c1a2b9615baa1a27496ac06080fbc2d`。
- 候选包：`engineering_static_v1/acceptance-5ljztt1b/packages/penguin_fb9002dbf5e8`。
- 候选指纹：`cad53a20ddbf76b84fa400ea8b9e452aee85618dea94564122276b2cb6740e5e`。
- `preserve_trace/`：新基线逐步trace，与native峰值一致；没有写入旧历史包。
- `final_evidence.json`：完整命令、退出码、耗时、环境、安装哈希、原始/候选/实验结果、保护快照。
- `output_hashes.json`：最终证据根所有既有文件的相对路径及SHA256（不含其自身）。各实验也有独立hash清单。
- `outputs/m1_2_20260913` 和 `outputs/m1_2_final_f563mbgm` 是最终审核修复前的本轮早期证据，保留供追溯，最终结果以上述final根为准。

## 6. 固定扩展组：全部为diagnostic

入口：`python -I -m asset_mujoco.profile_diagnostics --package <上述候选包> --output <新父目录>`。本轮退出0、3.636s；退出0表示实验完成，不表示所有工况达标。

路径：`experiments/profile-diagnostic-zmgx_86m/`；事先保存experiment_plan.json。每组有fixture.xml、experiment_config.json、逐步contact_trace.jsonl、contact_summary.json、output_hashes.json。先重跑候选baseline并核对正式native，匹配后才继续。时长均2秒；无pair/override，全部warning为0、逐步数值与时间检查通过。

| 子目录/单变量 | dt/步数 | 资产穿透mm | 资产峰值力N | 资产法向冲量N·s | 地面穿透mm | 5mm比较（资产/地面） |
|---|---|---:|---:|---:|---:|---|
| baseline | .002/1000 | 2.376893 | 64.355655 | .261378 | 8.960727 | 通过/失败 |
| dt_001 | .001/2000 | 3.042328 | 59.073187 | .261319 | 7.381737 | 通过/失败 |
| dt_0005 | .0005/4000 | 3.949255 | 62.737371 | .261107 | 7.543222 | 通过/失败 |
| analytic_plane | .002/1000 | 2.376893 | 64.355655 | .436230 | 4.258726 | 通过/通过 |
| offset_x_005：x+0.05m | .002/1000 | 2.371260 | 64.334877 | .254779 | 4.784913 | 通过/通过 |
| mass_02：质量.2kg | .002/1000 | 2.376893 | 128.711309 | .522756 | 8.960727 | 通过/失败 |
| radius_12：半径×1.2 | .002/1000 | 3.470353 | 67.715617 | .261473 | 8.993121 | 通过/失败 |
| counterparty_mismatch：probe .02 | .002/1000 | 7.082761 | 29.205162 | .263306 | 13.782234 | 失败/失败 |

解析对照为首次接触点的无限切平面，不是原企鹅的曲率/有限边界；初次法向入射速度约-1.813397m/s匹配，但后续运动不同。质量/半径组更新对应球体显式惯量，未移动初始位置以补偿半径。非全排列、没有无限参数扫描；所有失败保留，诊断结果不修改正式dt或状态。

## 7. 后续地面接触与适用范围

preserve地面首次接触324步，最大332步，穿透28.798826mm。候选地面首次319步(t=.636s)，最大320步(t=.638s)，穿透8.960727mm；实际参数也是[.006,1]和相同solimp。入射法向速度-3.864888m/s，峰值149.705839N，法向冲量1.724572790N·s，接触期间最大分离速度.594897m/s。候选地面接触区间319–328、378–1000步，说明分离后再接触；这不是材料弹性标定。

证据支持：候选改善了指定资产接触工况，较小dt仍有非零差异，不能视为已完成时间收敛；更快的后续落地在相同参数下仍超限。解析切平面初次峰值相同，不能把现象简单归因于网格转换损坏；偏移落点影响后续轨迹和接触采样。质量加倍使峰值力、冲量约加倍，穿透未变化，不能据此泛化质量无影响。没有足够证据将离散时刻、接触响应及几何轨迹贡献完全分离。

建议保持候选为受限可选配置，不推广为默认。若应用要求包括后续落地、任意入射方向或机器人交互，先由用户明确速度/质量/尺寸范围、允许穿透及应用力限，再另行批准工况验证或配置设计。本轮不继续调参，也不自动新增第二个profile。工程参数不是测得材料参数；任何宿主采用都需要显式双方契约及新的包、hash和原生证据。

## 8. 保护边界与结束条件

第一阶段HEAD前后均 `c78d96ea41a692917918af3d9ce4d3821be64f2b`、工作区均干净。原GLB SHA相同；历史 `outputs/penguin_m1_1_20260911_final/.staging-396kwwx1` 的19个文件逐一哈希相同；起始依赖版本与最终相同。第二阶段仅新增本轮输出，旧证据不覆盖；没有修改第一阶段代码/Skill/权重、hunyuan3d/acs_test/sim_test环境或系统驱动，没有调用第一阶段生成。

本轮源码、必要测试/文档和新输出分阶段本地提交；remote不变，未push。人工审核与真实宿主集成pending，任务8/9未开展。工作在此停止，等待用户决定下一步是否补充应用工况或进行宿主集成。
