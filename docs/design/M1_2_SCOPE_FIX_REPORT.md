# M1.2 验收范围与报告一致性修复报告

本轮结论：受限验收范围、失败观察和未验证边界已进入通用结果并受证据约束；人工外观批准不会扩大物理结论。**这不是整个场景达标、机器人安全验证或第二阶段全部完成。**

## 1. 基线与环境

起始提交 `a4fa889d60ba6370c76bd1493b421239d8f9ad64`，分支 main；最终实现和实测提交 `8db4eef7356cc7a060f6941248d9ff5960097ead`。后续仅归档文档和新输出；归档提交可由 `git log -1 -- docs/design/M1_2_SCOPE_FIX_REPORT.md` 获取，避免文档自引用哈希。

remote 保持 `https://github.com/gungnir33/3D-Assets-Mujoco.git`，未 push。起始已有未跟踪 `PHASE2_M1_1_CODEX_FIX_INSTRUCTIONS.md`，未修改或纳入提交。

解释器 `/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python`，Python 3.10.21；导入为该环境 `lib/python3.10/site-packages/asset_mujoco`，19个 Python 文件与最终源码逐字节相同。依赖未升级：MuJoCo 3.4.0、trimesh 4.7.4、numpy 2.2.6、Pillow 11.3.0、pydantic 2.11.7、pytest 8.4.1、scipy 1.15.3。

未修改第一阶段、宿主环境/驱动、几何算法或物理条件，未开展参数扫描、任务8/9。起止快照见最终输出中的 before.json、after.json、installed-source-check.json。

## 2. 复现、修复与独立审核

| 缺口 | 必要修复和测试 | 结果 |
|---|---|---|
| 指定接触通过变成裸PHYSICS_VALIDATED，隔离外观批准变成裸FULLY_VALIDATED | 唯一结果类型和aggregate；pending/approved/rejected/指纹失效测试 | 最多SCOPED_PHYSICS_VALIDATED / SCOPED_FULLY_VALIDATED |
| 通用入口丢失scope、地面失败和未验证边界 | 从已核对native/contact证据派生共同报告 | 磁盘、CLI、acceptance语义一致 |
| 删缓存版本可绕过摘要核对 | conversion_manifest绑定scope_reporting_version；删除版本+改ground回归 | INVALID_EVIDENCE |
| 两份JSON哈希自洽但语义冲突 | profile、接触对、工况、ground、参数/统计交叉核对 | contradictory，禁止受限通过 |
| CLI失败仅报错；acceptance读取可变汇总 | 失败也输出package和统一报告；读取绑定native而非benchmark汇总 | native失败事实保留 |
| 独立审核：缓存把native failed改成not_run可掩盖失败 | 3种缓存状态降级用例；核对层不由缓存决定是否执行 | native failed仍FAILED，保留原错误 |
| 独立审核：fixture与范围自述矛盾未识别 | 4种变异：geom名、dt、初态、强制pair；解析核对夹具和公开contact_scene | contradictory，不在report内运行引擎 |
| report固定退出0 | FAILED/INVALID_EVIDENCE/证据问题退出5，指定工况通过且人工pending退出0 | preserve 5，候选0 |

独立只读审查对7519f3c提出1个Critical、1个Important及退出码建议，均有先失败后通过的回归，修复落于8db4eef。审核不替代实测与保护核对。没有扩大范围或重构转换器。

源码改动限于 contracts.py、manifest.py、pipeline.py、validation.py、cli.py、acceptance.py。新增 scope 单元/集成测试；原 contracts、CLI、layered evidence、benchmark isolation 测试按新契约适配，未删除测试或放宽物理阈值。native初始化异常缺少夹具时，原“没有证据问题”的断言改为准确报告scope缺失；合成写入流程遵循新投影顺序。

## 3. 统一结果和证据顺序

所有入口输出contact_profile、validation_scope、followup_ground、application_force_limit、host_integration、robot_contact_safety、limitations，并保留compile/physics/render/appearance_review。

static case_id为native_asset_probe_v1，free为native_asset_ground_v1，不以企鹅命名。条件来自当前包native和XML：必需geom对、dt/步数/时长、初态、实际接触参数、版本及阈值；非固定5mm。compile-only为declared，不是verified。missing/stale/contradictory分别处理，不凭profile名称推断通过。

physics=passed仍是底层事实；scope验证有效才返回SCOPED_PHYSICS_VALIDATED。渲染通过且外观有效approved时最多SCOPED_FULLY_VALIDATED，地面失败、宿主pending、安全not_validated、力限not_specified仍保留。地面没有变成新的强制门槛。

写入顺序：转换manifest版本约定 → 编译层 → 独立native/contact结果及物理层 → 范围投影 → 渲染层及最终投影。缓存、审核、总状态不进入范围证据的循环哈希；外观审核独立绑定包内容。checked_report只读取和核验，不仿真、不写回、不补签。

完整旧包只读派生；缺依据保守报告。测试验证旧包指纹未变、迁移一致、contact_scene/接触结果/native修改使旧通过失效。预览变化使渲染/外观证据失效，但独立物理事实可保留。人工approved仅用于隔离副本，不批准真实包。

## 4. 安装和最终回归

```bash
/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -m pip install --no-deps --no-build-isolation .
env -u PYTHONPATH /home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -B -m pytest -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs
/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -m pip check
```

最终实测：`153 passed, 1 skipped in 33.18s`，退出0；pip check退出0，`No broken requirements found.`。唯一skip：OSMesa OpenGL loader不可用（glGetError）；EGL实测通过，未改驱动。

新增34个参数化后用例；独立审核新增7项先失败，修复后39项定向通过。完整回归保留资源边界、材质、法线、参数混合、碰撞位、benchmark异常隔离、证据失效、迁移及渲染测试。前期146 passed及历史119 passed不作为最终结果。

最终日志为final-installed-pytest.txt。部分既有CLI测试显式指定源码路径，但安装包与源码已逐文件核对相同；真实复测全部使用python -I，不依赖PYTHONPATH。

## 5. 最终原GLB复测

只读输入 `/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb`，SHA256 `12f1ed66a874efbdb3c350d819c1f6e076de469e7dc191d236de82073fdd2e12`。

最终证据根 `outputs/m1_2_scope_fix_jnabps39`；中间实现复测 `outputs/m1_2_scope_fix_8zw0gsj6` 独立保留，不冒充最终代码结果。原请求不变：source_up=y、yaw=180、scale=.5、static+hull、full；原探针质量/半径/初态、dt=.002、1000步/2秒、5mm门槛。完整命令保存于real_results.json，入口为：

```bash
python -I -m asset_mujoco.acceptance --input /home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb --output NEW_PARENT --contact-profile preserve
python -I -m asset_mujoco.acceptance --input /home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb --output ANOTHER_NEW_PARENT --contact-profile engineering_static_v1
```

| 本轮实测 | preserve | engineering_static_v1 |
|---|---|---|
| 状态 | FAILED | SCOPED_PHYSICS_VALIDATED |
| acceptance / report退出码 | 5 / 5 | 0 / 0 |
| asset_collision—probe | failed，11.795154509838177mm | passed，2.376892611438749mm |
| ground—probe，非必需观察 | failed，28.798825783942755mm | failed，8.960727379537667mm |
| 实际contact.solref | [.02,1] | [.006,1] |
| 首次接触步 / 首次超限步 | 144 / 146 | 144 / 无 |
| warning | 全0 | 全0 |
| 两份XML编译及mj_forward | passed | passed，另含contact_scene.xml |
| EGL四视角原生渲染 | passed | passed |
| 迁移编译/forward/指纹/分层报告 | passed | passed |
| acceptance耗时 | 2.6621s | 2.8405s |

数值来自最终代码重新转换和仿真，虽与历史一致，不是复用旧数值。首次超限步不是最大穿透发生步。没有新增参数扫描。

候选包：`engineering_static_v1/acceptance-vlvtw4it/packages/penguin_94ee0d78fb8f`；指纹 `6ac61e758f025b69fd0dec3f2ec140204752e0952eae2611f56446f9e60323f4`。

preserve失败诊断包：`preserve/acceptance-zjcc9elu/packages/.staging-auc2seo8`；指纹 `d1f12da66a599b31a45f0fb8e1e9c8b57cae46c2295a3b853ca13acf3721474d`。它仍是失败staging，不冒充成功发布包。

额外候选CLI convert包为`cli_convert/asset_d0c16ab59abc`，退出0，stdout/磁盘/checked_report一致。两组acceptance stdout、acceptance.json、磁盘报告与CLI report重叠字段一致。审核后report的状态上限只在隔离测试副本验证。

## 6. 保护核对和未验证边界

protection_and_comparison.json确认：第一阶段HEAD仍为`c78d96ea41a692917918af3d9ce4d3821be64f2b`，工作区状态及原输入哈希不变；原有922个已跟踪outputs文件哈希全部不变；依赖版本不变；.gitignore未改。

同profile的新旧视觉/碰撞OBJ、纹理PNG、model.xml、scene.xml、physics_native.xml、候选contact_scene.xml、render_config.json全部字节相同。预览独立渲染少量像素最大单通道差1，单独记录，不增加逐字节渲染一致门槛。历史图像/报告/审核记录未改写。

人工外观pending；真实宿主集成pending，未重测ACS等宿主；robot_contact_safety=not_validated；application_force_limit=not_specified。地面失败未修复，未做真实材料标定，不能宣称整个场景或机器人安全通过。

## 7. 本地提交和停止点

`de90eac`：结果契约；`7519f3c`：统一证据和入口；`8db4eef`：独立审核回归修复。后续归档文档/部署清单及两份新输出根，遵循当前Git跟踪策略，不纳入原有用户审核文件或输入GLB。

本轮修复和审核补强完成后停止，未push，不进入任务8/9，不继续地面调参。
