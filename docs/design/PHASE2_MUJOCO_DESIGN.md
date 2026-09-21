# 第二阶段：3D 资产到 MuJoCo MJCF 独立转换工程设计与实施计划

状态：R3 小范围契约修订，R2 总体设计已审核通过。本轮授权依次执行任务 1–7；实施证据单独记录，设计要求不等于验证通过。

主要依据：[完整修订指令](PHASE2_MUJOCO_CODEX_REVISION_INSTRUCTIONS.md)及本轮用户要求。原始 18 章结构保留；变更与检查记录见 [修订对照与待实测清单](PHASE2_MUJOCO_REVISION_REPORT.md)。

当前唯一权威设计位于 `/home/mcl/workspace/3D-Assets-Mujoco/docs/design/PHASE2_MUJOCO_DESIGN.md`。原稿和 R2 为同目录只读归档，tasks 中旧路径仅保留迁移指针。实施进度与证据见 M1_IMPLEMENTATION_REPORT.md；本设计仍保留全部 18 章和 10 项任务，不把未完成子项标为通过。本轮授权任务 1–7，不修改第一阶段或现有宿主环境，不调用生成、不自动 push。

## 1. 目标、交付物与边界

输入第一阶段已经生成的 GLB 或 OBJ，输出可由 MuJoCo 加载、查看和运行的 MJCF XML 及其引用资源。静态路障、家具、道具和单个可移动刚体是首版对象。

“同样的模型”定义为：保留可见形状、颜色、主要贴图与多部件相对位置；按照明确参数转换坐标和单位；显示网格与碰撞体对齐。不是逐像素复刻 Blender 渲染，也不是自动获得真实物理参数。

交付一个可整体移动的资源包，而不是只有 XML 的孤立文件。XML 引用 OBJ 和 PNG，移动时必须一起携带。无材质输入保留几何并使用明确默认色，不凭空生成纹理。

首版支持：

- GLB、OBJ 文件独立转换，不要求第一阶段服务可用。
- static：固定在世界中的物体，默认模式。
- free：一个具有自由关节的刚体，需要显式质量和可信惯量策略。
- 显示与碰撞分离，凸包、凸分解和用户提供代理碰撞体。
- 纹理资源提取、基础颜色保留、尺度与轴向转换。
- XML 编译、仿真、渲染与可移植性验证。
- 调用第一阶段现有 API 后再转换的独立串联脚本。

不包含：机器人关节识别、骨骼重建、驱动器、控制器、训练、流体、水的晃动、塑料变形、软体、自动测量真实密度、Web UI、第二个 FastAPI 服务。

四足机器人形状输入只能转换为一个刚体外形；不能因其外观像机器人就声称得到可行走机器人 XML。水马可表示为静态障碍物或指定质量的刚体，不自动模拟灌水。

## 2. 严格解耦约束

第一阶段冻结对象：

```text
/home/mcl/workspace/3D-Assets-Agent
/home/mcl/workspace/hunyuan3d/Hunyuan3D-2
Conda 环境 hunyuan3d
/home/mcl/models/hunyuan3d/Hunyuan3D-2
/home/mcl/models/hunyuan3d/HunyuanDiT-v1.1-Diffusers-Distilled
```

不修改第一阶段源码、配置、Skill、依赖、启动脚本、接口、生成模型、metadata 或 Git 历史；不安装任何第二阶段依赖到 hunyuan3d；不修改 Hunyuan3D upstream。

第二阶段固定配置：

| 项目 | 约定 |
|---|---|
| Git remote | https://github.com/gungnir33/3D-Assets-Mujoco.git |
| 默认本地工程 | /home/mcl/workspace/3D-Assets-Mujoco |
| Python 包 / Conda 环境 | asset_mujoco / asset_mujoco |
| Python 基线 | 3.10 |

本轮检查：目标目录尚不存在；旧建议目录 `/home/mcl/workspace/3D-Assets-MuJoCo` 也不存在，未发现需保留的旧目录工作。默认路径尚未初始化，不能称为已部署路径；后续检查发现旧目录含工作时先报告，不自动删除、改名或重复建工程。

后续初始化前重新执行 `git ls-remote https://github.com/gungnir33/3D-Assets-Mujoco.git`。本轮沙箱 DNS 失败，沙箱外只读重试退出 0 且无 refs，表明检查时无已公布 refs；初始化仍须重新检查。认证失败、404 或网络错误绝不当作空仓库。远端若已有提交，先读取并基于其内容工作；不覆盖提交、不 force push、不创建替代远端、不修改第一阶段 origin。

Git 仅跟踪源码、设计、配置、锁文件和合成 fixture。按目录忽略 outputs（保留 .gitkeep）、real_inputs、模型、环境、.env、密钥和缓存，不全局忽略 *.xml/*.obj/*.png；通过 git check-ignore 测试合成 fixture 可被跟踪。

第一阶段唯一必需接口是资产文件路径。可选 metadata 仅提供来源信息，不是核心转换依赖，不从其 prompt 推断真实尺寸或质量。

串联器只发 HTTP 请求、读取响应的 file/metadata，再调用第二阶段 CLI；不 import 第一阶段 Python 包，不直连其模型对象，不执行其 CUDA 初始化。

独立性证明：复制输入文件及依赖到测试目录，使第一阶段服务不可达、其 Python 包不在环境内，转换仍成功。对第一阶段仓库提交、工作区状态和既有资产 SHA256 做前后对比，不 reset 用户修改。后续显式启用的真实串联可通过原 API 新增独立 job，这是正常输出，不等于修改既有 job；既有资产和 metadata 不得覆盖。本轮不执行串联。

## 3. 架构和方案选择

```text
已有 GLB/OBJ ─────────────────────────────┐
                                        ▼
第一阶段原有 API → 独立 chain.py → 输入检查与快照
                                        ↓
                             Scene 图 / 材质 / 变换解析
                                        ↓
                              坐标、尺度、原点规范化
                                        ↓
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
       visual_geometry   collision_geometry  mass_geometry
       保留形状/UV/材质    凸包/凸分解/代理     质量积分独立副本
              └─────────────────┼─────────────────┘
                                        ↓
                            质量惯量与 MJCF 文档生成
                                        ↓
                         MuJoCo 编译、仿真、离屏渲染验收
                                        ↓
                           model.xml + scene.xml + 资源
```

方案比较：

| 方案 | 优点 | 限制 | 结论 |
|---|---|---|---|
| trimesh + MuJoCo + CoACD | 无第一阶段依赖、CPU 转换、结构可测试 | 需明确材质映射、UV 和凸体质量验证 | 主方案 |
| 全部由 Blender 转换 | 烘焙能力丰富 | Blender 版本耦合、启动开销、节点材质复杂 | 可选适配器 |
| 在第一阶段增加导出模块 | 调用近 | 修改已验收链路与依赖 | 不采用 |

mass_geometry 可仅存在于内存。质量副本焊接与碰撞副本简化不得写入 visual_geometry；不对重叠 CoACD 凸体直接求真实惯量。三类副本分别记录处理过程。

用户提供的 Blender 可作为后续可选工具（复杂 PBR 烘焙不在首版范围）：`/home/mcl/blender-5.2.1-linux-x64/blender`。基础转换不得依赖其安装或用户偏好设置。

## 4. 工程结构与模块接口

```text
3D-Assets-Mujoco/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.lock.txt
├── .gitignore
├── config/default.yaml
├── src/asset_mujoco/
│   ├── cli.py
│   ├── contracts.py
│   ├── pipeline.py
│   ├── inputs.py
│   ├── scene.py
│   ├── transforms.py
│   ├── materials.py
│   ├── collision.py
│   ├── mass_geometry.py
│   ├── inertia.py
│   ├── mjcf.py
│   ├── validation.py
│   ├── rendering.py
│   ├── manifest.py
│   └── errors.py
├── scripts/
│   ├── chain.py
│   ├── check_environment.py
│   └── view_asset.py
├── tests/{unit,integration,e2e,fixtures}/
├── docs/{design,usage,development}/
└── outputs/.gitkeep
```

建议核心类型：

```python
@dataclass(frozen=True)
class SuppliedInertia:
    frame: str             # 仅 normalized_body
    reference: str         # 仅 com
    com_units: str         # 仅 m
    inertia_units: str     # 仅 kg*m^2（文档写作 kg·m²）
    com: tuple[float, float, float]
    tensor: tuple[tuple[float, float, float], ...]  # 严格 3×3
    mass_kg: float          # 与请求质量一致
    final_size_m: tuple[float, float, float]  # 与最终 AABB 一致

@dataclass(frozen=True)
class ConversionRequest:
    input_path: Path
    output_dir: Path        # 输出父目录，可含其他任务
    name: str
    source_up: str           # y / z，OBJ 必须显式指定
    scale: float | None     # 未输入为 None；显式输入须 >0
    target_size_m: tuple[float, float, float] | None  # 最终 X/Y/Z
    yaw_deg: float          # 默认 0，有限，绕目标 +Z
    scale_mode: str         # uniform / fit_axes
    body_mode: str          # static / free
    collision_mode: str     # hull / decompose / supplied / none
    collision_proxy_path: Path | None  # collision=supplied 时必需
    supplied_inertia: SuppliedInertia | None
    validation_level: str   # compile / physics / full，默认 full
    contact_profile: str    # 默认 preserve；engineering_static_v1 仅 static+hull
    mass_kg: float | None
    inertia_mode: str | None # static 可省略；free 强制惯量策略及正质量
    seed: int

@dataclass(frozen=True)
class ConversionResult:
    package_dir: Path
    model_xml: Path
    scene_xml: Path
    manifest: Path
    validation_report: Path
    status: str
```

完整实现类型还包含纹理策略、摩擦、碰撞分解预算、origin 与严格检查开关；统一在 contracts.py 定义并验证，不在模块间传递无约束字典。

主要入口：`convert(request: ConversionRequest) -> ConversionResult`。CLI 只做参数解析和 JSON 输出。scene.py 保留 node/primitive/material 分组；transforms.py 返回统一矩阵；materials.py 返回可视 primitive 及纹理引用；collision.py 返回凸体列表；inertia.py 返回质量、质心、惯量；mjcf.py 接受这些结构并输出 XML；validation.py 返回结构化测试证据。

## 5. 输入契约、来源与安全

GLB 优先，OBJ 次要。第一版不接受 FBX、USD、远程 URL、骨骼动画或压缩扩展隐式下载。

输入检查：

1. resolve 后必须是普通文件，检查扩展名、内容是否可解析；默认最大输入 512 MiB、总面数 5,000,000、纹理展开后总像素预算 64,000,000。
2. 任何几何顶点须 finite；三角面索引合法；不接受空几何或退化三角形。单轴厚度为零的有效平面和单三角形允许进入编译兼容性判定，不在输入层拒绝；体积碰撞与质量积分另要求三维体积。
3. GLB 外部 URI、OBJ MTL 和纹理路径只能位于显式输入资源根目录内；禁止网络访问与目录穿越；符号链接同样检查最终路径。M1.1 的 OBJ 根目录为主文件父目录，实际 resolver 每次读取前 resolve 和边界检查，以受限目录 fd/O_NOFOLLOW 打开并保存字节快照及依赖哈希；禁止检查失败后回退到不受限加载器。
4. OBJ 缺少必需 MTL/纹理时严格报错。M1.1 未开放有损 fallback；未来只有用户显式选择并记录损失才可降级，不能吞掉错误输出灰模成功。mtllib 的 tab、map_Kd 的前导空格必须解析。
5. 稀有扩展如 Draco、KTX2、骨骼、morph target 首版报 UNSUPPORTED_ASSET_FEATURE，不静默丢弃。

源文件只读。记录输入 GLB 或 OBJ+MTL+纹理的全部哈希；在输出工作区建立自己的资源副本。--output 是父目录，可包含其他任务；每次分配唯一 <name>_<id> 最终目录，禁止覆盖。staging 位于同一父目录/文件系统，达到请求自动验证等级后原子发布。输入资源目录与 staging/final 目录不得重叠，防止覆盖来源。发布后重新检查 XML 及报告资源不依赖 staging；源绝对路径只作为 provenance。失败保留诊断目录。

## 6. 坐标、尺度、原点

MuJoCo 工程统一使用米、千克、秒；世界 Z 向上。GLB 按 glTF 约定默认 Y-up，但生成资产可能不遵守语义，允许 source_up=z 显式覆盖；OBJ 没有可靠单位和 up-axis，必须提供参数。

先展开并应用 Scene 节点层级变换，再进行轴变换、尺度和原点变换：

```text
v_output = T_origin × S_scale × R_yaw × R_axis × T_node_world × v_local
```

Y-up → Z-up 采用绕 X 轴正向 90°，统一实现并通过已知非对称模型验证。负行列式镜像变换要翻转面朝向，法线使用逆转置；可视和碰撞副本使用一致全局变换；几何计算惯量基于最终 mass_geometry。supplied 惯量已经属于最终 body，不执行任何二次变换（第 9 节）。

yaw_deg 默认 0 且必须有限，在 up-axis 转换后围绕目标 +Z 按右手规则旋转，再计算缩放。长轴先通过 inspect 确认；target_size_m 是最终 X/Y/Z，不自动排序。用长轴在 Y 的非对称夹具验证 yaw，不用 fit_axes 掩盖方向错误。

supplied 碰撞代理展开自己的 T_node_world 后应用视觉资产确定的同一 G=T_origin×S_scale×R_yaw×R_axis，不单独居中、缩放或自动配准。inspect 输出原始及解析的节点/primitive、材质、纹理、顶点色、AABB、面数和方向参数。

默认原点为规范化后包围盒底部中心，body 放在地面时最低点为 z=0。可选 centroid 和 source，记录转换矩阵、输入和输出 AABB。禁止对材质分块分别居中，禁止再次手工补偿 MuJoCo 编译器内部 mesh 重心变换。

尺度策略：

- scale 输入层为 None；只有用户显式 scale 与 target_size_m 同时提供才冲突。两者均省略时 GLB 解析 scale=1，报告 physical_scale_verified=false。OBJ 必须显式给出 source_up 以及 scale（允许 1）或目标尺寸，不猜单位。
- `--scale`：统一缩放因子，可用于 OBJ 毫米到米的 0.001。
- 显式倍率或目标尺寸也不能证明真实物理尺寸：M1.1 始终 `physical_scale_verified=false`，`scale_evidence.source` 区分 user_multiplier/user_target_size/format_default，记录 applied 和参数，confirmation 为 null。本轮不开发测量系统，旧示例错误字段仅作历史记录，不原地改写。
- `--target-size-m X Y Z --scale-mode uniform`：唯一比例 s=(d·t)/(d·d)，d 为轴转换与 yaw 后尺寸，t 为目标 XYZ，不排列轴。逐轴误差须 ≤0.02*t+1e-7 m。平面零轴要求目标对应轴为零，至少一个正尺寸轴。
- `fit_axes`：显式允许非均匀变形以达到三个目标尺寸，记录形状变形，不作为默认。
- scale 与 target_size 二选一，目标尺寸均须正数。

水马示例尺寸为 1.25×0.13×0.65 m，但模型长轴对应哪个方向必须经预览确认；不会从提示词自动推断。

## 7. 视觉、材质和贴图

### 7.1 原始格式检查与解析核对

先解析 GLB JSON、buffers/accessors、primitive、材质、资源引用与 extensionsRequired/extensionsUsed，再使用固定选项的 trimesh 加载；对照节点/实例/primitive/material 数量与对应表。任何加载器丢失信息都报 PARSER_INFORMATION_LOSS，不能加载后再声称原格式没有不支持特性。

检查 TEXCOORD_0 及其他 UV 集、COLOR_0、alphaMode、baseColorTexture.texCoord、sampler 的 wrap/filter、纹理变换、skin/morph/压缩扩展。首版支持矩阵仅包含经过目标版本测试的特性；非默认 UV 集、纹理变换、镜像/夹取 sampler 等未实现路径明确拒绝，不能静默换 UV 或忽略。未知必需扩展严格失败；已知可显式降级项记录逐项损失。

输入为 Scene 时保留所有可见节点及实例变换；按 primitive/material 分别导出 OBJ，保留 UV seam 的独立索引和正确法线。禁止直接合并全部网格导致贴图丢失。

材质支持分层：

| 输入 | 输出策略 |
|---|---|
| 无材质、无颜色 | 明确默认灰色 RGBA |
| 有 PBR 材质但省略 baseColorFactor | glTF 缺省 [1,1,1,1]，不是无材质灰色 |
| baseColorFactor | MJCF material/geom rgba |
| baseColorTexture + UV | PNG + OBJ UV + XML texture/material 引用 |
| 多材质 | 分别导出 mesh/geom，各自绑定 material |
| vertex color | 首版严格报错，或显式允许均色近似并报告损失 |
| metallic/roughness/normal/emissive 等 | 记录不支持的通道，基础外观模式近似；strict PBR 模式报错 |

不依赖 OBJ 的 MTL 被 MuJoCo 自动解析；XML 显式绑定纹理和材质。颜色因子与纹理相乘只能做一次，禁止重复变暗。首版核心只保证不透明颜色贴图，alpha blend/mask 不保证透明排序，默认报不支持；用户选择 flatten 时使用指定背景色并记录。

M1.1 同时根据原始 GLB COLOR 属性与 OBJ v 行检查源顶点色，存在即明确拒绝，不把加载器默认色误判为输入顶点色。未开放有损顶点色选项。缺省白色、显式全 1、非白因子通过实际像素及 MJCF 材质绑定测试，原始图片不修改。

源法线从解码 primitive/OBJ (v,vt,vn) 对应关系显式保存，不依赖 mesh.copy 的缓存。组合线性变换 A 包含节点世界、轴、yaw 和尺度；导出 normalize(inverse(A).T@n)，镜像只翻一次面绕序。无源法线才计算并标记 normals_source=computed；不焊接视觉 UV seam 或硬边，实际导出 OBJ 的 vn 和面角索引必须回归。

UV 垂直方向、repeat、颜色空间通过四色 UV 图和超范围 UV 测试；非单位纹理变换要么已实现并测试，要么明确拒绝。测试包括纯色纹理、多材质共享图片但颜色因子不同、不同 sampler、非默认 UV 集、缺纹理 OBJ。纯色纹理合法，“非单色”只用于四色夹具，不作通用验收。不能依据一次观察随意翻转 PNG。基础模式下 MuJoCo 渲染效果与 Blender 不会像素一致。

### 7.2 视觉资源编译实验（实施任务 3，早于全面材质导出）

必须在目标 MuJoCo 版本真实调用 MjModel.from_xml_path 和 mj_forward，测试闭合箱体、六面六材质箱体、单三角形材质 primitive、平面可视片+闭合独立碰撞体。geom.mass=0 不能证明 mesh 资源层一定编译成功。

体积子网格正常导出；平面/开放/少顶点资源的参数策略须实测。`mesh inertia="shell"` 仅为候选，当前未验证，不视为通用修复。仅允许经测试保持可见表面、UV、法线的细分适配，记录前后顶点/面数及表面误差；否则报 VISUAL_MESH_UNSUPPORTED。严禁静默加厚、封孔、删除 primitive/材质或改成凸包显示。

逐用例记录目标版本、参数、编译错误和结果。视觉资源编译策略不得改变自由刚体显式 inertial；任务 6 比较编译后质量、COM 和重建张量。任务 3 未解决的特性不能标为支持，若阻断首里程碑则停止并提交具体实验结果。

可视网格默认不减面，以保留第一阶段细节与 UV；超过预算明确报错。仅对独立碰撞副本清理/简化，绝不影响源可视网格。

## 8. 碰撞体策略

显示 geom 设 `contype=0 conaffinity=0 mass=0 group=2`；碰撞 geom 单独定义接触位与 group=3，常规 viewer 隐藏 group 3，碰撞调试时切换。碰撞体与可视体共用一个 body。

默认 hull：对规范化后的原始视觉几何全部顶点取整体凸包，不先简化。预算不够则失败；逐顶点检查在凸包内（数值容差记录），不能简化后声称必然包住原始形状。会封闭水马把手和凹槽，报告 collision_fidelity=convex_approximation，不声称孔洞可穿过。

decompose：使用 CoACD 在清理后的碰撞副本上作近似凸分解。提议预算：碰撞输入≤50,000 faces，最多 32 个凸体，随机 seed=12345，子进程超时 180 秒。超时或超预算默认失败，不偷偷换成单凸包；用户显式 `fallback=hull` 时允许降级并记录。

以上 CoACD 面数、32 凸体和 180 秒仅是资源预算，不保证精度。锁定版本后核对并记录实际误差阈值及单位/归一化语义、预处理、合并、再次减面、每凸体顶点预算和最终凸体数。不虚构默认值。逐凸体检查闭合、凸性、非退化、有限和数量，任何后处理引起的近似都记录；失败 fallback=hull 保留原失败原因。

supplied：必须提供 collision_proxy_path，逐 component 检查闭合凸性；节点展开后用视觉决定的全局 G（第 6 节）。代理只是候选几何，保留孔道仍须当前资产探针实测。

none：仅 static 且用户显式 validation_level=compile 允许，标记 VISUAL_ONLY；physics/full 请求拒绝，不能标物理成功。可单独渲染预览。

孔洞测试依赖 MJCF、仿真夹具，安排任务 8（任务 7 和首里程碑之后）。分别记录标准夹具回归和当前资产 hole_validation；当前资产未配置探针路径时必须为 not_tested，不借用标准夹具结论。

孔洞保持是单独质量目标。对标准带孔测试件放置探针验证穿过孔洞不接触、碰到边框有接触；凸分解不是孔洞准确性的保证。失败须标注 approximation 或要求人工代理。

## 9. 质量、质心、惯量和接触参数

static 不创建 joint、不要求质量。free 创建一个 freejoint、要求 mass_kg>0 和显式惯量策略。不能从颜色/材质外观猜测质量。所有 geom 不重复贡献质量，free 的显式 inertial 为唯一来源。

### 9.1 supplied：最终坐标系输入，不作二次变换

第一版只接受 frame=normalized_body、reference=com、COM 单位 m、惯量单位 kg·m²。用户数据属于最终输出尺寸及指定质量，COM 已在最终 body 坐标下，张量是关于该 COM 并按最终 body 轴表达。配置序列化单位统一 kg*m^2。

不得再次应用 R_axis、R_yaw、S_scale、T_origin 或平行轴项。source frame 明确 UNSUPPORTED_INERTIA_FRAME；不猜单位、不仅旋转后继续使用。若用户改变尺寸/原点，必须重给符合新最终 body 的 COM/张量；同一真实物体仅改变 body 原点时关于 COM 的惯量本身不变。

验证：质量和所有数有限；张量严格 3×3。提议相对容差 1e-8、绝对容差 1e-12 kg·m²；对称误差在容差内才允许数值对称化并记录，超出报错。最小特征值必须 >0，最大主惯量不超过其余两者之和+容差。目标尺寸容差为 rtol=0.02、atol=1e-7 m；几何数值一致性（含 supplied.final_size_m 对最终 AABB）为 rtol=1e-6、atol=1e-7 m；惯量数值一致性为 rtol=1e-8、atol=1e-12 kg·m²；质量匹配另用 rtol=1e-8、atol=1e-9 kg。分别记录，不混用；加入 float32 0.13 m 用例。

XML fullinertia 顺序拟为 Ixx Iyy Izz Ixy Ixz Iyz；目标版本通过非零非对角项测试核对。编译后用 body_iquat 与 body_inertia 重建张量，与 supplied 的 body 坐标张量、body_ipos、body_mass 比较，避免只看特征值漏掉方向错误。

### 9.2 box_approx

使用最终 X/Y/Z 包围盒与显式质量：Ixx=m(Y²+Z²)/12，其余循环；COM 是最终 body 下盒中心。报告 approximate=true，不能声称反映空心水马密度分布。

### 9.3 watertight 与独立 mass_geometry

mass_geometry 是规范化几何的独立副本，可仅驻留内存。只在此副本处理 UV seam 重复顶点；默认优先精确重合焊接，若需容差焊接，必须显式设置相对模型尺度容差、记录实际米制值并验证部件边界/薄壁不被合并；没有可靠局部间距证明则拒绝近邻焊接。visual_geometry 的位置、UV、法线及哈希必须保持不变。不自动封孔。

is_watertight、方向一致、正体积只是必要条件，不足以证明积分可信。首版保守接受经过拓扑与自交检测证明的单一闭合、方向一致、无自交实体。多部件重叠、嵌套壳、开放面、自交或无法确定体积语义报 UNTRUSTED_MASS_GEOMETRY；明确要求用户选择 box_approx/supplied，不静默回退。自交检测后端及容差任务 8 实测并锁定；无法证明前提就拒绝该输入，不引入未经验证布尔修复。

计算最终 mass_geometry 的均匀实体积分，缩放到指定质量；报告 mass_model=uniform_solid_assumption。不对可能重叠的 CoACD 凸体累加惯量。

### 9.4 必须测试的物理契约

- 12 kg、1.25/0.13/0.65 m 箱体解析值；均匀尺寸扩大 2 倍、质量不变时 box/watertight 计算惯量扩大 4 倍，supplied 不参与这种自动缩放。
- 非对称箱体旋转后的张量和编译方向正确；body 原点移动仅改变 COM 表达，不重复增加平行轴项。
- UV seam 箱体质量副本处理正确，视觉副本不变。
- 重叠闭合箱体不能仅凭 watertight 通过；开放、自交、嵌套壳全部失败。
- 非法 frame/reference/units、负特征值、非对称张量明确失败。

摩擦三个分量可配置且非负，记录锁定 MuJoCo 的实际默认值，不宣称真实 PE 系数。0.002 s 和 gravity=0 0 -9.81 只适用于测试场景，不覆盖宿主设置。

## 10. 输出资源包与 XML

```text
outputs/<name>_<short-id>/
├── model.xml                  # 单资产独立可编译，无全局地面/灯光
├── scene.xml                  # 带地面、灯光、相机的演示场景
├── contact_scene.xml          # M1.2候选可选：公开双方同参数的探针场景
├── meshes/visual_000.obj
├── meshes/collision_000.obj
├── textures/basecolor_000.png
├── conversion_manifest.json
├── contact_result_manifest.json # 运行native后记录实际参数、范围和统计
├── validation_report.json
├── conversion.log
└── previews/{front.png,side.png,iso.png,collision.png}
```

model.xml 和 scene.xml 都是完整 MJCF 文档；由同一个中间结构生成 asset/body，scene 额外添加演示设施，首版避免跨场景 include 路径和命名陷阱。所有 mesh/texture 路径相对 XML 所在包目录；在不同工作目录加载仍成功。资源命名加入资产前缀防冲突。

model.xml 为 static/free 中用户选定模式，scene 不擅自改变物理模型，仅 free 演示时抬高整体放置位置供跌落测试。scene 中 camera 与 ground 尺寸按资产包围盒生成。

XML 使用 ElementTree 构建，禁止字符串拼接用户名称。显式指定 angle=radian、autolimits=true；自由刚体具有合法 inertial，碰撞 geom 不透明度由调试 viewer 控制。

新增 examples/merge_into_minimal_host.py 和 tests/integration/test_host_merge.py：在自建最小宿主场景合并 model 的 asset/body，重映射名称前缀与相对资源路径，断言无重名、宿主选项不变、质量/COM/惯量和接触模式不变，并真实编译。不得修改用户真实 ACS 场景；不能把带 ground 的 scene.xml 无条件 include。自动多物体组合仍属后续范围。

--output 仅为父目录。验证通过才将唯一 staging 原子发布为唯一包；发布后从最终路径与另一工作目录重新加载。报告的 package 内路径都相对化，不能残留 staging 加载依赖；来源字段允许源绝对路径。

## 11. CLI 和串联契约

以下均为拟实现命令，审核前不可当作已有工具运行。

```bash
conda run -n asset_mujoco python -m asset_mujoco.cli inspect \
  --input /absolute/model.glb

conda run -n asset_mujoco python -m asset_mujoco.cli convert \
  --input /absolute/model.glb --output /absolute/mujoco-output \
  --name barricade --source-up y --body-mode static --collision hull

conda run -n asset_mujoco python -m asset_mujoco.cli convert \
  --input /absolute/model.glb --output /absolute/mujoco-output \
  --name barricade --source-up y --target-size-m 1.25 0.13 0.65 \
  --scale-mode fit_axes --body-mode free --mass-kg 12 \
  --inertia-mode box_approx --collision decompose
```

12 kg 仅是调用示例，不是水马实测重量。输出 JSON 至 stdout，进度/日志至 stderr。成功提供 package/model_xml/scene_xml/manifest/validation；失败提供 code、stage、message、details 和失败工作目录。

退出码：0 请求等级的自动检查成功（不表示人工审查完成）、2 参数/输入错误、3 转换失败、4 编译失败、5 物理或渲染内容检查失败、6 第一阶段连接/请求失败或结果未知、7 full 要求渲染但后端不可用。validation_level 与总体状态按第 13 节聚合。

串联请求例子：

```bash
conda run -n asset_mujoco python scripts/chain.py \
  --request /absolute/phase1-request.json \
  --conversion-config /absolute/phase2-config.yaml \
  --output /absolute/mujoco-output
```

仅共享本地文件系统串联。本轮只读核对 schemas.py/app.py：/generate/text 使用 prompt；/generate/image 使用 image；/generate/texture 使用 mesh、condition_image；成功响应为 job_id、file、type、metadata，file/metadata 是服务端路径而非内嵌对象。实施任务 9 前再次核对。

phase1-request.json 明确 endpoint 和原 payload，发请求前限制 format=glb/obj，默认 glb，拒绝 fbx。返回后验证 file 可读、类型与内容受支持；OBJ 同时验证依赖。metadata 可选读取，缺失/不可读时警告，但不阻止参数完整的独立转换。不会把远程机器路径视作共享本地文件。

服务由用户按原流程启动，chain 不 daemonize、不 import 第一阶段。HTTP timeout=1800 s，loopback 客户端 trust_env=False，仅作用该客户端，不改变全局代理。兼容 FastAPI 422 的 detail（列表或其他 JSON 值）以及业务 error.code/message/details，保留 HTTP 状态及原始原因；非 JSON 响应保存有长度限制的原文与 content-type。

不自动重试生成 POST。超时报 phase1.status=unknown，结果可能仍在生成，不声称取消；再次转换须用户定位已有结果后显式恢复。连接失败、422、503 和非 JSON 错误分别记录。

第一阶段成功后保留原 job/file/metadata，第二阶段失败仍输出 phase1 成功结果。恢复时用 `convert --input <原结果>`，无需再次生成。两阶段日志和 manifest 分开存放，chain_manifest 仅引用二者。

## 12. 版本、依赖与资源管理

独立环境候选依赖：Python 3.10、numpy、trimesh、Pillow、pydantic、PyYAML、mujoco、httpx、pytest。CoACD 为可选功能依赖；选择 trimesh 减面接口时必须核对 fast-simplification 等真实后端并加入扩展 lock，不以调用方法存在证明依赖完备。无需 Torch、HunyuanDiT、Hunyuan3D 或 CUDA 推理包。

确定版本前只读调查实际目标宿主。本轮安装元数据发现 acs_test 为 MuJoCo 3.2.3、sim_test/.conda-env 为 3.4.0；尚未确认哪个是目标宿主，也未运行库确认加载路径。host_compatibility=pending，安装版本不等于编译兼容证据。清单分别记录 converter_version、tested_versions、host_version、host_compatibility，任务 1 再识别宿主，任务 3/10 进行精确版本测试。不声称兼容所有版本，不升级第一阶段。

不在方案中捏造“已验证版本”。实施任务 1 在独立环境安装相互兼容的确定版本并生成精确 lock；MuJoCo/CoACD 版本和许可证纳入 deployment manifest。若可用版本要求更高 Python，则先报告独立环境版本调整，不触碰 hunyuan3d。

转换默认 CPU。EGL 与 OSMesa 分别在独立子进程中探测，导入 MuJoCo/渲染模块前设置 MUJOCO_GL；不在同进程切换后端。OSMesa 成功就是有效渲染，与有无 GPU 无关。GLFW viewer 单独记录；碰撞 group 显隐在 Renderer 与 viewer 均测试，只影响显示不关闭碰撞。渲染失败不修改驱动，清单记录后端、版本、许可证与错误。Blender 可选不参与核心依赖。

不生成单个 MJB 作为标准分发格式。资源包 XML/OBJ/PNG 与版本记录更便于审核；任何缓存只在第二阶段目录中。

## 13. 验收与测试矩阵

| 层次 | 测试 | 必须证明 |
|---|---|---|
| 单元 | 路径、材质、坐标、惯量、XML 名称 | 非法输入明确失败，数值和变换正确 |
| 结构集成 | GLB/OBJ→资源包→编译 | 原有三份资产可转换，资源引用完整 |
| 视觉 | 四色 UV 测试、多材质、灰色模型 | 不倒贴、不丢色、不把无材质伪装为有纹理 |
| 物理 | 静态接触、自由落体、孔洞探针 | 模式和碰撞能力符合声明 |
| 可移植 | 复制输出到新目录加载 | 不依赖源目录和第一阶段模型路径 |
| 解耦 | 无服务、无第一阶段 Python 包 | 已有资产转换可独立完成 |
| 串联 | mock API + 显式真实测试 | phase1 失败保留原因，phase2 失败可恢复 |

测试样例包括：三角化箱体、不同颜色四象限纹理、含多节点变换和负尺度的 Scene、多材质对象、薄板/开放网格、带孔测试件、缺纹理 OBJ、空模型、NaN 顶点。

编译门槛：`mujoco.MjModel.from_xml_path()` 加载 model.xml 和 scene.xml，创建 MjData 并执行 mj_forward。不得以 XML 语法正确代替引擎编译。

仿真门槛：测试场景显式启用 energy 计算，禁用 autoreset（具体 enum/flag 在目标版本核对并断言生效，不 mock）。0.002 s、1000 steps；在 mj_forward 前后与每次 mj_step 后检查 qpos/qvel/qacc/energy 全部 finite，时间每步增长 dt（atol=1e-10、rtol=1e-8），记录首次异常步和异常前状态。即使版本不能关闭自动重置，时间倒退/非预期增长及 warning 检查也必须将其判失败，不能只检查最终有限状态。

warning 按枚举名称分类：BADQPOS/BADQVEL/BADQACC、BADCTRL、惯量/求解数值异常和 CONTACTFULL/CNSTRFULL/VGEOMFULL 等资源溢出增量失败，未知新增 warning 默认失败并报原始编号。实际可用枚举及分类随锁版本记录；不一概忽略。

接触断言具体 geom 名对：落体-ground、probe-frame 必须在规定阶段出现接触，probe-hole 定义路径内不得出现接触。落体穿透阈值 min(0.005 m, 高度的 2%)；稳定箱体才断言终态速度（提议线/角速度各 <0.05 SI 单位），任意资产不套用静止条件。记录探针尺寸、路径、时段和预期对；不只看 ncon。孔洞测试在任务 8、仿真模块完成后运行。

视觉门槛：front/side/iso 与碰撞叠加图由 MuJoCo 原生渲染。有纹理资产检查 texture/material 绑定和预览，纯色纹理合法；仅四色测试夹具断言四种预期色与位置，非空/非单色不等于真实外观保真。真实资产人工审查记录 reviewer、时间、模型哈希、查看图片和结论，默认 pending，不自动填写 approved。

独立维度及示例（仅结构示例，不是本轮实测结果）：

```json
{"compile":"passed","physics":"passed","render":"unavailable","appearance_review":"pending"}
```

| validation_level | 必需自动检查 | 退出与最高聚合状态 |
|---|---|---|
| compile | 两份 XML 编译 + mj_forward | 成功 0 / COMPILE_VALIDATED，physics/render=not_run |
| physics | compile + 当前资产指定工况夹具 | 成功 0 / SCOPED_PHYSICS_VALIDATED，render 可 not_run |
| full（默认） | compile + physics + render | 指定工况自动成功 0；人工 pending 时 SCOPED_PHYSICS_VALIDATED，automatic_validation=passed |
| full 且 render unavailable | 已做检查各自保留 | 退出 7；指定物理工况已过仍 SCOPED_PHYSICS_VALIDATED |
| full 且 render passed 但 physics failed | 保留 render=passed | 退出 5，不能升级物理状态 |
| full 且指定工况通过且人工 approved | 所有范围证据齐备 | 最多 SCOPED_FULLY_VALIDATED |

CONVERTED 仅转换阶段完成，不表示任何引擎测试通过；编译失败时保留该阶段事实及失败原因。人工审查不影响自动命令退出码，只能批准外观，最多决定 SCOPED_FULLY_VALIDATED。compile 允许 passed/failed/not_run；physics 允许 passed/failed/not_run/not_applicable；render 允许 passed/failed/not_run/unavailable；appearance_review 为 pending/approved/rejected。渲染不可用不推翻物理通过，人工 rejected 则不能最终通过。不得输出无范围的 PHYSICS_VALIDATED/FULLY_VALIDATED。

M1.2 范围修订：唯一 ValidationResult/aggregate 与 checked_report 为所有入口的共同契约。validation_scope 包含稳定 case_id、required_pairs、实际 conditions、相对路径 evidence_refs 和 evidence_status（unknown/declared/verified/missing/stale/contradictory）。static 的当前范围为 native_asset_probe_v1，非资产名称；阈值、步长、时长、探针/初态/版本来自本包 native 与 XML，不硬编码企鹅或5毫米。compile-only 仅 declared。followup_ground 独立保留 status、mandatory_for_physics=false、比较阈值和证据引用，失败不否定已验证的指定接触对，也不允许宣称全场景通过。application_force_limit=not_specified、host_integration=pending、robot_contact_safety=not_validated 与 limitations 同时序列化。

写入顺序：conversion_manifest 中 scope_reporting_version=1 → 编译证据 → native/contact结果及物理证据 → 派生范围摘要 → 独立渲染证据及最终摘要。范围投影不纳入自身哈希；读取时重新核对已有哈希和 native/contact 语义一致性，并核对新包缓存。删除缓存版本不能取消受绑定版本契约。旧包完整依据允许只读派生，不回填、不补签；证据不足保留可核实层事实，禁止受限通过或退回裸通过。人工审核仍独立绑定包指纹，不参与范围构造，不得扩大工况或改写地面结果。迁移使用相对资源哈希不失效。

collision=none 必须 static+显式 compile，asset_kind=VISUAL_ONLY、physics=not_applicable，不得 PHYSICS_VALIDATED/FULLY_VALIDATED。用户可另行渲染预览但不升级物理状态。

原有三份真实输入作为只读 E2E，实施前重新检查存在性、原始 GLB JSON 和材质特征；缺失则报告，不自动调用第一阶段重新生成。本轮仅解析容器信息，前两份 POSITION 无材质，第三份 POSITION+TEXCOORD_0、1 材质和1图片，未做转换或 MuJoCo 验证：

```text
/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210330_6c804545/model.glb
/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210532_fe231a7e/model.glb
/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb
```

不把这些真实资产提交到第二阶段 Git；测试中通过显式 fixture 路径引用，仓库仅保存程序生成的小型合成 fixture。


物理通过必须绑定当前转换资产和碰撞资源哈希，并执行该资产的动态探针或 free 刚体测试，断言具体 geom 对、预期接触和逐步数值状态；标准箱体回归不能替代。VISUAL_ONLY 序列化 physics=not_applicable，聚合始终 VISUAL_ONLY。

M1.1 原始配置验收不得添加强制 contact/pair 或改写资产碰撞位、摩擦、solref/solimp；探针初始位置由转换参数确定并记录，碰撞体被移动后不能重新瞄准。独立 benchmark 可使用明确记录的强制 pair，仅作为受控基准。physics=passed 必须以 native=passed 为前提；原始失败而 benchmark 通过仍失败。保留既定 min(0.005 m, 高度2%) 穿透阈值，逐步记录首次异常（包括首次超限）、具体接触对和时段。历史 1.19 mm 仅属于定制夹具，不能视为原始配置保证。

M1.2 经显式批准增加可选 `contact_profile=engineering_static_v1`，仅 static+hull；默认仍为 `preserve`，不改变旧输出参数。工程约定为 solref=[0.006,1]、solimp=[0.9,0.95,0.001,0.5,2]，不是材料测量。导出时资产写入参数，scene.xml 的 ground 同步写入；新增公开 contact_scene.xml，包含完全沿用基线质量、半径和初始位置的 probe，双方采用相同参数。native 直接读取该交付场景，不增加 pair、override 或运行时接触配置。摩擦、碰撞位、priority、solmix、dt=.002、1000步及原阈值不改。free 或非 hull 的候选请求拒绝；不自动修改任何宿主。只给资产设置 .006、对方仍 .02 时不满足配置契约，实际解析结果必须报告，不能借用双方一致的通过结论。

M1.2 的 physics 判定范围明确为既定当前资产—探针工况，`acceptance_scope` 明示具体 geom 对；额外 `followup_ground` 单独记录是否发生、相同阈值下结果和非原验收门槛属性，不能用资产接触通过暗示整个场景达标。接触统计分资产—探针、ground—探针，记录实际参数、峰值法向力、积分冲量、接触时段和接触期间分离速度。力为同次求解的接触坐标系量，世界冲量明确作用于 probe；不是恢复系数标定。`application_force_limit=not_specified`，不声明机器人安全。dt、落点、解析几何和有限质量/半径变化仅在新诊断副本执行，先存固定实验计划，不回写正式参数。扩展超限必须保留并限制结论，人工和真实宿主继续 pending。

验收补强：benchmark为非强制诊断项。native完成后立即持久化结果、独立内容哈希和分层状态，再运行benchmark；其可恢复异常只记stage/type/message/已有文件，不更改native通过或原失败原因，不阻止独立渲染。native异常只产生失败证据；证据持久化或哈希I/O失败为EVIDENCE_IO_ERROR，禁止发布成功包，与物理超限区分。
test_real_asset_native_failure_is_reported只验证已知失败被正确处理；独立python -m asset_mujoco.acceptance才执行真实GLB的compile/native/render/迁移达标门槛。缺原始输入报告not_executed，不达标非零退出，不以回归全绿或诊断达标替代。
独立contact_diagnostics只操作新副本，执行前保存有限参数组，先验证未改基线再做控制变量实验。trace明确积分前采样和积分后时间，分列首次接触、首次超限、最大穿透步；累计接触记录不等于独立撞击次数。正式参数调整必须用户另行批准，未来native验收应测试新交付XML，不在验证器覆盖配置。

人工审查保存于 appearance_review.json：reviewer、UTC 时间、结论、审查图片相对路径与哈希、package_content_sha256。对包内排序的相对路径和内容 SHA256 列表计算包指纹，包含 XML/资源/预览/转换配置/验证证据，仅排除审查文件本身及可重算 aggregate_status.json，避免循环。report 每次重算指纹，改变受绑定内容后旧 approved 失效为 pending，保留旧记录用于审计。没有有效人工批准不得 SCOPED_FULLY_VALIDATED；有批准也不允许无范围的 FULLY_VALIDATED。

## 14. manifest 和可追溯性

M1.1 `evidence_manifest.json` schema_version=2 使用包相对路径及 SHA256。compile 绑定 model.xml/scene.xml/转换清单/引用网格和纹理；新physics绑定实际native夹具及physics_native_evidence.json，context.native_evidence指定主证据，benchmark_evidence.json和physics_evidence.json汇总不作为该层依赖。旧包继续按原physics_evidence绑定检查，不能重新签名冒充新版验证。native初始化异常未生成XML时保留失败结果；通过证据必须含nativeXML。render另绑定渲染配置、后端结果与四张预览。每层保存当时的上下文、状态和摘要，汇总状态、日志及人工审查不参与分层自动证据哈希，不形成循环。report只校验原记录；缺失、旧格式或内容变化使旧passed失效为not_run，不运行引擎、不重签。人工审核仍保留独立历史和更保守的整包内容绑定。原样迁移只改变目录，不失效。

M1.2 可选公开 contact_scene.xml 及引用资源加入 compile 清单；contact_result_manifest.json 保存实际 native 解析对象、接触参数、适用范围、后续地面结果和统计，并绑定 physics 层。conversion_manifest 只声明配置来源、参数、使用对象和运行结果文件名，不在物理运行后循环修改。更改公开场景或运行结果清单使对应旧证据失效；迁移不失效。benchmark 依然不参与 native 证据依赖。

conversion_manifest 至少包含：schema_version、转换器 commit、依赖版本、源路径与各资源 SHA256、可选第一阶段 job 引用、完整已解析参数、输入/输出 AABB、轴变换矩阵、尺度、原点、材质映射、近似/丢弃通道、可视/碰撞面数、凸体数、质量惯量与来源、seed、每阶段耗时、输出文件哈希。

validation_report 分别记录 compile/physics/render/appearance_review、validation_level、automatic_validation 和聚合状态/退出码；包含转换环境版本、实际测试版本、宿主兼容状态、body/joint/geom/mesh/material/texture 数量、每步数值检查、首异常步、autoreset/energy 开关、时间/告警、具体接触对、标准孔洞与资产 hole_validation、渲染后端和相对图片路径。峰值 CPU 内存可采样记录；不伪称精确 GPU 峰值。

manifest 额外记录 yaw、最终 X/Y/Z、scale 是否显式、代理共用矩阵、supplied frame/reference/units、mass_geometry 焊接/自交检测容差、全部 CoACD 实际参数及来源、可视编译适配和原始格式/解析映射。包内引用不包含 staging 绝对路径。

输入哈希和配置相同不承诺跨平台二进制一致，但要求固定版本+seed 下重复转换的包围盒、碰撞体数量与数值结果在约定容差内。清单记录能重现结果的实际配置，而不是仅保存 CLI 原字符串。

## 15. 分阶段实施计划与首个里程碑

以下保留 R2 的十项任务及验收清单，具体已执行/未完成子项以 M1_IMPLEMENTATION_REPORT.md 为准，只在第二阶段独立仓库实施。每项顺序为失败测试→最小实现→测试通过→本地阶段提交。任务 3 是真实引擎实验，不要求对不支持候选伪造预期成功。推送需后续明确授权，本轮不推送。

### 任务 1：独立仓库、环境、冻结边界和完整契约

依赖：审核批准。新增 pyproject.toml、config/default.yaml、contracts.py、cli.py、scripts/check_environment.py、.gitignore、requirements.lock.txt、tests/unit/test_contracts.py、tests/integration/test_isolation.py。

- [ ] 重新检查指定远端/新旧目录/已有提交与实际宿主环境；不把访问失败视为无内容。记录第一阶段状态和既有输入 SHA256。
- [ ] 统一实现 SuppliedInertia、ConversionRequest、结果/分层状态：scale=None、yaw、最终 XYZ、代理路径、frame/units、validation_level、输出父目录。
- [ ] 测试显式 scale+target 冲突、省略 scale 不冲突、OBJ 缺单位失败、NaN yaw 失败、supplied 缺字段失败、VISUAL_ONLY+full 失败。
- [ ] 在 asset_mujoco 独立环境锁依赖；识别宿主版本后决定 converter 版本，并记录未测兼容性。git check-ignore 断言 XML/OBJ/PNG 合成 fixture 可跟踪、真实资产不可跟踪。
- [ ] 通过标准：pytest tests/unit/test_contracts.py tests/integration/test_isolation.py -q；目录与 remote 精确匹配、第一阶段基线未改变。提交 chore: initialize isolated converter contracts。

任务 1 补充验收：static 可省略 inertia_mode、free 强制质量/惯量；VISUAL_ONLY JSON 往返及状态聚合；三类容差、float32 0.13 m 和 uniform 唯一比例规则；人工审核哈希失效与重算测试。任务 2/5/7 实测对应几何、惯量和物理行为。

### 任务 2：原始输入、Scene、尺度与 yaw

依赖：任务 1。新增 inputs.py、scene.py、transforms.py、tests/unit/test_raw_features.py、tests/unit/test_scene_transform.py、tests/unit/test_paths.py。

- [ ] 先写带 COLOR_0、第二 UV 集、纹理变换、压缩/skin/morph 声明的最小 GLB JSON fixture，断言原始特性在 trimesh 前可见且不能丢失。
- [ ] 固定加载选项并比对节点/primitive/material/实例映射；支持路径资源根目录检查与依赖哈希。
- [ ] 非对称长轴 Y 夹具先轴变换再 yaw 后缩放；验证 G 矩阵、镜像绕序、法线、uniform 2% 和 fit_axes 显式变形。代理共用 G 的接口保留到任务 8。
- [ ] 通过标准：pytest tests/unit/test_raw_features.py tests/unit/test_scene_transform.py tests/unit/test_paths.py -q，资源穿越拒绝，已知顶点/尺寸误差在记录容差内。提交 feat: inspect and normalize asset scenes。

### 任务 3：可视子网格最小 MuJoCo 编译实验

依赖：任务 1–2；必须早于任务 4。新增 mjcf.py 的最小实验构造器、tests/integration/test_visual_mesh_compile.py、docs/design/visual_mesh_compatibility.md。

- [ ] 创建闭合箱体、六面六材质箱体、单三角形 primitive、平面视觉片+闭合碰撞体四类 fixture。
- [ ] 每类真实运行 MjModel.from_xml_path 和 mj_forward；记录版本、顶点面数、参数、错误。分别测试正常设置及 shell 候选，不能 mock。
- [ ] 验证候选细分不改变表面点集/UV 插值/法线、材质和 primitive 数；不能加厚或封孔。少顶点即使 shell 失败也完整报告。
- [ ] 通过标准：目标版本适配矩阵齐全；支撑首里程碑的视觉策略实测可用，不支持的类型有明确错误。不满足时停止并报告，不删 primitive 通过。
- [ ] 提交 test: establish visual mesh compilation compatibility。此时仅有合成编译证据，不能声明真实资产已转换。

### 任务 4：材质与视觉资源

依赖：任务 2–3。新增 materials.py、tests/integration/test_visual_assets.py；扩展 mjcf.py 测试资源构造器与版本化特性支持矩阵。

- [ ] 先写四色 UV、纯色纹理、不同 factor、多材质共享图、超范围 UV、非默认 UV/变换、缺纹理 OBJ 用例。
- [ ] 原始格式检查与解析结果二次核对；提取 OBJ/PNG、显式 XML 材质绑定；仅已测试 sampler/UV 路径受支持，其他明确失败或显式损失记录。
- [ ] 用任务 3 策略真实编译；为材质用例提供最小独立子进程原生渲染测试，四色夹具检查预期位置和颜色、纯色图检查资源绑定及预期纯色。
- [ ] 通过标准：pytest tests/integration/test_visual_assets.py -q；颜色因子仅一次，visual seam 不丢失，纯色不会被判失败。若渲染后端不可用，记待验证，不能宣布视觉已通过。
- [ ] 提交 feat: export verified visual materials。

### 任务 5：hull、box_approx、supplied 基础策略

依赖：任务 2–4。新增 collision.py、inertia.py、tests/unit/test_inertia.py、tests/integration/test_hull.py。此任务 supplied 指惯量；supplied 碰撞代理在任务 8。

- [ ] hull 从规范化原始全部视觉顶点计算；测试所有源点包含于凸包容差内，预算失败不先简化。
- [ ] box 解析惯量与两倍尺寸四倍惯量测试；supplied 单位、质量/尺寸匹配、正定/对称/三角约束测试。
- [ ] 非对角张量按 MJCF 顺序输出后编译重建，COM/质量/方向正确；同 supplied 输入不经过 G；source frame 失败。
- [ ] 通过标准：pytest tests/unit/test_inertia.py tests/integration/test_hull.py -q；仅移动 body 原点不重复修改 COM 惯量。提交 feat: add baseline collision and inertial policies。

### 任务 6：static/free MJCF 和可移植包

实施数值适配记录：3.4.0 对一个非对角 fullinertia 测例重建误差约1.52e-7，未达到既定阈值。输出改为由最终 COM 张量显式求特征分解，写 diaginertia 和惯性坐标系 quat；真实编译后重建张量通过原 rtol=1e-8、atol=1e-12，不放宽阈值、不重新变换 supplied 数据。输入仍为完整对称张量。

依赖：任务 3–5。新增 pipeline.py、manifest.py，扩展 mjcf.py；新增 tests/integration/test_mjcf_compile.py、test_package_publish.py、test_host_merge.py、examples/merge_into_minimal_host.py。

- [ ] 从同一中间模型输出 model.xml/scene.xml；无重复质量、static 无 joint、free 的 supplied/box 编译值符合输入，视觉资源编译参数不影响 body inertial。
- [ ] --output 父目录含其他 job 仍可成功；唯一 staging、唯一包、并发命名冲突重分配或失败、不覆盖既有包。
- [ ] 达到请求自动等级才发布；先实现 compile 等级。验证相对引用、发布后报告无 staging 依赖、复制到新目录后两份 XML 编译+forward。
- [ ] 在合成宿主中合并 asset/body 并断言名称/资源无冲突、宿主 option 不变、物理属性不变，不碰真实 ACS 场景。
- [ ] 通过标准：上述三个测试文件通过；失败目录保留诊断。提交 feat: publish portable static and free mjcf packages。

任务 6 增加非默认宿主 compiler 配置测试：angle、inertiafromgeom、meshdir/texturedir、fusestatic、balanceinertia。分别报告语法支持、几何编译、物理/渲染效果；不兼容返回 HOST_COMPILER_CONFLICT，不静默修改宿主 compiler/option。

### 任务 7：物理、渲染、状态验证及首个可用里程碑 M1

依赖：任务 6。新增 validation.py、rendering.py、scripts/view_asset.py、tests/e2e/test_physics_render.py、tests/unit/test_validation_states.py、tests/e2e/test_milestone_static.py。

- [ ] energy 显式开启、autoreset 禁用并核对；每步 qpos/qvel/qacc/energy/time/warning 检查，异常记录首步，注入测试验证自动重置不能伪通过。
- [ ] 合成落体与 static 动态探针断言具体 geom 对、预期接触时段和穿透；此时不实施孔洞专项。
- [ ] EGL/OSMesa 各独立进程、导入前设置后端；GLFW 单独。三视图与碰撞显隐，OSMesa 通过等同有效 render。
- [ ] 测试 compile/physics/full 退出码矩阵，physics passed + render unavailable 保留指定物理工况通过，appearance pending 不得 SCOPED_FULLY_VALIDATED，VISUAL_ONLY 不升级。
- [ ] 用已有真实带纹理 GLB 建立 M1：inspect 确认方向→明确 scale/XYZ→static+hull→model/scene 编译→动态探针正确→原生渲染颜色/贴图正确→迁移后重载。用户人工审查结果单列，不自动批准。
- [ ] 通过标准：M1 上述自动闭环全部有证据，人工外观审核记录独立状态；pytest 对应三文件通过。提交 test: validate baseline real asset pipeline。

**M1 是第一个可用里程碑。闭环未通过，不优先开始任务 8 的 CoACD/质量积分，亦不开始任务 9 串联。free 基础策略可在合成夹具验证，M1 的真实资产范围仅 static+hull。**

### 任务 8：CoACD、碰撞代理、mass_geometry/watertight 与孔洞

依赖：M1 自动闭环、任务 7 物理夹具。新增 mass_geometry.py、tests/integration/test_decomposition.py、test_collision_proxy.py、test_mass_geometry.py、tests/e2e/test_hole_contact.py；扩展 collision.py/inertia.py 与可选依赖锁。

- [ ] 核对 CoACD 与减面实际依赖（包括选用 fast-simplification 时的版本），锁实际阈值语义、预处理/合并/后减面/顶点预算；资源预算与精度分开。
- [ ] 测试超时终止子进程、非法凸体/数量超限失败，显式 fallback 记录失败原因。代理先自身节点变换再使用视觉 G，断言相对位置和尺度没有重新归一化。
- [ ] mass 副本 UV seam 焊接测试视觉哈希不变；重叠箱体、自交、嵌套壳、开放输入失败；单实体积分验证双倍尺寸四倍惯量与原点平移。
- [ ] 自交/焊接后端和容差须证据支持，无法证明就拒绝 watertight。不得安装到 hunyuan3d。
- [ ] 孔洞夹具断言 probe-frame 接触与 probe-hole 不接触；真实资产无探针路径必须 not_tested，标准夹具通过不外推。
- [ ] 通过标准：上述四测试文件及相关惯量回归通过；明确每种近似/不支持状态。提交 feat: add validated advanced collision and mass geometry。

### 任务 9：第一阶段 HTTP 串联

依赖：M1、任务 6–7。新增 scripts/chain.py、tests/integration/test_chain.py。

- [ ] 实施前再次只读核对 schemas/app；模拟 text/image/texture payload 和 job_id/file/type/metadata 路径响应。
- [ ] 请求前 GLB/OBJ 格式检查；共享本地路径、metadata 可选、OBJ 资源依赖检查。
- [ ] mock 200/422 detail/503 error/非 JSON/连接失败/1800s 超时，断言无自动重试、超时 unknown，不假定取消。
- [ ] phase1 成功、phase2 失败返回完整已有来源，独立 convert 可恢复。无第一阶段 import/模型初始化/服务启动。
- [ ] 通过标准：pytest tests/integration/test_chain.py -q；真实生成 POST 本轮及默认测试都不执行，后续仅显式启用且新增唯一 job。提交 feat: chain existing generation protocol safely。

### 任务 10：三份真实资产、文档和部署证据

依赖：任务 1–9；基础模式失败不得被高级模式掩盖。新增 tests/e2e/test_existing_assets.py、docs/usage、docs/development、deployment_manifest.json。

- [ ] 再检查三份输入的实际原始材质/顶点色/扩展及哈希，缺失报告，不重生成。
- [ ] 独立环境且 phase1 不可达下执行三份转换，验证灰色/纹理各自预期，static/free 及碰撞模式明确标注证据；复制包重载，最小宿主兼容测试独立记录。
- [ ] 记录 converter 版本、实际验证版本、目标宿主及兼容状态；未指定/未测试版本 pending，不能宣称全版本兼容。
- [ ] 人工审查记录与自动结果分开，SCOPED_FULLY_VALIDATED 只能指定范围证据齐全时使用，不允许裸 FULLY_VALIDATED；后续任务涉及的 CoACD 参数、质量假设、孔洞状态须完整报告。
- [ ] 对比第一阶段仓库状态与既有输入 SHA，新的显式串联 job 独立列出。
- [ ] 通过标准：tests/unit、tests/integration 与显式 E2E 报告完整；限制与未实测内容如实记录，源码/合成 fixture 可提交、真实资产不提交。提交 docs: document validated conversion and compatibility。

## 16. 风险与审核默认选项

本方案推荐默认：独立 3D-Assets-Mujoco 工程；独立 asset_mujoco 环境；GLB/OBJ 输入；static + hull；保持视觉网格；纹理严格检查；不推断质量；原点底部中心；可选 free+显式惯量；CoACD 可选；Blender 非必需；不新增第一阶段 Skill 或服务接口。

主要风险及处置：

- GLB 名义 Y-up 与实际朝向不符：inspect 和预览后显式覆盖。
- 百万面网格过重：预算拒绝，碰撞副本简化，不静默损失显示细节。
- 空腔被凸包封闭：明确近似等级，必要时用户代理碰撞。
- 纹理/PBR 不完全对应：基础颜色保留，支持范围外严格错误或显式降级。
- 生成网格不适合物理积分：静态默认，自由模式使用明确惯量策略。
- 质量/真实尺寸未知：由用户配置，不从形状和 prompt 猜测。
- 环境渲染不可用：编译/物理结果单独保留，full 自动验收退出 7，OSMesa 成功视为有效渲染。
- 视觉 primitive 平面/少顶点：先做任务 3 编译实验，shell 仅候选，不能静默改外观。
- supplied 惯量单位/坐标不明确：明确拒绝，normalized_body/com 不作二次变换。
- watertight 标志掩盖不可信实体：独立 mass_geometry 与拓扑/自交检查，无法证明则失败。

R2 已审核通过，实施任务 1–7，包括 static 与基础 free 刚体。任务 8 已计划的孔洞测试不属新增范围，但须等待 M1 自动闭环通过；关节、流体和材料形变仍在范围外。不得自动 push。

## 17. 技术依据

以下官方资料用于核对格式和接口；本文的工程默认值、预算和验收阈值是本项目设计决策，不是官方保证。

- [MuJoCo XML Reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html)：网格资源、material/texture、geom 与 inertial 的字段约束。
- [MuJoCo Modeling](https://mujoco.readthedocs.io/en/stable/modeling.html)：MJCF 模型组织、坐标与建模方式。
- [MuJoCo Python](https://mujoco.readthedocs.io/en/stable/python.html)：MjModel/MjData、编译、仿真、Renderer 与 viewer 接口。
- [CoACD 官方仓库](https://github.com/SarahWeiii/CoACD)：近似凸分解实现和参数说明。

## 18. 方案自检（文档层，不代表实现通过）

- 不改第一阶段代码/功能/环境/源资产：第 2、5、13、15 节。
- 单文件转换与串联调用可分别运行：第 3、11 节。
- XML 配套资源、相对路径与迁移：第 7、10、13 节。
- 尺度、坐标、视觉、碰撞和质量分别定义：第 6–9 节。
- 运行证据分层而非仅检查文件存在：第 13–14 节。
- 已给出错误、失败恢复和预算：第 5、8、11 节。
- 只提交方案供审核，不开始实现：第 1、15–16 节。

本轮只读检查、逐项审核对照、实测依赖及失败处理详见 [修订报告](PHASE2_MUJOCO_REVISION_REPORT.md)。该报告不是另一份权威设计，实施依据始终是本文件及迁移后的唯一版本。
