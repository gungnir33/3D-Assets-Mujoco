# M1.2 发布门槛与渲染异常状态同步修复报告

结论：**发布门槛与渲染异常状态同步修复完成。** 这是软件控制流与状态/证据修复，不表示地面工况达标、人工审核通过、真实宿主兼容或机器人接触安全已验证。

## 1. 当前基线与实际环境

- 起始 HEAD：`75b7a7aeadbfed048b4d8d2c4ec800cbfc4cc28c`，main。
- 最终实现/实测 HEAD：`f1b91b05f310a6f906a92df542956bcd86774d9a`；之后仅文档和新证据归档。归档提交使用 `git log -1 -- docs/design/M1_2_PUBLICATION_STATE_FIX_REPORT.md` 查询，避免文档自引用提交哈希。
- origin：`https://github.com/gungnir33/3D-Assets-Mujoco.git`。本轮未 push。
- 原工作区仅 `PHASE2_M1_1_CODEX_FIX_INSTRUCTIONS.md` 未跟踪，保持不动、不提交。仓库和 tasks 下未发现本轮可选补充指令/复现ZIP。
- 解释器：`/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python`，Python 3.10.21。
- 实际导入：该环境 `lib/python3.10/site-packages/asset_mujoco`，19个Python文件均与最终源码逐字节匹配。
- 依赖未升级：MuJoCo3.4.0、trimesh4.7.4、numpy2.2.6、Pillow11.3.0、pydantic2.11.7、pytest8.4.1、scipy1.15.3。

源码改动限于 pipeline.py、manifest.py、contracts.py、cli.py；新增两个集成测试文件。不改validation物理算法、rendering实际渲染算法、contact_profiles、碰撞/材质/法线/坐标实现，也不改atomic_publish并发防覆盖实现。

## 2. 两条错误路径与修复

### A：无效证据仍发布

在锁定环境中真实编译、执行native及渲染，再对contact清单注入与native冲突的profile并保持文件哈希自洽。旧流程最后refresh_report已得到physics=passed、scope=contradictory、INVALID_EVIDENCE，却未抛异常，仍发布。confirmed-red.txt保留复现；测试没有mock发布门槛或原生物理执行。

新增pipeline.publication_report：在atomic_publish前重新调用checked_report核对磁盘，按当前request检查必需层。无效证据、未完成验证和原生失败分别以EVIDENCE_INVALID、VALIDATION_INCOMPLETE、ASSET_CONTACT_FAILED报告，不把所有原因写成穿透错误。ValidationFailed携带package、result、stage、code、reason及沿用的退出码。失败staging保留，Python API不返回成功目录；CLI输出相同分层结果，无法读取报告时保留核心拒绝原因。

### B：渲染异常写回旧scope

真实native通过后仅注入渲染错误。旧代码磁盘scope=declared，已绑定证据却是verified；失败回归明确出现declared != verified。修复后native结束直接读取完整checked_report，不再只更新旧对象的physics/hash。

渲染异常仅改变render和render_error；render_failure.json记录原异常并受render层哈希绑定。失败/不可用路径不要求凭空生成成功预览。渲染不可用保留SCOPED_PHYSICS_VALIDATED，原full请求仍退出7且不发布；渲染失败总状态FAILED，独立物理范围仍verified。保存诊断失败或成功渲染后的证据写入失败使用EvidenceIOError，保留原错误、存储错误和因果链；CLI退出3，明确diagnostic_persisted=false，不假称完整落盘。

## 3. 发布门槛矩阵与独立审核

| 请求/事实 | 核心准入与实际回归 |
|---|---|
| compile | compile passed、资源/编译证据有效、无evidence_issues；正常发布 |
| VISUAL_ONLY | static+显式compile，physics not_applicable；正常发布 |
| physics | 编译和native passed、scope verified、物理依据齐备、无证据问题；正常发布 |
| full | physics全部条件加render passed及有效渲染证据；正常发布 |
| physics passed但scope contradictory | EVIDENCE_INVALID；无publish调用，staging保留 |
| 必需层缺失 | VALIDATION_INCOMPLETE或证据无效；无成功目录 |
| full且render not_run/unavailable | 即使局部物理聚合通过也拒绝；unavailable退出7 |
| 任一等级资源损坏、报告丢失/不可读 | EVIDENCE_INVALID，不误分类为输入文件不存在 |
| 人工pending、非必需地面观察failed | 不增加门槛；保留限制后允许指定工况发布 |

独立只读审核另发现一项Important：绑定render层status为not_run/未知值时，读取器跳过校验，仍继承缓存render=passed，full可发布。对not_run、unexpected、null三项先RED再修复；现在存在但非终态/非法状态的绑定层变为not_run并报告invalid_bound_layer_status，不继承缓存通过。补强不是删除摘要检查或放宽哈希。修复提交f1b91b0；未发现其他Critical/Important或延后Minor。

所有拒绝测试均检查convert抛错、atomic_publish未调用、没有成功最终目录、staging及准确原因保留。故障注入只作用于渲染异常、存储/证据损坏和发布调用监视，正常物理与发布流程真实运行。

## 4. 可查看的异常诊断

最终证据根：`outputs/m1_2_publication_fix_yanu7ij1`，release_evidence.json汇总命令、源码导入一致性、结果、磁盘报告与checked_report。

各目录 `fault_injection/<case>/` 保存convert.stdout.json、checked_report.json及原staging：

| case | CLI退出码 | checked physics/render/scope | 发布调用 |
|---|---|---|---|
| render_unavailable | 7 | passed / unavailable / verified | 0 |
| render_failed | 5 | passed / failed / verified | 0 |
| diagnostic_io | 3 | passed / not_run / verified | 0 |
| scope_contradiction | 5 | passed / passed / contradictory | 0 |
| render_status_corrupt | 5 | passed / not_run / verified，render证据问题 | 0 |

前两项磁盘报告与checked_report完全一致，没有cached_projection_conflicts_with_bound_evidence。I/O注入时没有声称已成功写出render_failure.json；原生证据仍存在。范围矛盾和状态损坏没有被刷新成通过。

这些是合成小箱体真实native之后的明确故障注入，不代表本机真实EGL不可用。完整回归还覆盖独立acceptance在渲染不可用时automatic_validation=failed；查询report保留物理局部通过不代表此前full请求成功。

## 5. 最终安装回归

```bash
/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -m pip install --no-deps --no-build-isolation .
env -u PYTHONPATH /home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -B -m pytest -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs
/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -m pip check
```

最终实际输出：`183 passed, 1 skipped in 47.43s`，pytest退出0；pip check退出0，`No broken requirements found.`。定向矩阵30 passed。唯一skip为OSMesa的OpenGL loader不可用（glGetError），EGL真实可用；未修改驱动。

本轮新增30项参数化后回归；保留原范围、旧包只读、审核指纹、证据失效、benchmark隔离、材质、法线、安全边界、迁移和渲染测试。历史153和中间180 passed不冒充最终结果。部分既有CLI测试显式用源码路径，源码与安装包已全部匹配；真实验收和可归档故障诊断均使用python -I的已安装包。

## 6. 最终原GLB真实复测

只读原始输入 `/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb`，SHA256为`12f1ed66a874efbdb3c350d819c1f6e076de469e7dc191d236de82073fdd2e12`。

两个profile分别通过已安装的`python -I -m asset_mujoco.acceptance --input <原GLB> --output <新父目录> --contact-profile <profile>`执行，完整命令在release_evidence.json。保持y/yaw180/scale.5/static+hull/full、原探针、dt=.002、1000步/2秒、5mm门槛。

| 本轮实测 | preserve | engineering_static_v1 |
|---|---|---|
| 状态/退出码 | FAILED / 5 | SCOPED_PHYSICS_VALIDATED / 0 |
| Python发布 | 拒绝，仅staging | 新目录成功发布 |
| 资产—探针最大穿透 | 11.795154509838177mm，failed | 2.376892611438749mm，passed |
| 后续地面观察 | 28.798825783942755mm，failed | 8.960727379537667mm，failed |
| 地面是否必需 | false | false |
| XML编译/forward、EGL四视角、迁移加载 | passed | passed |
| 首次接触/首次超限步 | 144 / 146 | 144 / 无 |
| warnings | 全0 | 全0 |
| 本次acceptance耗时 | 2.6571s | 3.2586s |

数值来自最终代码新转换/仿真，未复制旧数值。首次超限步不是最大穿透步。没有参数扫描或接触调参。

最终根下失败包：`preserve/acceptance-v2g014fy/packages/.staging-0h2czt6b`，指纹`fcddc1f10bd360e29a5036655f2c13c465d177a30f81e5070f3209edd8e1366e`。

候选包：`engineering_static_v1/acceptance-y_ki66ae/packages/penguin_f2d24f113839`，指纹`b344b5cd3b085871db461f8e99b661a2046374797bf66380ff39bed74eb62016`。

迁移后两份XML（候选另含contact_scene）重新MjModel.from_xml_path及mj_forward通过，指纹/分层报告一致。preserve没有最终成功目录；候选虽地面观察失败仍按原必需集合发布。中间实现输出`outputs/m1_2_publication_fix_aw4dbh4y`保留，不作为最终提交验收依据。

## 7. 保护范围、执行裁决和停止点

before/after及protection_and_geometry.json核对：本轮实际检查1185个原已跟踪outputs文件，全部哈希未变；第一阶段HEAD/工作区状态、原GLB哈希未变；全部依赖版本未变。新旧对应profile的视觉/碰撞OBJ、纹理、model/scene/contact_scene/physics_native XML及render_config字节相同。只更新当前权威设计局部契约，18章/10任务结构保留，历史报告/审核记录未覆盖。

执行裁决：沿用用户指定main/现有目录并精准暂存，不另建worktree（代价是无分支隔离）；为遵守不改.gitignore及保留证据要求，用/tmp账本后归档，未执行会改忽略规则或清理工作区的技能脚本（代价是手工账本）。审核未扩审物理算法、原子发布实现或宿主；安装回归和真实复测由主执行独立完成，不能据此声称宿主/物理全面验收。无延后Minor。

本地阶段提交：9d44fa9（完整渲染异常结果）、0261f35（Python发布门槛）、f1b91b0（审核发现的非法绑定状态旁路），随后归档文档/输出。未自动push。

人工审核pending、真实宿主集成pending、robot_contact_safety=not_validated、application_force_limit=not_specified。地面失败仍存在。至此停止，不进入任务8/9、不继续调参。
