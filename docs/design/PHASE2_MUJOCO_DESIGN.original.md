# 第二阶段：3D 资产到 MuJoCo MJCF 独立转换工程设计与实施计划

状态：待用户审核。本文不代表已经实现或验证第二阶段功能。

本文存放在 `/home/mcl/models/hunyuan3d/tasks/`，避免为了记录方案而改动第一阶段仓库。批准后在独立工程内保存正式设计副本。本次仅编写方案，不创建运行环境、不安装依赖、不转换模型、不提交或推送第一阶段仓库。

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

建议第二阶段根目录：`/home/mcl/workspace/3D-Assets-MuJoCo`。

建议独立 Conda 环境：`asset_mujoco`，Python 3.10。独立本地 Git 仓库；未指定远端，因此本方案不创建 GitHub 仓库、不借用第一阶段 origin、不擅自推送。

第一阶段唯一必需接口是资产文件路径。可选 metadata 仅提供来源信息，不是核心转换依赖，不从其 prompt 推断真实尺寸或质量。

串联器只发 HTTP 请求、读取响应的 file/metadata，再调用第二阶段 CLI；不 import 第一阶段 Python 包，不直连其模型对象，不执行其 CUDA 初始化。

独立性证明：复制输入文件及依赖到测试目录，使第一阶段服务不可达、其 Python 包不在环境内，转换仍成功。对第一阶段仓库提交、工作区状态和源资产 SHA256 做前后对比。

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
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                    可视 OBJ + PNG               简化碰撞副本
                         │                             ↓
                         │                    凸包 / 凸分解 / 代理
                         └──────────────┬──────────────┘
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

用户提供的 Blender 可作为后续可选烘焙工具：`/home/mcl/blender-5.2.1-linux-x64/blender`。基础转换不得依赖其安装或用户偏好设置。

## 4. 工程结构与模块接口

```text
3D-Assets-MuJoCo/
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
class ConversionRequest:
    input_path: Path
    output_dir: Path
    name: str
    source_up: str           # y / z，OBJ 必须显式指定
    scale: float            # 严格大于 0
    target_size_m: tuple[float, float, float] | None
    scale_mode: str         # uniform / fit_axes
    body_mode: str          # static / free
    collision_mode: str     # hull / decompose / supplied / none
    mass_kg: float | None
    inertia_mode: str       # supplied / box_approx / watertight
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
2. 任何几何顶点须 finite；三角面索引合法；无空几何或零尺寸模型。
3. GLB 外部 URI、OBJ MTL 和纹理路径只能位于显式输入资源根目录内；禁止网络访问与目录穿越；符号链接同样检查最终路径。
4. OBJ 缺少必需 MTL/纹理时，默认 texture_policy=strict 报错；显式 allow_flat 才能降级，并记录警告。
5. 稀有扩展如 Draco、KTX2、骨骼、morph target 首版报 UNSUPPORTED_ASSET_FEATURE，不静默丢弃。

源文件只读。记录输入 GLB 或 OBJ+MTL+纹理的全部哈希；在输出工作区建立自己的资源副本。现有输出目录非空则拒绝，失败不会覆盖成功资源包。工作目录使用唯一 staging，验证结束后同文件系统原子重命名发布。

## 6. 坐标、尺度、原点

MuJoCo 工程统一使用米、千克、秒；世界 Z 向上。GLB 按 glTF 约定默认 Y-up，但生成资产可能不遵守语义，允许 source_up=z 显式覆盖；OBJ 没有可靠单位和 up-axis，必须提供参数。

先展开并应用 Scene 节点层级变换，再进行轴变换、尺度和原点变换：

```text
v_output = T_origin × S_scale × R_axis × T_node_world × v_local
```

Y-up → Z-up 采用绕 X 轴正向 90°，统一实现并通过已知非对称模型验证。负行列式镜像变换要翻转面朝向，法线使用逆转置；所有可视、碰撞、质心和惯量一致转换。

默认原点为规范化后包围盒底部中心，body 放在地面时最低点为 z=0。可选 centroid 和 source，记录转换矩阵、输入和输出 AABB。禁止对材质分块分别居中，禁止再次手工补偿 MuJoCo 编译器内部 mesh 重心变换。

尺度策略：

- 未指定目标尺寸：GLB 按标准数值单位处理，scale 默认 1；报告 physical_scale_verified=false，提示第一阶段生成值未必为真实尺寸。
- `--scale`：统一缩放因子，可用于 OBJ 毫米到米的 0.001。
- `--target-size-m L W H --scale-mode uniform`：要求三个轴同比例，误差超过 2% 则报错，防止伪造精确尺寸。
- `fit_axes`：显式允许非均匀变形以达到三个目标尺寸，记录形状变形，不作为默认。
- scale 与 target_size 二选一，目标尺寸均须正数。

水马示例尺寸为 1.25×0.13×0.65 m，但模型长轴对应哪个方向必须经预览确认；不会从提示词自动推断。

## 7. 视觉、材质和贴图

输入为 Scene 时保留所有可见节点及实例变换；按 primitive/material 分别导出 OBJ，保留 UV seam 的独立索引和正确法线。禁止直接合并全部网格导致贴图丢失。

材质支持分层：

| 输入 | 输出策略 |
|---|---|
| 无材质、无颜色 | 明确默认灰色 RGBA |
| baseColorFactor | MJCF material/geom rgba |
| baseColorTexture + UV | PNG + OBJ UV + XML texture/material 引用 |
| 多材质 | 分别导出 mesh/geom，各自绑定 material |
| vertex color | 首版严格报错，或显式允许均色近似并报告损失 |
| metallic/roughness/normal/emissive 等 | 记录不支持的通道，基础外观模式近似；strict PBR 模式报错 |

不依赖 OBJ 的 MTL 被 MuJoCo 自动解析；XML 显式绑定纹理和材质。颜色因子与纹理相乘只能做一次，禁止重复变暗。首版核心只保证不透明颜色贴图，alpha blend/mask 不保证透明排序，默认报不支持；用户选择 flatten 时使用指定背景色并记录。

UV 垂直方向、repeat、非单位纹理变换、颜色空间通过四色 UV 校验图测试；不能依据一次观察随意翻转 PNG。基础模式下 MuJoCo 渲染效果与 Blender 不会像素一致。

可视网格默认不减面，以保留第一阶段细节与 UV；超过预算明确报错。仅对独立碰撞副本清理/简化，绝不影响源可视网格。

## 8. 碰撞体策略

显示 geom 设 `contype=0 conaffinity=0 mass=0 group=2`；碰撞 geom 单独定义接触位与 group=3，常规 viewer 隐藏 group 3，碰撞调试时切换。碰撞体与可视体共用一个 body。

默认 hull：整体凸包，速度快，但会封闭水马把手和凹槽，报告 collision_fidelity=convex_approximation。不得声称孔洞可穿过。

decompose：使用 CoACD 在清理后的碰撞副本上作近似凸分解。提议预算：碰撞输入≤50,000 faces，最多 32 个凸体，随机 seed=12345，子进程超时 180 秒。超时或超预算默认失败，不偷偷换成单凸包；用户显式 `fallback=hull` 时允许降级并记录。

supplied：用户指定一个独立代理碰撞文件，每个 component 必须验证为闭合凸体；适合可靠保留把手通道的复合几何。代理声明 source 坐标系，应用与视觉一致的规范化矩阵。

none：仅静态视觉模式允许，输出 VISUAL_ONLY；free 模式默认禁止。

孔洞保持是单独质量目标。对标准带孔测试件放置探针验证穿过孔洞不接触、碰到边框有接触；凸分解不是孔洞准确性的保证。失败须标注 approximation 或要求人工代理。

## 9. 质量、质心、惯量和接触参数

static 不创建 joint，不要求物理质量。free 创建一个 freejoint，并要求 mass_kg>0；不能从红色塑料外观推测质量。

free 的惯量策略必须显式选择：

- supplied：用户提供 COM 与完整对称惯量张量，检查有限、正定及主惯量三角不等式，按坐标变换正确旋转。
- box_approx：以规范化包围盒和明确质量计算，Ixx=m(W²+H²)/12，其余循环；质心取盒中心并明确 approximate=true。
- watertight：仅对确认闭合、定向一致且正体积网格使用均匀密度积分，再缩放到指定质量；空腔未建模、开放网格或非流形时失败。

不对可能重叠的 CoACD 凸体简单累加惯量，以免重复体积。显式 inertial 是唯一质量来源，显示/碰撞 geom 不重复贡献质量。

接触默认采用 MuJoCo 标准参数，配置中显式列出实际解析值；可覆盖摩擦三个分量并验证非负。不给用户宣称“真实 PE 摩擦系数”。time step=0.002 s、gravity=0 0 -9.81 为测试场景提议值，不强制覆盖用户已有场景。

## 10. 输出资源包与 XML

```text
outputs/<name>_<short-id>/
├── model.xml                  # 单资产独立可编译，无全局地面/灯光
├── scene.xml                  # 带地面、灯光、相机的演示场景
├── meshes/visual_000.obj
├── meshes/collision_000.obj
├── textures/basecolor_000.png
├── conversion_manifest.json
├── validation_report.json
├── conversion.log
└── previews/{front.png,side.png,iso.png,collision.png}
```

model.xml 和 scene.xml 都是完整 MJCF 文档；由同一个中间结构生成 asset/body，scene 额外添加演示设施，首版避免跨场景 include 路径和命名陷阱。所有 mesh/texture 路径相对 XML 所在包目录；在不同工作目录加载仍成功。资源命名加入资产前缀防冲突。

model.xml 为 static/free 中用户选定模式，scene 不擅自改变物理模型，仅 free 演示时抬高整体放置位置供跌落测试。scene 中 camera 与 ground 尺寸按资产包围盒生成。

XML 使用 ElementTree 构建，禁止字符串拼接用户名称。显式指定 angle=radian、autolimits=true；自由刚体具有合法 inertial，碰撞 geom 不透明度由调试 viewer 控制。

导入现有复杂 MuJoCo 场景首版提供 asset/body 合并说明，不能把带 ground 的 scene.xml 直接无条件 include。自动多物体组合列入后续范围。

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

退出码：0 成功、2 参数/输入错误、3 资源转换失败、4 MJCF 编译失败、5 仿真/质量验收失败、6 第一阶段连接/请求失败、7 渲染不可用且请求完整验收。

串联请求例子：

```bash
conda run -n asset_mujoco python scripts/chain.py \
  --request /absolute/phase1-request.json \
  --conversion-config /absolute/phase2-config.yaml \
  --output /absolute/mujoco-output
```

phase1-request.json 明确 endpoint=text/image/texture 及原有 payload，串联器不添加第一阶段不存在的字段。服务由用户按第一阶段原流程启动；chain 不 daemonize。HTTP timeout=1800 s，失败时读取并显示服务的 JSON details，保留 422 长度错误、503 OOM 等原因。不自动重试生成请求，避免产生重复任务。

第一阶段成功后保留原 job/file/metadata，第二阶段失败仍输出 phase1 成功结果。恢复时用 `convert --input <原结果>`，无需再次生成。两阶段日志和 manifest 分开存放，chain_manifest 仅引用二者。

## 12. 版本、依赖与资源管理

独立环境候选依赖：Python 3.10、numpy、trimesh、Pillow、pydantic、PyYAML、mujoco、coacd、httpx、pytest。无需 Torch、HunyuanDiT、Hunyuan3D 或 CUDA 推理包。

不在方案中捏造“已验证版本”。实施任务 1 在独立环境安装相互兼容的确定版本并生成精确 lock；MuJoCo/CoACD 版本和许可证纳入 deployment manifest。若可用版本要求更高 Python，则先报告独立环境版本调整，不触碰 hunyuan3d。

转换默认 CPU；渲染通过 MuJoCo 官方渲染接口，依次验证 EGL 或 OSMesa，交互 viewer 使用 GLFW。渲染失败不安装/修改系统驱动；输出明确渲染状态。Blender 适配器作为可选 extra，按版本记录，不参与核心依赖。

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

仿真门槛：0.002 s 步长、1000 steps；每步检查 qpos/qvel/能量 finite、MuJoCo warning 计数、接触数量。自由落体箱体应触地后不持续穿透；测试夹具最大允许穿透为 min(0.005 m, 高度的 2%)，最终速度阈值针对稳定箱体测试，不强求任意物体都在两秒内静止。静态物体用动态探针验证接触。

视觉门槛：至少 front/side/iso 三张 MuJoCo 原生渲染图和碰撞叠加图。有纹理资产检查编译后 texture/material 引用及像素非单色；非空图不能单独证明外观正确，人工复核形状和 UV。

状态分级：CONVERTED、COMPILE_VALIDATED、PHYSICS_VALIDATED、FULLY_VALIDATED。渲染缺失或只能视觉模式时不能声明完整物理验收；无 GPU 渲染环境时编译仿真仍可测试，但应输出 RENDER_VALIDATION_PENDING。

原有三份真实输入作为只读 E2E：

```text
/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210330_6c804545/model.glb
/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210532_fe231a7e/model.glb
/home/mcl/workspace/3D-Assets-Agent/assets/20260909_210805_9dfdcdd0/model.glb
```

不把这些真实资产提交到第二阶段 Git；测试中通过显式 fixture 路径引用，仓库仅保存程序生成的小型合成 fixture。

## 14. manifest 和可追溯性

conversion_manifest 至少包含：schema_version、转换器 commit、依赖版本、源路径与各资源 SHA256、可选第一阶段 job 引用、完整已解析参数、输入/输出 AABB、轴变换矩阵、尺度、原点、材质映射、近似/丢弃通道、可视/碰撞面数、凸体数、质量惯量与来源、seed、每阶段耗时、输出文件哈希。

validation_report 包含编译成功/失败、MuJoCo 版本、body/joint/geom/mesh/material/texture 数量、仿真步数、警告、物理测试结果、渲染后端和图片路径。峰值 CPU 内存可采样记录；不伪称精确 GPU 峰值。

输入哈希和配置相同不承诺跨平台二进制一致，但要求固定版本+seed 下重复转换的包围盒、碰撞体数量与数值结果在约定容差内。清单记录能重现结果的实际配置，而不是仅保存 CLI 原字符串。

## 15. 分阶段实施计划与审核点

本节仅安排实施，不在本轮执行。每项完成后先验证、再独立提交到第二阶段本地仓库。第一阶段没有任何修改项。

### 任务 1：独立工程与只读边界

新增 pyproject.toml、contracts.py、cli.py、check_environment.py、.gitignore 和 tests/unit/test_contracts.py。

- [ ] 固定独立目录/环境并记录第一阶段 Git 状态与源资产哈希。
- [ ] 定义请求/结果/错误结构，测试负质量、非法轴向、输入输出重叠被拒绝。
- [ ] 验证仅在 asset_mujoco 中安装依赖，生成 lock 和环境清单。
- [ ] `pytest tests/unit/test_contracts.py -q` 通过，提交 chore: initialize isolated mujoco converter。

### 任务 2：输入解析、Scene 与尺度

新增 inputs.py、scene.py、transforms.py 和 tests/unit/test_scene_transform.py。

- [ ] 写嵌套变换、多材质节点、负尺度和资源穿越 fixture。
- [ ] 实现只读加载与依赖快照，遍历实例，保留 primitive/material 对应关系。
- [ ] 验证矩阵顺序、米制缩放和底部中心，三轴尺寸达到设定容差。
- [ ] `pytest tests/unit/test_scene_transform.py -q` 通过，提交 feat: add scene normalization。

### 任务 3：可视资源和材质

新增 materials.py 和 tests/integration/test_visual_assets.py。

- [ ] 用四色纹理箱体验证 UV、颜色因子与外部 PNG，缺纹理时严格失败。
- [ ] 导出每个材质对应的 OBJ/PNG，报告不支持通道。
- [ ] 用无材质模型、多材质模型验证材质数量及引用正确。
- [ ] `pytest tests/integration/test_visual_assets.py -q` 通过，提交 feat: preserve visual assets and textures。

### 任务 4：碰撞和惯量

新增 collision.py、inertia.py、tests/unit/test_inertia.py、tests/integration/test_collision.py。

- [ ] 箱体质量 12、尺寸 1.25/0.13/0.65 的解析惯量与函数输出比较。
- [ ] 实现 hull、带预算 CoACD 子进程和 supplied，测试超时可终止子进程且不覆盖输出。
- [ ] 开放网格 watertight 模式失败；重叠凸体不重复累加质量。
- [ ] 测试凸体合法性、孔洞探针和显式 fallback 报告。
- [ ] 相关测试通过，提交 feat: add collision and inertia policies。

### 任务 5：MJCF 输出与可移植包

新增 mjcf.py、pipeline.py、manifest.py、tests/integration/test_mjcf_compile.py。

- [ ] 实现相对资源引用、static/free XML、独立 scene 与 staging 发布。
- [ ] 验证 static 无 freejoint、free 有合法 inertial，材质绑定正确。
- [ ] 对两个 XML 执行 MjModel.from_xml_path、mj_forward；复制目录后二次加载。
- [ ] 非空目标目录明确失败，失败包保留诊断但不宣称发布。
- [ ] 测试通过，提交 feat: export portable mjcf packages。

### 任务 6：仿真、渲染和查看

新增 validation.py、rendering.py、view_asset.py 和 tests/e2e/test_physics_render.py。

- [ ] 实现 1000 步仿真检查、静态探针、落体 fixture 与 warning 采集。
- [ ] 实现 MuJoCo Renderer 三视图、碰撞开关及 viewer。
- [ ] 无渲染上下文时输出准确状态和退出码，不把空白图算通过。
- [ ] 测试通过，提交 test: add mujoco simulation and render validation。

### 任务 7：外部串联脚本

新增 scripts/chain.py 和 tests/integration/test_chain.py。

- [ ] mock 第一阶段 200/422/503/连接失败/超时，验证错误 JSON 完整保留。
- [ ] 检查第二阶段失败仍返回已生成 file，可独立恢复。
- [ ] 证明无第一阶段 import、无自动启动服务、无 GPU 依赖。
- [ ] 测试通过，提交 feat: chain generation and conversion externally。

### 任务 8：真实资产验收与文档

新增 docs/usage、docs/development、deployment_manifest.json 和 tests/e2e/test_existing_assets.py。

- [ ] 对三份真实 GLB 分别输出独立包，并验证纹理模型、两份几何模型。
- [ ] 对 static/free 和凸包/分解策略分别执行受控测试，明确近似结果。
- [ ] 对比第一阶段仓库和源文件前后哈希，冻结边界通过。
- [ ] 更新完整运行命令、故障表、格式限制、质量惯量说明与许可证。
- [ ] 全部单元/集成/真实 E2E 通过后提交 docs: document validated mujoco conversion。

## 16. 风险与审核默认选项

本方案推荐默认：独立 3D-Assets-MuJoCo 工程；独立 asset_mujoco 环境；GLB/OBJ 输入；static + hull；保持视觉网格；纹理严格检查；不推断质量；原点底部中心；可选 free+显式惯量；CoACD 可选；Blender 非必需；不新增第一阶段 Skill 或服务接口。

主要风险及处置：

- GLB 名义 Y-up 与实际朝向不符：inspect 和预览后显式覆盖。
- 百万面网格过重：预算拒绝，碰撞副本简化，不静默损失显示细节。
- 空腔被凸包封闭：明确近似等级，必要时用户代理碰撞。
- 纹理/PBR 不完全对应：基础颜色保留，支持范围外严格错误或显式降级。
- 生成网格不适合物理积分：静态默认，自由模式使用明确惯量策略。
- 质量/真实尺寸未知：由用户配置，不从形状和 prompt 猜测。
- 环境渲染不可用：编译/物理结果单独报告，渲染门槛保留。

审核同意本方案后再开始任务 1。若需要“路障为静态障碍物”以外的物理行为、精确孔洞接触或可运动关节，应在实施前修改对应范围。

## 17. 技术依据

以下官方资料用于核对格式和接口；本文的工程默认值、预算和验收阈值是本项目设计决策，不是官方保证。

- [MuJoCo XML Reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html)：网格资源、material/texture、geom 与 inertial 的字段约束。
- [MuJoCo Modeling](https://mujoco.readthedocs.io/en/stable/modeling.html)：MJCF 模型组织、坐标与建模方式。
- [MuJoCo Python](https://mujoco.readthedocs.io/en/stable/python.html)：MjModel/MjData、编译、仿真、Renderer 与 viewer 接口。
- [CoACD 官方仓库](https://github.com/SarahWeiii/CoACD)：近似凸分解实现和参数说明。

## 18. 方案自检

- 不改第一阶段代码/功能/环境/源资产：第 2、5、13、15 节。
- 单文件转换与串联调用可分别运行：第 3、11 节。
- XML 配套资源、相对路径与迁移：第 7、10、13 节。
- 尺度、坐标、视觉、碰撞和质量分别定义：第 6–9 节。
- 运行证据分层而非仅检查文件存在：第 13–14 节。
- 已给出错误、失败恢复和预算：第 5、8、11 节。
- 只提交方案供审核，不开始实现：第 1、15–16 节。
