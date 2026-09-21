# M1.2 受限基础版本收尾与交接

## 1. 已审核基线与本轮边界

- accepted_code_commit：`746949a90953ad88e774aec689a71124707a1f06`。
- 项目：`/home/mcl/workspace/3D-Assets-Mujoco`；branch：`main`。
- remote：`https://github.com/gungnir33/3D-Assets-Mujoco.git`。
- 2026-09-21 收尾前只读检查：HEAD 与上述 SHA 一致；无已跟踪文件差异，仅原有 `PHASE2_M1_1_CODEX_FIX_INSTRUCTIONS.md` 未跟踪，保持不动、不提交。
- 本文件是唯一的本轮收尾记录，不替代 [权威设计](PHASE2_MUJOCO_DESIGN.md)。设计保留 18 章/10 项任务；历史拟实现参数、待办和初始化叙述不代表当前 CLI 或本轮授权。当前使用入口以 README 和已审核实现为准，不恢复旧跟踪规则或历史规格。

本轮接受：Python 转换核心按请求等级核对证据后才允许发布；渲染失败/不可用保留既有物理事实和 verified 范围；非法绑定层状态不能继承缓存 passed；正常受限发布、compile-only、VISUAL_ONLY 及失败语义保留。此次局部软件修复到此结束，不再修改代码。

本轮仅核对 Git、记录、环境元数据和文件存在性，新增本收尾文档及 README 链接；没有运行转换、pytest、pip check、MuJoCo 编译/仿真、渲染、迁移或历史文件全量哈希，也没有重新签署证据。没有修改运行产物、第一阶段、宿主、依赖、审核记录、参数或阈值；没有启动 GUI/服务、建立分支/worktree、tag/Release 或推送。

## 2. 已有证据与明确状态

以下全部是已审核基线归档的历史实测，不是本轮新测试：

- [发布与异常修复报告](M1_2_PUBLICATION_STATE_FIX_REPORT.md)：最终实现/实测提交 `f1b91b05f310a6f906a92df542956bcd86774d9a`，由 accepted_code_commit 归档文档与证据。
- [机器证据](../../outputs/m1_2_publication_fix_yanu7ij1/release_evidence.json)、[部署清单](../../deployment_manifest.json)、[锁文件](../../requirements.lock.txt)。归档中的 `pushed=false` 是当时记录，本轮不回写历史文件。
- 既有回归：183 passed、1 skipped，47.43 秒；pip check 通过。skip 是 OSMesa loader 不可用；EGL 通过。既有 XML 编译/forward、四视角渲染及迁移加载通过，不等于真实宿主集成通过。
- 本轮只读确认解释器 `/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python`，Python 3.10.21，实际导入该环境的 `lib/python3.10/site-packages/asset_mujoco/__init__.py`。元数据为 MuJoCo 3.4.0、trimesh 4.7.4、numpy 2.2.6、Pillow 11.3.0、pydantic 2.11.7、pytest 8.4.1，与既有记录一致；未安装或升级依赖。

| 项目 | 既有结果及边界 |
|---|---|
| 软件流程修复 | 上述限定范围审核通过，不等于第二阶段全部完成 |
| 默认 preserve | 资产—探针最大穿透 11.795154509838177 mm，超过 5 mm，FAILED；仅保留失败 staging，未发布成功包 |
| 可选 engineering_static_v1 | 同一指定工况最大穿透 2.376892611438749 mm，受限通过；SCOPED_PHYSICS_VALIDATED |
| 候选后续地面观察 | 8.960727379537667 mm，failed；mandatory_for_physics=false，不隐藏也不新增强制门槛 |
| 未验证边界 | appearance_review=pending；host_integration=pending；robot_contact_safety=not_validated；application_force_limit=not_specified |

数值来源为上列报告第 6 节、部署清单及两个包的 validation_report/physics_native_evidence/contact_result_manifest。既有工况为当前包的 `native_asset_probe_v1`，必需对 `asset_collision:probe`，source_up=y、yaw=180、scale=.5、static+hull、dt=.002、1000 步/2 秒、原探针及 5 mm 门槛。scope=verified 表示证据可核对，不会把 preserve 的失败变成通过。

默认继续 preserve；候选须显式选择且仅 static+hull，双方约定 solref=[.006,1]、solimp=[.9,.95,.001,.5,2]。单独给资产设置候选参数而对方仍用默认参数不属于此通过条件。不是实测材料参数，不适用于任意机器人/宿主。scale=.5 是用户倍率，physical_scale_verified=false；单凸包会封闭孔道，hole_validation=not_tested。

代码审核不批准真实资产外观。有效外观批准也最多为 SCOPED_FULLY_VALIDATED，不能扩大物理范围、清除地面失败或批准宿主/机器人安全；本轮未写入任何 approved。

## 3. 可用包、预览与入口（本轮未执行命令）

以下相对路径均相对于工程根；本轮已确认两个目录存在。

候选包：
`outputs/m1_2_publication_fix_yanu7ij1/engineering_static_v1/acceptance-y_ki66ae/packages/penguin_f2d24f113839`

preserve 失败诊断包（不是成功交付包，勿清理 staging）：
`outputs/m1_2_publication_fix_yanu7ij1/preserve/acceptance-v2g014fy/packages/.staging-0h2czt6b`

候选包内下列 7 个文件均存在：

| 文件 | 实际用途 |
|---|---|
| model.xml | 完整单资产 MJCF，static body、视觉及碰撞资源；无地面或探针。不是可直接塞入任意宿主的通用 include 片段 |
| scene.xml | 独立演示场景，额外含地面、灯光和显示配置；不表示全部场景接触达标 |
| contact_scene.xml | 公开交付的候选资产、ground、动态 probe 及既定求解设置；用于双方一致配置的指定接触验收，不是通用宿主片段 |
| previews/front.png | 正面预览，供后续人工查看 |
| previews/side.png | 侧面预览 |
| previews/iso.png | 斜视预览 |
| previews/collision.png | 碰撞可视化预览 |

preserve 目录有 model.xml、scene.xml 和四张预览；没有 contact_scene.xml，符合该默认配置的输出，不猜测替代文件、不重新生成。移动候选时应保留整个资源包，不单独取 XML。宿主接入须重新处理命名/路径、摆放与编译配置，不无条件 include 带地面/探针的场景。

当前 CLI 语法已只读核对 `src/asset_mujoco/cli.py`。在工程根目录查询候选报告（不重新仿真）：

```bash
/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -I -B -m asset_mujoco.cli report \
  outputs/m1_2_publication_fix_yanu7ij1/engineering_static_v1/acceptance-y_ki66ae/packages/penguin_f2d24f113839
```

将参数换为失败 staging 可查询失败报告，其退出 5 是预期。新转换的显式命令见 [README 使用](../../README.md#使用) 和 [可选配置](../../README.md#m12-可选工程接触配置受限使用)：输入为位置参数，使用 `--collision-mode`、`--contact-profile`、`--validation-level`；不要照搬历史拟议 `--input`/`--collision`。转换会新建输出并运行验证，本轮不执行。预览仅交给用户查看，不启动 viewer 或自动审核。

## 4. 下一阶段仅待选择，不构成授权

| 方向 | 目标与最小范围 | 所需用户输入 | 验收边界 |
|---|---|---|---|
| A：实际宿主静态障碍物接入 | 将选定现有包接入真实仿真；核对资源名/路径、摆放坐标、视觉与碰撞包络和宿主加载 | 宿主 XML、启动脚本/工程入口；解释器与 MuJoCo 版本；资产、位置、尺寸、用途 | 不预设 acs_test/sim_test，不升级环境；独立编译不等于真实宿主通过，不附带机器人安全结论 |
| B：任务 8 几何扩展 | 仅选真正需要的一项：supplied 碰撞代理、CoACD、mass_geometry/watertight 或孔洞专项 | 目标资产、精度/孔道需求、代理文件、质量与惯量依据；先指定子项 | 不同时实施全部；单凸包通过不证明当前资产孔洞可通行；质量假设需明确 |
| C：任务 9 HTTP 串联 | 复用第一阶段既有 API 后调用独立转换器 | 端点、服务地址、请求/输出约定、是否批准真实生成 POST | 不改第一阶段源码/环境/既有资产；不自动启动服务、不自动重试生成；超时结果未知 |

静态导航障碍物优先考虑 A；必须保留把手/孔道碰撞时先明确 B；需要文本/图片到 XML 一体化操作时再考虑 C。选定一个方向并补齐输入后，另行制定和审核方案；本轮不开展宿主集成、任务 8/9、新功能或接触调参。

M1.2 受限基础版本收尾完成；既有地面失败和人工/宿主待验证状态保留。未开始新的功能开发，等待选择下一阶段范围。
