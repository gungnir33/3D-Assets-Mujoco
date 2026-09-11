# M1.1 缺陷修复与回归报告

日期：2026-09-11。依据根目录 PHASE2_M1_1_CODEX_FIX_INSTRUCTIONS.md 和本轮用户要求。权威设计仍为 docs/design/PHASE2_MUJOCO_DESIGN.md，仅修订受影响契约，不重写18章/10项任务。

## 1. 结论和保护边界

**缺陷修复回归通过；M1.1 真实资产自动验收未通过。**

| 独立结果 | 本轮证据 |
|---|---|
| 回归 | 新独立环境、实际安装包：94 passed, 1 skipped in 8.04s |
| 全新安装 | 新 Python3.10 环境实际安装锁文件/项目；pip check exit0 |
| 编译 | model.xml、scene.xml 均 MjModel.from_xml_path + mj_forward 成功 |
| 原始碰撞配置 | failed：最大穿透0.011795154509838177 m > 0.005 m |
| 受控 benchmark | passed：0.001190423480125262 m，仅代表受控夹具 |
| 渲染 | EGL front/side/iso/collision 原生渲染 passed |
| 迁移 | 新目录两份 XML 可加载，包指纹及分层证据相同 |
| 人工外观 | pending；未替用户批准 |
| 真实宿主集成 | pending；未进入真实 ACS 场景 |

不能声明“M1.1 自动验收通过”或 FULLY_VALIDATED。没有降低阈值、调整导出 solref/solimp 或降低真实资产探针高度来获得通过。未进入任务8/9，未自动 push。

起始 main/HEAD：e224b96e242f8b9486f737e4160073f91e6f40ff。
remote 始终为 https://github.com/gungnir33/3D-Assets-Mujoco.git。
最终生产代码提交：830556e02ceb0bf35979e137fdf4cf44056cf402；后续提交仅整理文档/证据，交付 HEAD 在最终终端报告列出，避免提交内部循环记录自身 SHA。
保留用户起始 outputs/.gitkeep 删除和未跟踪审核指令，不暂存这两项。
未找到 PHASE2_M1_AUDIT_REPROS.zip，未使用旧函数覆盖代码。

## 2. 八项审核问题对照

测试目录均为 tests/；使用锁定 Python3.10 / trimesh4.7.4 / MuJoCo3.4.0，不照搬其他环境角度误差。

| 审核项 | 复现与修复 | 具体回归与断言 | 状态/限制 |
|---|---|---|---|
| 1. pair 绕过碰撞配置 | 原强制 pair 下禁用碰撞位仍接触。validation 分离 native/benchmark；pipeline 只用 native 决定物理结果，失败仍独立渲染并保留诊断 | integration/test_native_contact.py：正常具体对接触；碰撞位全0时 native失败但benchmark通过；碰撞体移到x=10后固定探针不瞄准；温和合成夹具native通过；pipeline不提升benchmark；首次异常步 | 修复通过；真实企鹅native失败，不等于其接触精度已解决 |
| 2. OBJ 实际越界读取 | tab mtllib/前导空格map_Kd存在预扫绕过。RestrictedResolver读取前resolve/根边界检查，目录fd+O_NOFOLLOW打开；字节快照与错误闩锁防止吞异常fallback | integration/test_resource_boundary.py：../、symlink越界断言内容未读；tab、前导空格、合法子目录、普通贴图OBJ、缺纹理；依赖主文件/MTL/PNG哈希 | 通过；单mtllib/map_Kd有界支持，其余不支持语义拒绝 |
| 3. 证据过期 | 原compile-only无物理hash不能发现变化。manifest统一schema2分层内容清单，report只核对旧证据，不补签 | integration/test_layered_evidence.py：真正compile后损坏XML/改mesh/删纹理不再通过；改预览使render和approved失效；迁移有效、旧包保守、日志不循环失效compile。test_cli.py：先真实native passed再改资产，physics失效 | 通过；内容一致性系统，不是数字签名/防恶意伪造系统 |
| 4. 锁文件污染 | 原首行WARNING触发unit/test_lock.py失败。重新捕获freeze stdout/stderr，保持实际工作版本，去掉无关pyrealsense2及不可移植pip file URI，固定构建依赖 | 真正新环境install -r、项目安装、pip check、安装包模式全量回归；test_lock.py固定版本条目、test_isolation.py验证Python3.10且无torch/第一阶段包 | 通过，不是只删警告；网络慢第一次中断，缓存重试成功 |
| 5. PBR/OBJ顶点色 | 原缺省白图像素219而非255；红色顶点OBJ被接受。区分PBR缺省全1和无材质灰色；原始OBJ v行颜色检测拒绝 | integration/test_pbr_and_obj_colors.py：raw JSON省略factor；全1等价；白图255、非白0.5线性因子188；源字节不变；灰色180/255；红顶点OBJ拒绝，普通OBJ可用，真实MJCF材质绑定/ntex | 6项通过；没有新增顶点色有损开关 |
| 6. 源法线 | 实际加载导出7项测试原先失败。显式保存解码primitive/OBJ面角映射，完整组合逆转置，独立数组导出，不依赖copy cache | integration/test_source_normals.py：恒等、纯旋转、fit_axes非均匀、镜像、父子组合、无NORMAL computed、OBJ UV seam/硬边；检查真实vn及面角索引 | 7项通过；不以历史某个角度作固定目标 |
| 7. 默认级别 | 原Python/CLI默认compile。contracts/cli/config统一full，只测编译的回归显式compile | integration/test_defaults_and_scale.py：正常默认full，渲染不可用退出7不降级；显式compile退出0；none须static+显式compile | 通过，既有关键测试保留 |
| 8. 尺度声明 | 原显式倍率即verified=true。始终false，scale_evidence区分用户倍率/用户尺寸/格式默认和applied/confirmation | test_defaults_and_scale.py三类来源均false；真实scale=.5为user_multiplier、applied=true、confirmation=null | 通过，未开发测量系统 |

原 test_physics_render.py 和 test_m1_real_asset.py 仍运行真实物理/渲染，改为断言旧实现遗漏的 native 超限失败及 benchmark/render 独立状态。这不是放宽阈值；真实自动验收明确失败。补充首次异常步测试先得到 TypeError（旧值null），修复后接触5项通过。

## 3. 独立重建与依赖

新环境：/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild。
原 asset_mujoco、hunyuan3d、acs_test、sim_test 依赖均未修改。

| 组件 | 实测版本 |
|---|---|
| Python / MuJoCo | 3.10.21 / 3.4.0 |
| trimesh / numpy | 4.7.4 / 2.2.6 |
| Pillow / scipy | 11.3.0 / 1.15.3 |
| pydantic / pytest | 2.11.7 / 8.4.1 |
| setuptools / wheel | 83.0.0 / 0.47.0 |

实际命令（安装 stdout/stderr 分开保存）：

```bash
conda create -n asset_mujoco_m1_1_rebuild python=3.10 -y
env PYTHONNOUSERSITE=1 /home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -m pip install -r requirements.lock.txt
env PYTHONNOUSERSITE=1 /home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -m pip install --no-deps --no-build-isolation .
/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -m pip --no-cache-dir check
env PYTHONNOUSERSITE=1 /home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -B -m pytest -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs
```

从/tmp以python -I import得到新环境site-packages/asset_mujoco/__init__.py，非仅src隐式加载。最终异常步修复后重新安装并全量测得：94 passed, 1 skipped in 8.04s，exit0；pip check：No broken requirements found.，exit0。

唯一skip：integration/test_render_backend.py的OSMesa，OpenGL loader报 AttributeError: 'NoneType' object has no attribute 'glGetError'。EGL对应测试和真实四图成功，没有改驱动。原环境补异常步前全量94passed/1skip；补修后接触5passed，新环境全量覆盖最终代码。

首次无缓存SciPy下载多次低速/续传约15分钟，精准SIGINT中断本轮自己的安装进程(exit1)，未kill用户程序；随后使用pip已有同版本缓存完整安装exit0。未更换镜像或系统代理。
日志目录：/tmp/asset-mujoco-m1-1-UI1do8，包含freeze*.stdout/stderr、install-lock*.stdout/stderr、install-project-final*.stdout/stderr、final-pytest.txt。临时目录可能被清理，核心版本、pip check、pytest原文及验收数据已存入 [M1_1_EVIDENCE.json](M1_1_EVIDENCE.json)。

## 4. 新资产与两类接触

只读输入：/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb。
SHA256：12f1ed66a874efbdb3c350d819c1f6e076de469e7dc191d236de82073fdd2e12。

```bash
/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -B -m asset_mujoco.cli convert \
  /home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb \
  --output /home/mcl/workspace/3D-Assets-Mujoco/outputs/penguin_m1_1_20260911_final \
  --name penguin_m1_1 --source-up y --yaw-deg 180 --scale 0.5 \
  --body-mode static --collision-mode hull --validation-level full
```

实际退出5/ASSET_CONTACT_FAILED，不作为成功发布。
完整新诊断包：/home/mcl/workspace/3D-Assets-Mujoco/outputs/penguin_m1_1_20260911_final/.staging-396kwwx1。
包含两份XML、meshes、textures、previews、分层证据。
首次诊断 outputs/penguin_m1_1_20260911_rebuild/.staging-ks_dcta0 同样保留，未覆盖。
最终包指纹：c0c316e460fe5047c31292c10412dc8bba562c0e12d592be1d6df93b17a8433b。
各文件SHA256见机器证据files_sha256。全转换/编译/两类仿真/四图耗时3.5489787699189037秒。未采集分阶段计时/峰值内存，不虚报。

| 接触字段 | native原始验收 | benchmark受控基准 |
|---|---|---|
| geom对 | asset_collision ↔ probe | 相同 |
| 探针起点(m) | [0,0,1.2221956863999368] | 相同 |
| 资产碰撞位 | contype=1/conaffinity=1，未修改 | 相同，但pair强制接触 |
| 资产friction | [1,0.005,0.0001]，未修改 | 相同 |
| 实际接触solref | [0.02,1] | [0.004,1] |
| 实际接触solimp | [0.9,0.95,0.001,0.5,2] | [0.99,0.99,0.001,0.5,2] |
| 步数/时间(s) | 1000 / 2.0000000000000013 | 相同 |
| 首次/最后接触步 | 144 / 213 | 144 / 206 |
| 接触数 | 70 | 48 |
| 最大穿透(mm) | 11.795154509838177 | 1.190423480125262 |
| 原阈值(mm) | 5 | 5 |
| 首次异常步 | 146（穿透超限） | null |
| warning | 全8项计数0 | 全8项计数0 |
| 结果 | failed | passed |

energy开启、autoreset禁用；每步qpos/qvel/qacc/energy有限且时间递增，无数值异常。探针在表面后滑出，不对任意形状套用最终静止要求。benchmark数值虽接近旧报告，表中数据来自本轮新安装环境和原始GLB重新转换、重新仿真；不复用旧结果，也不提升native失败。

## 5. 渲染、迁移与宿主

EGL原生512×512四图：previews/front.png、side.png、iso.png、collision.png。render=passed，人工审核pending，无自动review approved。
完整复制至 /tmp/asset-mujoco-m1-1-migrated-h49qqdcx/package 后，两份XML再次实际MjModel.from_xml_path+mj_forward，资源不依赖旧路径；指纹一致，checked_report仍compile=passed/physics=failed/render=passed/appearance_review=pending，evidence_issues=[]。失败也忠实迁移，不补签通过。

转换器验证版本3.4.0。历史3.2.3/3.4.0编译矩阵保留并标为历史；本轮不将独立环境编译/合成宿主回归等同真实宿主集成。host_integration=pending，不声称shell语法适用所有版本。

## 6. 第一阶段与历史证据保护

第一阶段前后git status --short均空，HEAD均c78d96ea41a692917918af3d9ce4d3821be64f2b。
三份既有输入前后SHA256一致：

| job | SHA256 |
|---|---|
| 20260909_210330_6c804545 | 18659f94dcc66ba4d80a95c637f2bbe2194501cad54bd4fd3574c170f7d31fa4 |
| 20260909_210532_fe231a7e | 62d7be2ff354320570674c67fdf07dfc011b05830b492ef3bbc2801892c85554 |
| 20260909_210805_9dfdcdd0 | 12f1ed66a874efbdb3c350d819c1f6e076de469e7dc191d236de82073fdd2e12 |

git diff e224b96 -- example_outputs为空；历史M1报告未改。上述证明检查范围内无变化，未声称对所有权重重新全量哈希。本轮未对第一阶段源码/配置/Skill/环境/权重执行写操作，未调用API或生成新资产。

## 7. 提交、文件与未解决项

本地阶段提交：

- 0cacf6a：原始碰撞与benchmark分离。
- ad26ba3：OBJ实际资源边界。
- 581b18c：分层内容证据。
- 187f7fe：干净锁及独立重建。
- a264e7e：PBR/顶点色和源法线（各有独立失败/通过测试）。
- f2a94f2：默认full与尺度。
- 830556e：首次穿透异常步。
- 后续文档提交同步报告、README、权威设计、deployment manifest和机器证据。

修改src/asset_mujoco中的validation、pipeline、inputs、scene、manifest、cli、contracts、rendering、materials；config/default.yaml；pyproject.toml、requirements.lock.txt、.gitignore。新增/扩展测试见上表，另保留host_merge/package_publish/physics_render/m1_real_asset/isolation回归。准确文件清单：git diff --name-only e224b96 HEAD。

尚未解决/未开展：真实企鹅原始配置超出5mm；人工外观待用户；真实宿主集成未测；OSMesa不可用但EGL有效；无自动尺度测量。如后续调整接触模型或探针条件，须另行明确授权和物理含义，不抹掉本轮失败。到此停止，不push，不进入复杂凸分解、质量积分或HTTP串联。
