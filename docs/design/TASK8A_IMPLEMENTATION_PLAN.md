# Task 8A Collision Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将用户提供的一个或多个闭合凸碰撞部件接入现有转换器，并使实际验收只声明明确选定的接触范围。

**Architecture:** 共用受限输入解码，代理仅使用视觉决定的全局矩阵；增加碰撞资源列表和单一范围解析器，保留旧 hull/none 路径。复用现有 compile/native/render/发布门槛与证据系统。

**Tech Stack:** Python 3.10、MuJoCo 3.4.0、trimesh 4.7.4、numpy 2.2.6、scipy 1.15.3、pydantic 2.11.7、pytest 8.4.1；无新运行时依赖。

**Spec:** [TASK8A_9_DESIGN.md](TASK8A_9_DESIGN.md) 第 1–4、7 节（用户已确认）；[PHASE2_MUJOCO_DESIGN.md](PHASE2_MUJOCO_DESIGN.md) 为总体权威设计。

状态：已获用户确认并按方式 1 执行；以下保留原规划步骤，实际提交/测试及边界见 [实施报告](TASK8A_IMPLEMENTATION_REPORT.md)。规划起点 HEAD `5854e8b7e9062affe6ac23c2e2abb2ec36672d06`，实际执行起点为后续计划提交 b0419be，不回退。

## Global Constraints

- 工程 `/home/mcl/workspace/3D-Assets-Mujoco`，origin `https://github.com/gungnir33/3D-Assets-Mujoco.git`；不 reset、clean、force push 或自动 push。
- 不修改第一阶段、现有环境、宿主、驱动、原始资产、历史输出或旧审核记录；保留原有未跟踪审核文件。
- 新建唯一 `asset_mujoco_m1_1_rebuild_8a9_<id>` 环境，不覆盖原环境；Python 3.10，按 requirements.lock.txt 安装，不升级锁定依赖。任务 9 复用该环境。
- preserve/full 仍是默认；engineering_static_v1 仍仅 static+hull；不改接触参数、探针工况、dt、步数、穿透阈值或必需地面集合。
- 仅 supplied 碰撞代理；不实现 CoACD、自动代理、mass_geometry、watertight、孔洞专项。supplied 惯量含义不变。
- 凸部件最多 32，总面数不超过 50,000，每部件顶点不超过 10,000；拒绝超限，不简化。
- 代理与视觉共源世界坐标/单位；仅代理实例副本内精确重合焊接，容差 0；G 仅由视觉计算，法线/UV 等视觉产物不变。
- 证据、渲染、人工审核与宿主状态仍独立；真实代理未提供时只声明合成代理验证，hole_validation=not_tested。

## Review Focus

1. 多节点实例含镜像和非均匀尺度：代理误做第二次居中会错位；Task A1 用已知坐标逐点检查。
2. 连通组件拆分器默认丢弃开放片：必须整份代理失败，不能只留下闭合部分；Task A1 mixed-valid-invalid 用例。
3. 代理部件被修改但不是选定目标：仍属于交付碰撞资源，旧 compile/physics 必须失效；Task A3 篡改非目标资源测试。
4. 非目标部件先碰探针：不能代替必需对，也不能据此重新瞄准；Task A3 真引擎负向测试。
5. 新范围读取器破坏旧包、渲染异常或 benchmark 隔离：Task A4 全量旧回归和历史包只读检查。

## 文件与接口地图

| 文件 | 职责 |
|---|---|
| 新增 asset_decode.py | 从 scene.py 抽取受限原始解码，返回未全局规范化的 Scene 与源法线、依赖 |
| 新增 collision_proxy.py | 精确焊接、连通面分组、凸体检查、应用视觉 G、导出部件清单 |
| 修改 scene.py | 仅调用公共解码器；视觉归一化与法线算法不改 |
| 修改 contracts.py / cli.py | 新增代理路径、显式目标索引和 supplied CLI |
| 修改 mjcf.py / pipeline.py | 多碰撞资源输出、清单与编译绑定 |
| 新增 collision_scope.py | 从已绑定转换清单解析部件集合、目标及 case_id |
| 修改 validation.py / contact_statistics.py / manifest.py | 显式必需对、部件观察与统一证据核对 |
| tests/integration/test_collision_proxy.py / test_proxy_evidence.py | 代理几何、引擎、证据和迁移回归 |

上述源码均位于 `src/asset_mujoco/`。不新增第二套状态枚举或 publication 函数。

## Task A1：独立执行环境、受限解码与代理几何

**Files:** 新增 asset_decode.py、collision_proxy.py、tests/integration/test_collision_proxy.py；修改 scene.py。本任务不开放 CLI supplied，保持阶段提交可运行。

**Interfaces:**

- `decode_asset(path: Path) -> DecodedAsset`；dataclass 字段 `scene: trimesh.Scene`、`source_normals: dict[str, np.ndarray]`、`dependencies: list[dict]`、`raw: dict | None`。搬移现有解码逻辑及源声明核对，不改变 loader 参数/资源边界。
- `ProxyPart` 字段 `index: int, node: str, geometry: str, first_face: int, mesh: trimesh.Trimesh, checks: dict`；`CollisionProxy` 字段 `parts: list[ProxyPart], dependencies: list[dict], transform: list, weld_records: list[dict]`。
- `load_collision_proxy(path: Path, global_transform: np.ndarray) -> CollisionProxy`，不接受独立 scale/origin；该函数不写文件。
- `validate_convex_part(mesh: trimesh.Trimesh) -> dict` 返回数值检查记录，不替换网格。

- [ ] **Step 1：记录保护基线并建立唯一环境。** 在第二阶段外的唯一临时目录记录 git HEAD/status、第一阶段 HEAD/status、原 GLB 哈希和历史已跟踪输出哈希。不提交私人路径正文。以下是执行阶段命令，当前规划阶段不运行：

```bash
task89_env="asset_mujoco_m1_1_rebuild_8a9_$(date -u +%Y%m%d%H%M%S)"
test ! -e "/home/mcl/anaconda3/envs/$task89_env"
/home/mcl/anaconda3/bin/conda create -n "$task89_env" python=3.10 -y
task89_python="/home/mcl/anaconda3/envs/$task89_env/bin/python"
"$task89_python" -m pip install -r requirements.lock.txt
"$task89_python" -m pip install --no-deps --no-build-isolation .
"$task89_python" -m pip check
"$task89_python" -I -B -c 'import sys,asset_mujoco; print(sys.executable,asset_mujoco.__file__)'
```

任一命令失败即停止后续安装/测试，不在命令失败后误用原环境；环境名存在时重新生成唯一名字，不覆盖。记录绝对解释器路径供后续任务，不依赖另一 shell 的变量存活。源码 RED/GREEN 使用该解释器的 pytest（现有 pythonpath=src），最后安装包回归显式清除 pythonpath。

- [ ] **Step 2：先写失败测试。** test_collision_proxy.py 使用显式 box/scene fixture，不需要原 GLB 或模型服务：

```python
import numpy as np
import pytest
import trimesh

def test_proxy_uses_visual_transform_once(tmp_path):
    from asset_mujoco.collision_proxy import load_collision_proxy
    source = tmp_path / 'proxy.glb'
    mesh = trimesh.creation.box(extents=[2, 1, 1])
    mesh.apply_translation([4, 0, 0])
    mesh.export(source)
    matrix = np.diag([2., 3., 4., 1.])
    matrix[:3, 3] = [10, 20, 30]
    result = load_collision_proxy(source, matrix)
    assert len(result.parts) == 1
    np.testing.assert_allclose(result.parts[0].mesh.bounds,
                               [[16, 18.5, 28], [20, 21.5, 32]], atol=1e-7)

def test_open_part_not_silently_discarded(tmp_path):
    from asset_mujoco.collision_proxy import load_collision_proxy
    good = trimesh.creation.box()
    bad = trimesh.creation.box()
    bad.update_faces(np.arange(len(bad.faces) - 1))
    bad.apply_translation([3, 0, 0])
    path = tmp_path / 'mixed.glb'
    trimesh.Scene([good, bad]).export(path)
    with pytest.raises(ValueError, match='COLLISION_PROXY'):
        load_collision_proxy(path, np.eye(4))
```

补入可执行参数化测试：两个节点及父子矩阵、负 determinant、同一 geometry 的两个实例；非有限/退化/重复三角形/非整数越界索引、凹体、开放/平面、资源上限、精确重复顶点；主文件/MTL/纹理 ../ 和 symlink 越界，复用 os.read inode 监视断言未读越界字节。不同部件排序不依赖字典插入顺序。

- [ ] **Step 3：运行 RED。** `"$task89_python" -B -m pytest tests/integration/test_collision_proxy.py -q`；记录缺模块/断言失败，不把环境导入失败算功能 RED。

- [ ] **Step 4：实现公共解码和纯代理管线。** 将 scene.load_scene 前半段原封提取到 decode_asset；视觉继续使用原节点顺序和 normal_provenance。代理按稳定节点/geometry 排序，精确焊接后按共享边的面图拆分，显式保留所有分量。可使用以下纯 numpy 核心，不调用默认 process 或 silently-repair：

```python
vertices, inverse = np.unique(np.asarray(mesh.vertices), axis=0, return_inverse=True)
faces = inverse[np.asarray(mesh.faces)]
canonical_faces = np.sort(faces, axis=1)
if len(np.unique(canonical_faces, axis=0)) != len(faces):
    raise ValueError('COLLISION_PROXY_DUPLICATE_FACE')
edges = np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
_, counts = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
if np.any(counts != 2):
    raise ValueError('COLLISION_PROXY_NOT_CLOSED_MANIFOLD')
```

输入索引在重映射前检查；不能用强制 int cast 掩盖浮点索引。精确焊接只在代理副本，连通面 BFS 保留最小原始面索引用于排序。部件先按自身节点世界矩阵展开，再乘 G；镜像翻面一次。实例之间不焊接。

凸性检查固定为：有限及非退化三角面、每边恰两个反向面边、单连通闭合曲面、Euler characteristic=2、正体积、三维秩；每面外法线半空间应包含全体顶点，按块计算避免 N×F 常驻矩阵；对 scipy.spatial.ConvexHull 的支持边界和体积作独立对照。距离容差 `eps=1e-7 + 1e-6 * max_extent_m`，体积对照容差 `1e-6*hull_volume + eps*hull_area`，记录值；不使用 inertia 容差替代。尺寸接近 eps 无法可靠判定时明确 COLLISION_PROXY_NUMERICALLY_AMBIGUOUS，不自动放宽。ConvexHull 只用于检查，不把其输出替换用户代理。内部凹点、重面、反向壳、穿插面通过负向回归确认被拒绝；若谓词未能可靠拒绝，不开放该输入类型。

- [ ] **Step 5：GREEN 与无回归。** 运行新测试及 test_source_normals.py、test_pbr_and_obj_colors.py、test_resource_boundary.py、test_scene_transform.py；解码提取必须保持视觉导出像素、vn、UV seam 的既有断言。
- [ ] **Step 6：精准提交。** `git add` 仅本任务列出的文件，staged diff 检查后提交 `feat: validate supplied convex collision proxy geometry`。

## Task A2：请求、CLI、多碰撞资源与编译发布

**Files:** 修改 contracts.py、cli.py、mjcf.py、pipeline.py、manifest.py、tests/unit/test_contracts.py；新增 collision_scope.py；扩展 collision_proxy.py、test_collision_proxy.py。

**Interfaces:** 新字段 `collision_proxy_path: Path | None`、`validation_collision_part: int | None`；`export_collision_proxy(proxy: CollisionProxy, root: Path) -> dict` 写 meshes 并返回 schema_version=1 的代理清单；`document(request, visuals, size, scene=False, collisions=None)` 的 collisions 是 `list[dict]`，每项含 index/geom_name/mesh_name/file。旧调用默认保持 hull 资源名。`resolve_collision_case(metadata: dict) -> dict` 在本任务定义，返回 case_id、target_geom、required_pairs、collision_geoms、limitations；本任务只接入 compile 声明，A3 接入实际物理证据。

- [ ] **Step 1：写失败请求/编译测试。**

```python
def test_supplied_requires_explicit_target_for_physics(tmp_path):
    from pydantic import ValidationError
    from asset_mujoco.contracts import ConversionRequest
    with pytest.raises(ValidationError):
        ConversionRequest(input=tmp_path/'visual.glb', output=tmp_path/'out',
                          collision_mode='supplied', collision_proxy_path=tmp_path/'p.glb',
                          validation_level='physics')

def test_compile_exports_all_proxy_parts(tmp_path):
    import json
    import mujoco
    from asset_mujoco.contracts import ConversionRequest
    from asset_mujoco.pipeline import convert
    visual = tmp_path/'visual.glb'
    proxy = tmp_path/'proxy.glb'
    trimesh.creation.box(extents=[4, 1, 1]).export(visual)
    a, b = trimesh.creation.box(), trimesh.creation.box()
    a.apply_translation([-1, 0, 0]); b.apply_translation([1, 0, 0])
    trimesh.Scene([a,b]).export(proxy)
    package = convert(ConversionRequest(input=visual, output=tmp_path/'out', source_up='z',
        collision_mode='supplied', collision_proxy_path=proxy, validation_level='compile'))
    for filename in ('model.xml','scene.xml'):
        model = mujoco.MjModel.from_xml_path(str(package/filename))
        mujoco.mj_forward(model, mujoco.MjData(model))
        assert model.geom('asset_collision_000').id != model.geom('asset_collision_001').id
    data = json.loads((package/'conversion_manifest.json').read_text())
    assert len(data['collision_proxy']['parts']) == 2
    assert data['hole_validation'] == 'not_tested'
```

其他断言：hull/none 带 proxy 或目标拒绝；负数/布尔/浮点索引拒绝；候选+supplied 拒绝；选定索引越界在引擎运行前拒绝。static 不强加 mass；free+supplied 碰撞仍要求既有质量/惯量。输出 raw proxy 文件不被覆盖。

- [ ] **Step 2：RED。** 对上述新测试及 CLI supplied 子进程测试运行 pytest，保存当前 extra_forbidden/不支持碰撞错误。
- [ ] **Step 3：实现分支及清单。** Pydantic 目标索引 strict integer、ge=0；路径格式 GLB/OBJ，存在性在 loader 处理。CLI `--collision-proxy` 使用 dest=collision_proxy_path。pipeline 将 supplied 加入允许集合，在视觉 load_scene 获得 info['matrix'] 后加载代理并导出，不改变视觉加载/归一化代码。代理清单包含 source_dependencies、transform、weld_records、parts、target_index、collision_fidelity；每项 part 包含源映射、AABB、顶点/面数、checks、file/sha256 与 geom_name/mesh_name。

```python
collisions = None
if request.collision_mode == 'supplied':
    proxy = load_collision_proxy(request.collision_proxy_path, np.asarray(info['matrix']))
    if request.validation_collision_part is not None and request.validation_collision_part >= len(proxy.parts):
        raise ValueError('COLLISION_PROXY_TARGET_OUT_OF_RANGE')
    proxy_manifest = export_collision_proxy(proxy, staging)
    proxy_manifest['target_index'] = request.validation_collision_part
    collisions = proxy_manifest['parts']
```

metadata['collision_proxy'] 仅新模式需要；compile_resources 自动遍历 XML 全部引用，不能遗漏非目标部件。mjcf 使用 geom mass=0、原碰撞位、group=3，free 显式 inertial 不变。代理路径只作来源信息，运行资源全相对化。compile 无目标时范围声明无 required_pairs；共用解析器在本任务接入 manifest 声明部分，A3 完成前不开放 supplied physics/full。解析器对已校验的 supplied 清单构造结果如下，旧 hull/none 分支保留原 case 与名字：

```python
body = metadata['request']['body_mode']
target_index = metadata['collision_proxy']['target_index']
parts = metadata['collision_proxy']['parts']
names = [part['geom_name'] for part in parts]
target = None if target_index is None else names[target_index]
case = {
    'case_id': 'native_supplied_part_probe_v1' if body == 'static' else 'native_supplied_part_ground_v1',
    'target_geom': target,
    'required_pairs': [] if target is None else [[target, 'probe' if body == 'static' else 'ground']],
    'collision_geoms': names,
    'limitations': ['SELECTED_COLLISION_PART_ONLY'],
}
```

构造前校验列表非空、索引连续、名字/文件不重复、target与request一致且范围合法。test_collision_proxy 的 compile断言同时检查 declared 和空 required_pairs；不要借用旧 hull 的 asset_collision 声明。

- [ ] **Step 4：GREEN。** 新 compile/CLI 测试及 test_mjcf/host/package 相关实际存在测试通过；复制新包到另一个临时目录，真实编译与 forward，原样指纹一致；对 hull 与 supplied 的视觉 OBJ/PNG 字节做对比。
- [ ] **Step 5：提交。** `feat: export supplied collision parts with bound provenance`；中间如尚无 A3，supplied physics/full 必须显式报告尚未实现，不允许错误使用单 asset_collision 验证器。

## Task A3：明确目标接触、范围核对及负向证据

**Files:** 新增 tests/integration/test_proxy_evidence.py；扩展 collision_scope.py；修改 validation.py、contact_statistics.py、manifest.py、pipeline.py。

**Interfaces:** `resolve_collision_case(metadata: dict) -> dict` 返回 case_id、target_geom、required_pairs、collision_geoms、limitations；对 old hull 不要求新清单。`ContactStatistics(collision_geoms=None, target_geom='asset_collision')` 默认序列化保持旧结果，supplied 增加 per_collision_part 观察，不提升非目标验证。

- [ ] **Step 1：先写范围与真实引擎失败测试。**

```python
def test_scope_requires_the_selected_part():
    from asset_mujoco.collision_scope import resolve_collision_case
    meta = {'request':{'body_mode':'static','collision_mode':'supplied',
                      'validation_collision_part':1},
            'collision_proxy':{'schema_version':1,'target_index':1,'parts':[
                {'index':0,'geom_name':'asset_collision_000','mesh_name':'collision_mesh_000',
                 'file':'meshes/collision_000.obj'},
                {'index':1,'geom_name':'asset_collision_001','mesh_name':'collision_mesh_001',
                 'file':'meshes/collision_001.obj'}]}}
    case = resolve_collision_case(meta)
    assert case['required_pairs'] == [['asset_collision_001','probe']]
    assert case['case_id'] == 'native_supplied_part_probe_v1'
    assert 'SELECTED_COLLISION_PART_ONLY' in case['limitations']
```

test_proxy_evidence 创建两箱体代理：一块在原固定探针下，第二块离开路径；选第二块时即便第一块接触也失败。通过 XML 将目标 contype/conaffinity 均置0、或 pos 移到远处，运行现有 run_contact_case，断言 contact_count=0、status=failed、initial_position 没变化。仅故障注入副本允许修改 XML，不改正式参数。测试匹配目标并保存它的实际结果，不预写 preserve 必然 passed。

- [ ] **Step 2：RED。** 运行 test_proxy_evidence.py；纯解析断言可能已随 A2 通过，必须记录真实 native/fixture 仍使用单 geom 假设导致的失败，不能把已绿单元用例冒充 RED。
- [ ] **Step 3：统一目标解析并扩展观察。** collision_scope 检查清单索引连续、geom名/资源映射唯一、目标与request一致；static/free 选择 probe/ground，none 无必需对。validation 从本包 conversion_manifest 取 case，不从被修改的碰撞体重新选择落点。run_contact_case 使用 case['required_pairs'][0]；benchmark 仅为同一目标的独立受控测试。

```python
metadata = json.loads((package/'conversion_manifest.json').read_text())
case = resolve_collision_case(metadata)
pair = tuple(case['required_pairs'][0])
statistics = ContactStatistics(collision_geoms=case['collision_geoms'],
                               target_geom=case['target_geom'])
```

native 记录目标和所有部件实际解析参数；contact_result_manifest 镜像记录。manifest._scope_projection 复用解析器，核对清单、model/scene/native fixture 中全部 geom→mesh→file 关系，核对 native expected_pair、case_id、body_mode、完整碰撞集合、目标索引及统计。compile-only 无目标保持 declared；full 无 verified 范围继续拒绝发布。新版语义只用于 supplied；旧 hull 不添加不存在的新证据要求。

对全体代理资源与清单使用现有 compile/physics 层绑定；不形成报告循环哈希。渲染和发布继续现有完整结果刷新机制。free 的 per-part 统计以 ground 对为观察对象，不给没有 probe 的工况伪造 on_probe 力值；既有 hull 统计布局保留，supplied 新观察明确力的对象。

- [ ] **Step 4：补全证据故障与迁移测试并 GREEN。** 对真正编译包逐一修改非目标 OBJ、目标清单、目标索引、fixture geom名；checked_report 不能继续通过，report 不写文件。对 compile-only 或 native failed 均可检查对应证据失效，不伪造 passed。在隔离合成用例以哈希自洽但语义冲突的数据检查 contradictory。已有 benchmark 异常/渲染 unavailable/failed 矩阵照常运行，atomic_publish 门槛不能被 mock。

free 测试对同一视觉物体分别 hull 与 supplied，真实读取 body_mass/body_ipos/body_inertia/iquat，比较 box_approx 与用户 supplied 惯量不变；代理形状不代替质量几何。physicspassed 只在引擎实测达标时记录，未达标的新模式不能声称完整物理验收通过。

- [ ] **Step 5：提交。** `feat: bind supplied proxy validation to an explicit collision part`。

## Task A4：安装包回归、公开用法与交付

**Files:** README.md、docs/design/PHASE2_MUJOCO_DESIGN.md 受影响局部、docs/usage/COLLISION_PROXY.md（新增）、docs/design/TASK8A_IMPLEMENTATION_REPORT.md（新增）、deployment_manifest.json 增量记录；不擦除旧证据。

**Interfaces:** 公开 `--collision-mode supplied --collision-proxy ... --validation-collision-part ...`；compile 包内 conversion_manifest 部件列表用于选择目标。

- [ ] **Step 1：新增安装包 CLI 回归。** 子进程执行 help/compile/report，检查 package 资源和分层字段，再执行 supplied physics/full 记录实际通过或失败；不能用 pytest.raises 结果冒充资产达标。fixture 为合成 box 及代理，不声称真实用户代理已测。
- [ ] **Step 2：重装新环境并运行，不改旧环境。**

```bash
"$task89_python" -m pip install --no-deps --no-build-isolation .
env -u PYTHONPATH "$task89_python" -B -m pytest -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs
"$task89_python" -m pip check
"$task89_python" -I -B -c 'import asset_mujoco,sys; print(sys.executable,asset_mujoco.__file__)'
```

核对安装源码哈希与工作树一致后才接受安装包结果。保存 stdout/stderr、退出码与 skip 原因；只有实际已执行的结果可计入报告。若 EGL/OSMesa 都不可用，full 验证记 pending/失败，不修改驱动或偷偷降级。

- [ ] **Step 3：写真实使用示例与保护核对。** 说明代理准备、同一坐标系、部件选择、缺省 preserve、compile≠physics、孔洞未验证；给出唯一输出目录命令。比较第一阶段 HEAD/status、原输入及旧输出保护哈希；新证据用新目录，私人输入不提交。
- [ ] **Step 4：本地文档提交并停止扩展。** `docs: document supplied proxy contracts and validation evidence`。检查 diff 只有本任务授权文件，保留原有未跟踪文件；不 push，不安装 CoACD，不开展质量积分/孔洞专项。

## 自检映射与执行交接

设计 3→A1/A2；设计 4→A2/A3；设计 7 的几何/边界/证据/迁移→A1–A4。五项 Review Focus 均已分配。9 的实现见 [TASK9_IMPLEMENTATION_PLAN.md](TASK9_IMPLEMENTATION_PLAN.md)，不得因 8A 完成把整个任务 8 标完成。

计划不预设新的实测数字。用户确认计划与执行方式后，执行者先使用相应实施技能，再按每任务 RED→GREEN→阶段提交推进。
