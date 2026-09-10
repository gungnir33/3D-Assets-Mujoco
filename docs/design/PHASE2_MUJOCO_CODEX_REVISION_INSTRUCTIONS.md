# 第二阶段 MuJoCo 转换工程：设计与实施计划修订指令

## 0. 本轮任务与依据

请以现有 `PHASE2_MUJOCO_DESIGN.md` 和以下审核意见为依据，修订第二阶段设计及实施计划。保留原文的主体架构、范围和章节组织，不推倒重写，不把第二阶段并入第一阶段。

本轮先修改文档并做必要的只读检查；不要自动开始安装环境、转换资产、修改第一阶段或推送 Git。下文中的实现要求、测试及 Git 初始化均需写入后续实施计划，不表示已经执行成功。

原始设计文件预期位于：

```text
/home/mcl/models/hunyuan3d/tasks/PHASE2_MUJOCO_DESIGN.md
```

先确认实际文件。若未找到，报告缺失，不另写一份假装已经读取原设计。修改该设计时保留可追溯的原稿副本；工程初始化后，将正式设计放入第二阶段的 `docs/design/PHASE2_MUJOCO_DESIGN.md`，确定唯一权威版本，避免两份文档长期漂移。

本说明中的默认值与新增契约属于本项目设计决定。对 `mesh inertia="shell"` 等版本相关策略，必须安排实测，不得把候选方案写成已验证结论。

## 1. 固定第二阶段仓库，并保留第一阶段冻结边界

### 1.1 第二阶段配置

```text
Git remote：https://github.com/gungnir33/3D-Assets-Mujoco.git
默认本地目录：/home/mcl/workspace/3D-Assets-Mujoco
Python 包名：asset_mujoco
Conda 环境：asset_mujoco
Python 基线：3.10
```

更新原规格中“未指定远端、独立本地 Git 仓库”的描述。新建工程采用 `3D-Assets-Mujoco` 命名，不要误用第一阶段的 `3D-Assets-Agent` remote。

如果旧建议目录 `/home/mcl/workspace/3D-Assets-MuJoCo` 已存在且包含工作，先检查并报告，不自动重命名、删除或另建一份造成混淆。设计中记录最终采用的真实路径。

后续初始化前执行：

```bash
git ls-remote https://github.com/gungnir33/3D-Assets-Mujoco.git
```

退出成功但无 refs，可以作为空远端处理；认证失败、404 或网络错误不能解释为“空库”。不得另建 GitHub 仓库，不得强推、覆盖已有提交或修改第一阶段 origin。若远端已有内容，先读取并在其基础上工作。

第二阶段只跟踪源码、设计、测试、配置示例和锁文件。忽略 outputs、真实输入资产、模型权重、环境、密钥和运行缓存。不要全局忽略全部 `*.xml`、`*.obj`、`*.png`，以免误排除必要的合成测试 fixture。

### 1.2 第一阶段保持不变

冻结以下对象：

```text
/home/mcl/workspace/3D-Assets-Agent
/home/mcl/workspace/hunyuan3d/Hunyuan3D-2
Conda 环境 hunyuan3d
/home/mcl/models/hunyuan3d/Hunyuan3D-2
/home/mcl/models/hunyuan3d/HunyuanDiT-v1.1-Diffusers-Distilled
```

不修改第一阶段源码、配置、Skill、API、依赖、upstream、既有模型或 metadata；不在 hunyuan3d 环境安装第二阶段依赖。第二阶段只能独立读文件，或者通过第一阶段原有 HTTP API 串联。

独立转换验收时，第一阶段服务不可达、Python 包不在第二阶段环境内，也必须可运行。对第一阶段已有仓库状态和既有资产哈希做前后对比，不能为得到“干净状态”而 reset 用户修改。

后续真实串联测试会让第一阶段通过既有 API 新增 job，这是正常生成行为；不得覆盖既有 job，也不要把“新增 job”和“改坏既有资产”混为一谈。真实串联需显式启用，本轮不执行。

## 2. 保留总体方案，明确三类几何职责

保留 GLB/OBJ 输入、static 默认、free 可选、显示与碰撞分离、XML+OBJ+PNG 可迁移包、CPU 转换、Blender 可选、无第二个 API 服务等范围。

将现有双分支细化为三个逻辑分支：

```text
输入检查与快照 → Scene/材质解析 → 全局坐标与尺度规范化
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
     visual_geometry         collision_geometry         mass_geometry
     保留形状/UV/材质         凸包/凸分解/代理             质量积分专用
           └────────────────────────┼────────────────────────┘
                                    ▼
                          MJCF → 编译/物理/渲染验证
```

`mass_geometry` 可以是内存中的独立副本，无需强制输出额外大文件。禁止为质量积分焊接顶点时破坏视觉 UV，也禁止直接用可能重叠的 CoACD 凸体求真实惯量。

仍不实现关节识别、机器人运动控制、流体、软体、自动猜质量、复杂 PBR 烘焙、Web UI 或自动多物体场景生成。

## 3. 补全请求契约、朝向及尺寸语义

在 `contracts.py` 统一定义并校验，不让各模块自行解释字段。

| 字段 | 修订要求 |
|---|---|
| `scale` | 输入层允许为空，仅显式输入时参与与 target_size 的互斥检查 |
| `target_size_m` | 最终规范化坐标系的 X/Y/Z 尺寸，不是自动排序后的长/宽/高 |
| `source_up` | 保留 y/z；GLB 默认 y，OBJ 必须显式指定 |
| `yaw_deg` | 新增，默认 0、有限数；完成 up-axis 转换后，绕目标 +Z 按右手规则旋转，再做尺寸缩放 |
| `collision_proxy_path` | collision=supplied 时必须提供，且是可读的受支持资产 |
| `supplied_inertia` | inertia=supplied 时必须提供质量惯量契约所需的 COM、张量、frame、reference 和 units |
| `validation_level` | 新增 compile / physics / full；明确各级行为，正常物理资产默认 full |
| `output_dir` | 明确定义为输出父目录，允许已有其他任务；最终任务包目录必须唯一且不得覆盖 |

两个尺度参数都未提供时，GLB 解析为 scale=1，并继续报告 `physical_scale_verified=false`。OBJ 转换必须显式给出 scale（可以为 1）或目标尺寸，不擅自猜测单位。保留 uniform 模式的比例一致性检查和原有 2% 提议容差；fit_axes 仅在显式选择时允许形变。

将变换顺序更新为：

```text
v_output = T_origin × S_scale × R_yaw × R_axis × T_node_world × v_local
```

保留 Scene 层级变换、负行列式面朝向处理、法线逆转置、全资产统一原点，以及不重复补偿 MuJoCo mesh 内部变换等正确要求。

代理碰撞文件首先展开自己的节点变换，然后使用由视觉资产确定的同一全局规范化变换；不得独立重新居中、自动配准或另算缩放。

`inspect` 应输出节点/primitive、材质、纹理、顶点色、输入 AABB、面数和方向参数。长轴确认后用 yaw 调整，不能用 fit_axes 掩盖轴向错误。新增长轴位于 Y 的非对称模型测试。

## 4. 前置验证：可视子网格能否真正通过 MuJoCo 编译

按材质拆分正确，但不能预设拆出的每个子网格都有体积、都能在目标 MuJoCo 版本编译。可视 geom 的 `mass=0` 也不能作为“资源层编译一定通过”的依据。

在材质导出全面实现之前，新增最小引擎实验，覆盖：

```text
普通闭合箱体
六个面分别使用不同材质的箱体
单个三角形材质分块
平面可视片 + 独立闭合碰撞体
```

测试必须调用目标版本的 `mujoco.MjModel.from_xml_path()` 和 `mj_forward`，不能只验证 XML 语法，也不能 mock 编译器。

为 `materials.py` / `mjcf.py` 明确视觉资源编译策略：

- 有体积子网格采用正常资源导出。
- 平面、开放或特殊子网格验证目标版本可用的设置；`mesh inertia="shell"` 仅是候选，不保证普适可用。
- 顶点数不足等情况，只有经测试证明保持可见表面、UV 和法线的细分适配才可使用，并记录处理；否则返回明确不支持错误。
- 不得为通过编译而静默加厚、封孔、删材质、删除 primitive 或退化成凸包显示。

区分视觉资源自身的编译处理和自由刚体 `<inertial>`：前者不得改变显式定义的物体质量惯量。不要要求每个可视 primitive 都具有非零三维体积。

记录 MuJoCo 版本、各子网格顶点/面数、编译参数、错误与结果。以上实验通过后，才能把所选策略写为“已验证”。

## 5. 质量、质心与惯量契约

### 5.1 supplied：第一版只接受最终 body 坐标系下的数据

明确限定：

```text
frame = normalized_body
reference = com
COM 单位 = m
惯量单位 = kg·m²
数据对应最终输出尺寸和指定质量
```

即：用户提供的是最终规范化后 body 坐标系中的质心位置，以及关于该质心、在该坐标轴下表达的完整对称惯量张量。

对上述输入，不得再次应用轴变换、yaw、尺度或原点补偿。验证数值有限、对称性、正定性、主惯量三角不等式，并明确数值容差；输出时验证 MJCF 的字段排列及编译后的质量惯量。

第一版不支持含糊的“源坐标系惯量”。如果传入 source frame，明确报不支持，不猜测、不仅旋转后继续输出。也不要因为改变 body 原点，就给已经关于 COM 的惯量重复加平行轴项。

### 5.2 box_approx 与 watertight

box_approx 保持原设计：用最终尺寸和显式质量计算，COM 为盒中心，报告近似。

watertight 使用独立 `mass_geometry`，进行带尺度相关容差的顶点处理和拓扑检查。焊接只用于该副本，容差及处理记录进入 manifest；不能焊掉薄壁、窄缝或不同部件，也不自动封孔。

不能仅凭 `is_watertight + winding consistent + volume > 0` 就宣称积分可信。多部件重叠、自交和嵌套壳关系不明确时，必须拒绝该惯量策略或要求用户另选，而不是暗中改成 box_approx。

第一版可保守限定为经过检查的单个闭合、方向一致、无自交实体；无法证明满足前提就失败。不为兼容任意生成模型而加入未经验证的布尔修复。报告 `mass_model=uniform_solid_assumption`，不声称反映空心水马或真实材质分布。

### 5.3 必须新增的测试

| 用例 | 断言 |
|---|---|
| 尺寸 1.25/0.13/0.65 m、质量 12 kg 的箱体 | 解析惯量与输出一致；这些数值只是测试输入 |
| 同质量、均匀尺寸放大 2 倍 | 计算得到的惯量放大 4 倍；用于 box/watertight 等几何计算，不是再次缩放 supplied 输入 |
| 非对称箱体旋转 | 惯量方向及编译结果正确 |
| 仅移动 body 原点 | COM 坐标变化，不重复改变关于 COM 的惯量 |
| 带 UV 接缝重复顶点的箱体 | 质量副本正确处理接缝，视觉副本不变 |
| 两个相互重叠的闭合箱体 | 不能仅凭 watertight 标志通过可信积分验收 |
| 开放、自交、嵌套壳或无法确定体积的输入 | 明确失败，不静默近似 |

## 6. 材质采用“原始格式检查 + 解析结果核对”两层验证

不能完全依赖 trimesh 加载后的对象判断原始输入是否使用了不支持的特性。设计中增加加载前检查，覆盖 GLB JSON 的场景、primitive、材质、扩展和资源引用。

至少检查：

```text
extensionsRequired / extensionsUsed
TEXCOORD_0 / 其他 UV 集
COLOR_0
alphaMode
baseColorTexture 的 UV 集和 sampler
纹理变换
骨骼、morph 和压缩扩展
```

采用显式支持矩阵：实现且验证的特性才支持；不支持的特性按原有严格/显式降级策略处理，并记录实际损失。不要静默换 UV 集、忽略纹理变换，或让解析器先丢信息后再报告“未发现异常”。固定 trimesh 的加载选项，保留实例与 primitive/material 对应关系。

继续保留原设计中的 MTL 非自动依赖、XML 显式材质绑定、颜色因子只应用一次、UV seam 和视觉网格不随碰撞简化等要求。

将视觉测试扩充为：四色 UV、多材质共享图、不同颜色因子、超范围 UV、非默认 UV/纹理变换的支持或明确拒绝、纯色纹理、缺纹理 OBJ。

删除“所有有纹理资产都必须像素非单色”的通用断言。纯色纹理合法；非单色只能用于特定校验图。真实资产需检查资源绑定、预览和外观审查，不能把非空图片当作保真证据。

## 7. 碰撞策略增加精度与处理过程记录

保留 static+hull 默认，以及 CoACD 的原有提议预算：输入≤50,000 faces、最多 32 个凸体、seed=12345、180 秒子进程超时。明确这些是资源预算，不是碰撞精度保证。

在确定 CoACD 版本后补齐并记录实际解析值：误差阈值、阈值单位/归一化方式、预处理、是否合并、是否再次减面、每凸体顶点预算、最终凸体数和验证结果。不捏造尚未核实的参数默认值。

具体要求：

1. hull 默认以规范化后的原始几何顶点构造整体凸包；若预算不允许则明确失败。不得先简化后仍宣称凸包一定包住全部原始视觉几何。
2. CoACD 输出逐个检查合法性；数量约束或进一步简化造成的近似必须记录。
3. 超时、输出不合法或超预算默认失败，仅显式 fallback=hull 才能回退，并保留原失败原因。
4. supplied 代理逐 component 验证闭合凸性，使用第 3 节约定的统一变换。
5. 分别记录“标准孔洞夹具测试”和“当前资产孔道测试”。未配置当前资产探针路径时，报告 `hole_validation=not_tested`，不得沿用算法回归测试结论。

保持显示 geom 不参与碰撞、质量不重复贡献、碰撞隐藏仅作用于渲染显示选项，而不关闭物理碰撞。

## 8. 修订仿真、渲染和最终状态判定

### 8.1 仿真检查

保留演示测试的 0.002 s、1000 steps 和原有落体夹具穿透阈值；这些不覆盖宿主场景配置。

在测试场景显式启用能量计算；记录实际配置。明确测试环境的 autoreset 处理，检查每步 qpos/qvel/qacc/energy 是否 finite、仿真时间是否按步长递增、相关 warning 及首次异常步。

不能只检查最终状态，不能把异常自动重置后的有限数值当作成功。数值异常和资源溢出等告警应失败；其他告警按明确分类处理，不允许全部忽略。

接触测试断言具体 geom 对及预期行为，而不只看总接触数：落体与地面、探针与边框应接触，探针在已定义孔道内不应接触。孔洞测试必须放到 MJCF 与仿真夹具已经可用之后。

### 8.2 渲染检查

EGL/OSMesa 各在独立子进程中探测；在导入相关渲染模块之前设置后端，不在同一进程反复切换环境变量并假设已生效。GLFW 交互 viewer 与离屏渲染分别报告。

OSMesa 成功也属于有效渲染，不以“没有 GPU”直接判渲染失败。不修改宿主机驱动。碰撞 group 显隐同时覆盖 viewer 和 Renderer。

### 8.3 结果分层

至少分别记录：

```json
{
  "compile": "passed",
  "physics": "passed",
  "render": "unavailable",
  "appearance_review": "pending"
}
```

保留 CONVERTED、COMPILE_VALIDATED、PHYSICS_VALIDATED、FULLY_VALIDATED，但写清聚合规则：没有渲染不否定已经通过的物理测试；渲染成功不替代物理；真实资产人工审查未发生就不能记为已批准。

`validation_level=compile/physics/full` 分别执行编译、编译+物理、完整自动检查。正常物理资产默认 full；collision=none 需显式选择 compile，标注 VISUAL_ONLY，不得升级为 PHYSICS_VALIDATED/FULLY_VALIDATED，预览仍可单独执行。

退出码表示所请求命令和自动检查的结果，不等价于人工验收。full 自动检查成功但人工审查 pending 时，可报告自动检查成功，但不得把真实资产标为最终 FULLY_VALIDATED。完整自动检查要求渲染而后端不可用时，保留退出码 7；模型已有的编译/物理通过结果仍保留。

## 9. 按第一阶段真实协议修订 chain.py

第一阶段保持原有接口，不新增字段、不更改响应。实施前再次只读核对其当前源码；当前需兼容的契约是：

```text
POST /generate/text       payload 包含 prompt
POST /generate/image      payload 包含 image
POST /generate/texture    payload 包含 mesh、condition_image
成功响应：job_id、file、type、metadata
```

`file` 和 `metadata` 为服务端文件路径，metadata 不是内嵌 JSON 对象。第一版只支持与服务共享本地文件系统的串联，不把任意远程服务器路径当成本地路径。

发请求前验证请求的格式为 GLB/OBJ，优先 GLB；返回后校验文件存在、可读、实际类型受支持。metadata 作为可选来源信息，缺失或不可读时记录警告，不影响已有完整转换参数下的独立转换。

错误处理同时兼容 FastAPI 422 的 detail 列表，以及业务错误的 error.code/message/details。保留第一阶段状态码和原因；包括 503 OOM、非 JSON 响应、连接失败和超时。

保留 timeout=1800 s，不自动重试生成 POST。超时表示结果未知，不表示服务必然取消；不得自动再次生成。第一阶段成功、第二阶段失败时，保留原 job/file/metadata，允许直接从原文件恢复转换。

本机 loopback 请求可设置客户端 `trust_env=False`，避免历史代理环境干扰；不修改用户全局代理。chain 不启动服务、不 import 第一阶段包、不初始化 GPU。

## 10. 包发布、宿主版本和依赖补充

`--output` 是可含其他任务的父目录，最终写入唯一 `<name>_<id>/`。staging 与最终目录位于同一文件系统，达到请求的自动验证等级后原子发布；失败保留诊断但不覆盖已发布包。

XML 和包内产物引用使用相对路径；manifest 中源路径可以作为来源信息，但不得成为加载依赖。重命名发布后确认报告不残留必须存在的 staging 路径。

保留两个完整 MJCF 文档：model.xml 不带全局地面/灯光，scene.xml 包含演示设施。增加最小宿主场景合并示例及测试，验证名称前缀、资源路径和物理模型不被意外改变，不自动修改用户真实 ACS 场景。

确定新环境 MuJoCo 版本前，先只读调查目标宿主仿真的版本。部署清单分别记录生成版本、实际验证版本、宿主兼容性状态。宿主版本暂不可确认时报告 pending，不声称兼容任意版本，也不因此升级第一阶段环境。

按选择的算法安装真实依赖：如果采用 trimesh 的对应减面接口，核对并纳入 fast-simplification；CoACD、Blender 保持按功能可选。不添加 Torch 或 Hunyuan3D。渲染后端、减面后端、MuJoCo/CoACD 版本和许可证记录到清单。

## 11. 重排实施计划，先形成最小真实转换闭环

保持文档第 15 节作为实施计划，调整依赖顺序。每项写清新增/修改文件、测试路径、实际断言和通过条件；先失败测试再实现，不只写“完善测试”。

| 顺序 | 工作及主要文件 | 必须提供的证据 |
|---|---|---|
| 1 | 独立仓库/环境、contracts.py、check_environment.py | 正确 remote、第一阶段只读基线、环境 lock、参数冲突测试 |
| 2 | inputs.py、scene.py、transforms.py | 原始格式清单、层级变换、yaw、比例、镜像、路径穿越测试 |
| 3 | 最小 mjcf.py 编译实验、test_visual_mesh_compile.py | 箱体、材质平面、单三角形、独立碰撞体的真实编译结果 |
| 4 | materials.py、test_visual_assets.py | 原始格式/解析结果核对、四色/纯色/多材质测试、真实编译和渲染 |
| 5 | collision.py、inertia.py 的基础实现 | hull、box_approx、supplied 的明确契约与解析测试 |
| 6 | pipeline.py、mjcf.py、manifest.py | static/free 基础包、相对路径、staging、移动后编译 |
| 7 | validation.py、rendering.py、view_asset.py | 动态探针、落体、告警与 autoreset 检查、三视图及状态分层 |
| 8 | CoACD、supplied 代理、watertight 的扩展 | 时间/数量预算、重叠与接缝测试、此时再运行孔洞接触测试 |
| 9 | chain.py、test_chain.py | 200/422/503/超时 mock、结果恢复、无第一阶段 import |
| 10 | test_existing_assets.py、文档与部署清单 | 三份真实资产、独立性、可移植性、宿主兼容状态和最终报告 |

第一个可用里程碑只要求：

```text
一份真实 GLB → 正确方向/尺度与外观 → static+hull
→ model.xml/scene.xml 可编译 → 探针接触正确 → 可渲染 → 换目录可加载
```

该闭环未通过之前，不优先扩展复杂 CoACD、任意网格质量积分或自动串联。

原设计三份本机 GLB 继续作为只读 E2E 输入，但先检查实际存在及材质特征，不预先认定哪份必然带纹理或没有顶点色。缺失时报告，不自动调用第一阶段重新生成，不将这些真实资产提交 Git。

## 12. 本轮交付与自检

本轮输出：

1. 修订后的完整 PHASE2_MUJOCO_DESIGN.md，保留设计依据并标识新增约定。
2. 修改对照表：审核问题 → 原章节 → 修订内容 → 计划测试 → 当前验证状态。
3. 调整后的分阶段实施计划、模块/测试文件、依赖和里程碑。
4. 精确仓库地址、拟用/实际本地路径、现有工作与访问状态；未检查的项目明确标注未检查。
5. 实测依赖清单：哪些技术策略还需验证，在哪个任务验证，失败时采取何种明确处理。

自检重点：

```text
远端是 gungnir33/3D-Assets-Mujoco，不是第一阶段仓库
“未指定远端”的旧描述已替换
新旧本地目录命名没有混用
未修改第一阶段或执行环境安装/资产转换
supplied 惯量没有被二次变换
watertight 标志没有被当成体积积分可信的充分条件
shell 等候选策略没有冒充已验证方案
单色纹理不被错误判失败
孔洞测试没有依赖尚未实现的仿真模块
渲染、物理、人工审查和退出码没有混为一谈
staging、发布目录、输出父目录语义一致
所有“通过”声明都有实际证据；待实测项目保留明确状态
```

后续实施只在第二阶段仓库按测试通过的里程碑提交。推送前检查 remote、分支和待提交内容，不强推、不替换仓库、不提交真实资产。此次文档修订完成后停止，不自动进入实现或推送。
