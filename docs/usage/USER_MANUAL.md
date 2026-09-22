# 使用手册：GLB/OBJ 与生成服务到 MuJoCo XML

更新：2026-09-22。对应已实现代码 `6310ea0`，交接提交 `38b1465`。
本文是当前使用总入口；总体设计以 [PHASE2_MUJOCO_DESIGN.md](../design/PHASE2_MUJOCO_DESIGN.md) 为准，8A/9 增补见 [TASK8A_9_DESIGN.md](../design/TASK8A_9_DESIGN.md)。历史报告不是当前命令参考。

## 1. 当前完成了什么

| 能力 | 当前实现与边界 |
|---|---|
| GLB/OBJ → XML 资源包 | 输入检查、场景节点展开、方向/尺度归一化、基础颜色/纹理/法线导出 |
| 静态/自由物体 | static；free 需显式质量及 box_approx 或 supplied 惯量 |
| 碰撞 | 原始视觉顶点 hull、无碰撞 VISUAL_ONLY、8A supplied 闭合凸代理 |
| 8A 多部件代理 | 凸性/闭合性/预算检查、多 geom、指定部件验收；不是自动凸分解 |
| 自动验证 | compile / physics / full；真实 MuJoCo 编译、forward、指定接触工况、渲染 |
| 发布与证据 | 请求等级满足才原子发布；失败留 staging；分层哈希、迁移检查、人工外观审核 |
| 工程接触配置 | 默认 preserve；engineering_static_v1 仅 static+hull 显式可选，不能推广成任意宿主安全结论 |
| 任务 9 串联 | 文本/图片/纹理 HTTP 请求 → 已有转换器；一次 POST、1800 秒超时、失败可恢复 |
| 尚未实现 | CoACD、复杂质量积分/watertight、孔洞专项、任意宿主自动集成、多机服务 |

8A 和任务 9 的软件实现已完成，**真实 Hunyuan3D 生成串联、用户真实代理及真实宿主集成尚未实测**。已有回归是模拟 HTTP + 真实 MuJoCo，不能替代真实 GPU 生成证据。

## 2. 工程与环境

两个阶段严格独立：

```text
3D-Assets-Agent（hunyuan3d 环境，已有 HTTP 服务）
        ↓ job_id / file / type / metadata（服务端本地文件路径）
asset_mujoco.chain（第二阶段环境，共享本机文件系统）
        ↓ 只读 GLB/OBJ
asset_mujoco.pipeline → 唯一 XML 资源包 + 分层验证证据
```

仓库：`/home/mcl/workspace/3D-Assets-Mujoco`；remote：`https://github.com/gungnir33/3D-Assets-Mujoco.git`。
不 import 第一阶段 Python 包，不加载 CUDA 模型，不修改第一阶段环境、权重或既有 job。

### 本机使用已验证环境

```bash
conda activate asset_mujoco_m1_1_rebuild_8a9_20260921_5Ibcv05j
cd /home/mcl/workspace/3D-Assets-Mujoco
python -c "import sys, asset_mujoco; print(sys.executable); print(asset_mujoco.__file__)"
python -m asset_mujoco.cli --help
python -m asset_mujoco.chain --help
```

解释器应在上述独立环境，安装模块应位于其 site-packages。本手册使用安装包模式，不需要设置 PYTHONPATH；已有 PYTHONPATH 指向旧源码时先清除该干扰。

### 新机器或新独立环境安装

以下是用户自行执行的安装步骤，不要安装到 hunyuan3d、ACS 或已有宿主环境；环境名已存在时换唯一名称：

```bash
conda create -n asset_mujoco_user python=3.10 -y
conda activate asset_mujoco_user
cd /home/mcl/workspace/3D-Assets-Mujoco
python -m pip install -r requirements.lock.txt
python -m pip install --no-deps --no-build-isolation .
python -m pip check
```

当前锁定 Python 3.10 系列、MuJoCo 3.4.0、trimesh 4.7.4。修改源码后需重新安装项目，再确认导入位置；不随意升级依赖。

`config/default.yaml` 是约定记录，**当前 CLI 没有自动读取它的配置加载器**；编辑它不会自动改变运行行为。运行参数以 CLI / ConversionRequest 为准；串联接受独立的 JSON 转换配置。

## 3. 已有 GLB/OBJ 如何转 XML

以下 /absolute 路径是占位，需替换；命令本身会执行转换。

### 3.1 先检查输入

```bash
python -m asset_mujoco.cli inspect /absolute/model.glb
```

inspect 检查原始格式特性与资源信息，不表示编译、物理或外观已通过。输入支持 GLB/OBJ，不直接支持 FBX、USDZ 或 XML 反向转换。OBJ 的 MTL/贴图必须位于输入文件父目录内（可用合法子目录），禁止 ../ 越界和符号链接越界。材质缺失不能静默输出灰模成功。

### 3.2 最小编译包

初次检查方向、尺寸和材质时可显式选择 compile：

```bash
python -m asset_mujoco.cli convert /absolute/model.glb \
  --output ./outputs --name my_asset \
  --source-up y --yaw-deg 0 --scale 1 \
  --body-mode static --collision-mode hull --validation-level compile
```

成功 stdout JSON 的 package 是实际唯一目录，如 outputs/my_asset_<id>。
compile 只证明当前转换器版本可以编译，不是物理通过，也不生成 full 等级的四张预览。

### 3.3 请求完整自动验证

```bash
python -m asset_mujoco.cli convert /absolute/model.glb \
  --output ./outputs --name my_asset \
  --source-up y --yaw-deg 0 --scale 1 \
  --body-mode static --collision-mode hull \
  --contact-profile preserve --validation-level full
```

正常资产默认 static+hull+preserve+full。full 会执行物理和渲染，可能因真实穿透超限失败；工具不降低阈值、不自动换配置或降级。失败目录为 .staging-*，不得当成成功发布包。

OBJ 示例：

```bash
python -m asset_mujoco.cli convert /absolute/model.obj \
  --output ./outputs --source-up z --scale 0.001 --validation-level compile
```

0.001 仅适用于你已知该 OBJ 坐标以毫米表示的情况；OBJ 必须显式声明 up-axis 和 scale 或 target-size-m。

### 3.4 方向与尺寸

变换顺序：`T_origin × S_scale × R_yaw × R_axis × T_node_world`。
先展开节点世界变换，再转到 Z-up、绕 Z 执行 yaw、缩放，最后将 XY 包围盒中心及最低 Z 置于 body 原点。

- GLB 未指定 source-up 时按 y；实际源方向不同需显式指定。
- target-size-m 是**最终 X/Y/Z**，不会自动排序成长宽高；先用 yaw 修正朝向。
- scale 与 target-size-m 互斥。
- uniform：单一比例 `dot(current_size,target_size)/dot(current_size,current_size)`；各轴误差限 `0.02*target+1e-7 m`。
- fit_axes：逐轴缩放，会改变形状，必须主动选择；不能用它掩盖错误朝向。
- 平面允许某轴尺寸为 0，但不制造厚度，不保证任意平面子网格能编译。
- 用户倍率或声明尺寸不等于测量证明，physical_scale_verified 仍为 false。

例如目标尺寸（仅作为已知尺寸示例）：

```bash
python -m asset_mujoco.cli convert /absolute/barrier.glb \
  --output ./outputs --source-up y --yaw-deg 90 \
  --target-size-m 1.25 0.13 0.65 --scale-mode uniform --validation-level compile
```

若模型三轴比例不匹配，uniform 会拒绝；不要为了成功而盲目改成 fit_axes。

### 3.5 自由物体与惯量

```bash
python -m asset_mujoco.cli convert /absolute/model.glb \
  --output ./outputs --source-up y --scale 1 \
  --body-mode free --mass 2 --inertia-mode box_approx --validation-level full
```

box_approx 用最终包围盒估算均匀长方体惯量，不代表真实质量分布。碰撞代理不参与质量积分。

已有可靠惯量时使用 `--inertia-mode supplied --supplied-inertia /absolute/inertia.json`。完整数据结构示例（仅适用于对应 1 m 立方体、质量 2 kg 的均匀盒体，不能直接套用任意资产）：

```json
{
  "frame": "normalized_body",
  "reference": "com",
  "com_unit": "m",
  "inertia_unit": "kg*m^2",
  "com": [0, 0, 0.5],
  "tensor": [[0.3333333333333333, 0, 0], [0, 0.3333333333333333, 0], [0, 0, 0.3333333333333333]],
  "mass_kg": 2,
  "final_size_m": [1, 1, 1]
}
```

数据必须对应最终 body 坐标系、最终尺寸和指定质量，并且关于 COM；不会再次做轴/yaw/尺度变换。不接受源坐标系猜测，检查有限性、对称性、正定性和主惯量三角不等式。

## 4. 碰撞选择与任务 8A

| collision-mode | 用途 | 限制 |
|---|---|---|
| hull（默认） | 对规范化后的原始视觉顶点取单凸包 | 会填平孔洞；未验证孔道可通过 |
| none | 仅视觉 XML | 仅 static + 显式 compile；physics=not_applicable |
| supplied | 使用用户提供的一个或多个闭合凸代理部件 | 不自动修复、配准或凸分解 |

纯视觉命令：

```bash
python -m asset_mujoco.cli convert /absolute/model.glb \
  --output ./outputs --collision-mode none --validation-level compile
```

supplied 先检查编译与部件映射：

```bash
python -m asset_mujoco.cli convert /absolute/model.glb \
  --output ./outputs --source-up y --scale 1 \
  --collision-mode supplied --collision-proxy /absolute/proxy.glb \
  --validation-level compile
```

然后在新包中验收明确部件：

```bash
python -m asset_mujoco.cli convert /absolute/model.glb \
  --output ./outputs --source-up y --scale 1 \
  --collision-mode supplied --collision-proxy /absolute/proxy.glb \
  --validation-collision-part 0 --validation-level full
```

代理可以是 GLB/OBJ，必须与视觉资产共享原始世界坐标和单位；自身节点先展开，再用视觉确定的同一全局矩阵。禁止独立归一化后再传入。映射在 conversion_manifest.json 的 collision_proxy.parts。

最多 32 部件、50,000 总三角面、每部件 10,000 顶点；只在代理实例内精确焊接同位置顶点。开放、非凸、重复/非流形、反向或数值不确定的部件拒绝。

physics/full 必须显式给零起始部件索引。static 必需对为所选部件与 probe，free 为所选部件与 ground；其他部件碰撞不能代替。探针不自动瞄准代理。结论为 SELECTED_COLLISION_PART_ONLY，不是整件资产所有部件或孔洞都达标。engineering_static_v1 不支持 supplied。详见 [代理手册](COLLISION_PROXY.md)。

## 5. 一个命令：描述/图片 → XML

首次使用请先读 [串联详解](CHAIN.md)。需要第一阶段服务已由用户启动：

```bash
/home/mcl/workspace/3D-Assets-Agent/scripts/start_server.sh
```

该服务使用自己的 hunyuan3d 环境；不要在第二阶段安装或加载生成模型。chain 不会自行启动后台服务。

在工作目录保存 convert.json：

```json
{
  "name": "generated_asset",
  "source_up": "y",
  "yaw_deg": 0,
  "scale": 1,
  "body_mode": "static",
  "collision_mode": "hull",
  "contact_profile": "preserve",
  "validation_level": "full"
}
```

先进行零网络、零生成、零输出目录的预检：

```bash
python -m asset_mujoco.chain --prompt "A red road barrier" \
  --conversion-config convert.json --output ./outputs --dry-run
```

正式命令会发起一次真实 GPU 生成请求，需服务和模型已就绪：

```bash
# 描述 → GLB → XML
python -m asset_mujoco.chain --prompt "A red road barrier" \
  --conversion-config convert.json --output ./outputs

# 图片 → GLB → XML
python -m asset_mujoco.chain --image /absolute/input.png \
  --conversion-config convert.json --output ./outputs

# 已有 mesh + 条件图 → 带纹理模型 → XML
python -m asset_mujoco.chain --mesh /absolute/model.glb \
  --condition-image /absolute/condition.png \
  --conversion-config convert.json --output ./outputs
```

默认生成参数：texture=true、seed=12345、face_count=40000、shape_steps=50、format=glb。可用 --seed、--face-count、--shape-steps、--no-texture、--format obj。文本最多 1000 字符。命令入口另有 `python scripts/chain.py`，共用同一实现。

地址默认 http://127.0.0.1:8080；仅接受显式端口的 HTTP loopback（127.0.0.1 / localhost / [::1]），不跟随重定向、不用系统 HTTP 代理。两个阶段必须共享本地文件系统，不能把远程机器的 file 路径当成本地文件。

接口为 /generate/text 的 prompt、/generate/image 的 image、/generate/texture 的 mesh 与 condition_image；成功 file 和 metadata 都是路径，metadata 不是内嵌对象。

每次输出 chain_<id>/，保存 request.json、phase1_response.json、chain_manifest.json、packages/。最终 XML 包路径在 stdout 的 phase2.package；原始生成资产保持第一阶段 job 位置。

### 失败恢复

- health 失败：LOCAL_3D_SERVER_NOT_RUNNING，按提示启动服务。
- 生成 POST 超时/断连或响应不能确认：phase1=unknown，不表示服务器取消任务；先查第一阶段结果，**不要直接重试生成**。
- 第二阶段失败：保留 phase1=passed、源路径/哈希和 recovery_argv/recovery_command。使用返回的恢复命令只重新转换原文件，不再次发生成 POST。
- 不会自动把 full 改 compile，或 preserve 改工程候选。
- --request JSON、相对路径基准及错误详情见 [串联手册](CHAIN.md)。

## 6. 输出包、查看和迁移

| 文件/目录 | 含义 |
|---|---|
| model.xml | 完整无地面资产模型；不是任意宿主可无条件 include 的片段 |
| scene.xml | 独立查看场景，带地面及显示/仿真设置 |
| contact_scene.xml（候选配置） | 显式交付的资产、地面、探针工况，不是用户机器人场景 |
| meshes/、textures/ | 包内相对资源，必须与 XML 一起移动 |
| previews/front.png、side.png、iso.png、collision.png | full 成功时的四张原生渲染 |
| conversion_manifest.json | 来源/依赖哈希、变换、尺寸、材质近似、代理和配置 |
| validation_report.json、evidence_manifest.json | 分层结果、范围投影和证据绑定 |
| physics_native.xml、physics_evidence.json、contact_result_manifest.json | 实际验收夹具及结果；异常时文件可能不齐 |
| benchmark_evidence.json | 非强制受控诊断，不能代替 native |
| appearance_review.json | 用户实际审核后才创建/更新的内容绑定记录 |

以本次实际包文件为准：compile 不产生物理/渲染证据；失败包不保证完整。

只读查询：

```bash
python -m asset_mujoco.cli report /absolute/package
```

用户需要 GUI 时可自行运行（本轮文档更新不启动）：

```bash
python -m mujoco.viewer --mjcf=/absolute/package/scene.xml
```

迁移应复制整个包到新位置，再 report，并在目标解释器调用 MjModel.from_xml_path 和 mj_forward。不能只复制 XML，也不能把相对纹理路径改成旧 staging 的绝对路径。独立编译通过不代表真实宿主兼容；merge_host 仅为自建最小宿主提供受限合并辅助，不是通用 ACS 接入器。

## 7. 如何读“通过”与错误

| 状态 | 正确理解 |
|---|---|
| COMPILE_VALIDATED | 编译层通过；不是物理通过 |
| VISUAL_ONLY | 无碰撞视觉输出；physics=not_applicable |
| SCOPED_PHYSICS_VALIDATED | 报告中指定工况物理通过；人工通常 pending |
| SCOPED_FULLY_VALIDATED | 指定工况检查齐备、渲染通过且外观批准有效；不扩大到整场景/宿主/安全 |
| FAILED / INVALID_EVIDENCE | 验收失败或证据不足/失效，不能沿用旧成功 |
| CONVERTED | 尚无编译通过事实，不是发布成功证明 |

同时读取 contact_profile、validation_scope.required_pairs/conditions/evidence_status、followup_ground、limitations 和 evidence_issues。范围 declared 不是 verified。

Python 转换核心核对磁盘证据后才发布：compile 需编译层；physics 另需 native 与 verified 范围；full 另需渲染。任意证据问题拒绝发布。人工 pending 不阻止自动受限发布，非必需地面失败也不改变既定必需集合，但必须显示。

full 渲染不可用时退出 7、不发布；报告仍可保留独立 physics=passed 与 verified 范围，不能反称 full 请求成功。报告不重新跑仿真，不为被改动的内容补签。

| 退出码 | 主要含义 |
|---|---|
| 0 | 请求的自动层级成功，或只读查询无失败；不等于人工已批准 |
| 2 | 参数/输入问题 |
| 3 | 转换或证据持久化问题 |
| 4 | XML 编译问题 |
| 5 | 物理/渲染内容失败；report 中失败或证据问题 |
| 6 | chain 第一阶段 HTTP/响应/结果未知 |
| 7 | full 所需渲染后端不可用 |

以上为 cli/chain 常用映射；独立 acceptance 使用其验收结果退出规则。

人工审核必须真正查看对应新包预览后执行，不能为提高状态自动批准：

```bash
python -m asset_mujoco.cli review /absolute/package \
  --reviewer YOUR_NAME --decision approved \
  --images previews/front.png previews/side.png previews/iso.png previews/collision.png
```

不接受时使用 rejected。内容/预览改变使旧批准失效；批准仅针对外观，不更改碰撞参数、阈值、地面结果或宿主状态。

## 8. 工程候选与历史证据

preserve 始终默认。engineering_static_v1 是显式双方一致的工程配置，仅 static+hull；不是测得真实材料参数。资产与公开测试接触对象采用 solref=[0.006,1]、solimp=[0.9,0.95,0.001,0.5,2]。仅一侧为 .006、另一侧 .02 的混合接触不是同一工况。

已有 M1.2 报告中：指定企鹅—探针 preserve 约 11.795 mm 失败；候选约 2.377 mm 受限通过；后续 ground 约 8.961 mm 失败且 mandatory_for_physics=false。**这些是历史值，不是本文更新时新跑的结果**。来源见 [发布状态修复报告](../design/M1_2_PUBLICATION_STATE_FIX_REPORT.md)。

appearance_review=pending、host_integration=pending、robot_contact_safety=not_validated、application_force_limit=not_specified，不能改写为整个场景或机器人安全已验证。

独立 acceptance 是固定企鹅基线工况工具：y-up、yaw=180、scale=.5、static+hull+full，即使 --input 指向其他 GLB，也不会自动适配工况。不应把它当成任意请求的通用验收入口。通用用户资产用 convert/report：

```bash
python -m asset_mujoco.acceptance --contact-profile preserve --output ./outputs/acceptance
```

该命令实际重新转换默认原始 GLB；缺输入报告未执行，不用旧 OBJ 代替。contact_diagnostics/profile_diagnostics 是显式实验工具，会创建新实验，不是普通查看命令；不能用诊断通过替代交付验收。

## 9. 代码库模块索引

路径均相对仓库；链接直接指向当前源码。实现采用现有同步转换器与分层证据，不存在独立任务队列或后台服务。

| 代码位置 | 实现职责 |
|---|---|
| [contracts.py](../../src/asset_mujoco/contracts.py) | Pydantic 输入、惯量、范围/地面/验证结果；状态聚合 |
| [inputs.py](../../src/asset_mujoco/inputs.py) | GLB 原始特性检查、OBJ 语义预检、实际资源读取边界及依赖哈希 |
| [asset_decode.py](../../src/asset_mujoco/asset_decode.py) | 共用受限解码；构造网格前检查面索引，保存源法线 |
| [scene.py](../../src/asset_mujoco/scene.py) | 展开实例/节点世界变换，视觉几何与来源记录 |
| [transforms.py](../../src/asset_mujoco/transforms.py) | up-axis/yaw/尺度/body 原点矩阵及最终尺寸 |
| [materials.py](../../src/asset_mujoco/materials.py) | 视觉 OBJ/UV/法线/纹理导出，基础颜色因子仅应用一次 |
| [collision.py](../../src/asset_mujoco/collision.py) | 对全部原始规范化视觉顶点构造 hull |
| [collision_proxy.py](../../src/asset_mujoco/collision_proxy.py) | supplied 实例分量、精确焊接、拓扑/凸性/预算检查、部件导出 |
| [collision_scope.py](../../src/asset_mujoco/collision_scope.py) | 指定部件工况与 geom→mesh→文件映射一致性检查 |
| [inertia.py](../../src/asset_mujoco/inertia.py) | box_approx 与 supplied 惯量验证，不做 watertight 积分 |
| [mjcf.py](../../src/asset_mujoco/mjcf.py) | model/scene、视觉/碰撞分离、显式 free inertial、受限最小宿主合并 |
| [contact_profiles.py](../../src/asset_mujoco/contact_profiles.py) | preserve/engineering 参数声明与公开 contact_scene |
| [pipeline.py](../../src/asset_mujoco/pipeline.py) | staging→转换→编译→验证→核对证据→原子发布；失败留诊断 |
| [validation.py](../../src/asset_mujoco/validation.py) | native 与 benchmark 隔离；逐步状态、warning、指定接触对与穿透检查 |
| [contact_statistics.py](../../src/asset_mujoco/contact_statistics.py) | 接触统计、力/冲量、地面及每代理部件观察 |
| [rendering.py](../../src/asset_mujoco/rendering.py) | 独立子进程后端探测与四视图渲染 |
| [manifest.py](../../src/asset_mujoco/manifest.py) | 分层资源哈希、证据核对/范围投影、只读 report 与外观审核绑定 |
| [cli.py](../../src/asset_mujoco/cli.py) | inspect/convert/report/review，JSON 输出及退出码 |
| [acceptance.py](../../src/asset_mujoco/acceptance.py) | 固定真实 GLB 基线验收和迁移复编译；区别于失败处理回归 |
| [chain_contracts.py](../../src/asset_mujoco/chain_contracts.py) | 生成请求、严格 JSON、路径/转换预检、响应契约 |
| [chain_http.py](../../src/asset_mujoco/chain_http.py) | loopback、health、1800 秒单次 POST、响应边界与错误保留 |
| [chain.py](../../src/asset_mujoco/chain.py) | dry-run、来源保存、转换调用、恢复 argv、包外串联记录 |
| [contact_diagnostics.py](../../src/asset_mujoco/contact_diagnostics.py)、[profile_diagnostics.py](../../src/asset_mujoco/profile_diagnostics.py) | 独立实验副本与诊断，不自动更改正式配置 |
| [scripts/](../../scripts/) | chain 薄入口、环境检查、最小 mesh 编译和渲染探测 |
| [tests/](../../tests/) | 合成/负向/故障注入/真实 MuJoCo/迁移与 HTTP 契约回归 |
| [deployment_manifest.json](../../deployment_manifest.json) | 分阶段环境和历史证据；读取 task8a9_final 获取最新一轮记录 |
| [requirements.lock.txt](../../requirements.lock.txt)、[pyproject.toml](../../pyproject.toml) | 精确依赖与 Python 3.10 项目安装 |

Python 调用复用同一发布门槛：

```python
from pathlib import Path
from asset_mujoco.contracts import ConversionRequest
from asset_mujoco.pipeline import convert

package = convert(ConversionRequest(
    input=Path("/absolute/model.glb"),
    output=Path("/absolute/output-parent"),
    source_up="y", scale=1,
    validation_level="compile",
))
print(package)
```

异常不能当成返回成功目录处理；物理/渲染拒绝发布可通过 ValidationFailed.package 定位诊断，证据写入故障单独为 EvidenceIOError。

## 10. 常见问题与验证记录

| 现象 | 检查方向 |
|---|---|
| 命令没有 chain / supplied 参数 | 实际解释器、导入位置；重新安装本仓库，不修改旧环境 |
| 模型灰色/无贴图 | 源 GLB 基础贴图、OBJ MTL/纹理是否完整；检查 textures 和材质绑定；不是完整 PBR 等价渲染 |
| 方向/比例错误 | source-up、yaw 和最终 XYZ；不要用非均匀缩放掩盖朝向问题 |
| 代理被拒绝 | 共享坐标、闭合/凸性、重复面、部件预算；工具不自动“修好”不可信代理 |
| native 失败而 benchmark 通过 | benchmark 非强制诊断，不能替代交付原配置验收 |
| 修改 XML 后旧通过失效 | 预期保护机制；创建新包重新验证，不手改证据哈希 |
| full 无法渲染 | 检查 EGL/OSMesa；不降级后再声称 full，通过一种真实后端即可 |
| 生成 422/503 | chain 保存 HTTP/业务错误；422 看 detail，503 看业务 code/message；不凭状态码猜测显存原因 |
| 宿主编译冲突 | HOST_COMPILER_CONFLICT 不自动修宿主；需要独立集成方案 |

最新已有完整回归：**298 passed、1 skipped（OSMesa loader），63.59 s；pip check 通过**，来自代码 6310ea0 的 [最终验证记录](../design/TASK8A_9_FINAL_VERIFICATION.md) 与 [原始 pytest 输出](../design/evidence/TASK8A_9_FINAL_PYTEST.txt)，不是本次文档更新重新跑出的数字。

需要自行全量回归时，在独立环境和仓库根目录：

```bash
env -u PYTHONPATH python -B -m pytest -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs
python -m pip check
```

outputs 当前按用户要求可被 Git 跟踪；生成请求、来源路径、贴图和图片可能敏感，提交前逐项审查。工具不自动提交或推送，也不会批准人工外观或修改历史资源包。

本次文档核对：读取当前源码与安装包 cli/chain 的 --help，检查 README 与使用文档的 58 个本地链接和 JSON 示例；使用本文转换配置运行文本 --dry-run，退出 0，phase1/phase2 均 not_run，未创建输出目录。未发送生成请求、未执行实际转换或重跑完整 pytest/仿真/渲染。
