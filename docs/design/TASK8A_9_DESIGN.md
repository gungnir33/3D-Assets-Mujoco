# 任务 8A + 9：碰撞代理与 HTTP 串联设计增补

状态：用户已确认本设计；不是已实现功能或验证报告。2026-09-21。对应实施计划：[8A](TASK8A_IMPLEMENTATION_PLAN.md)、[任务 9](TASK9_IMPLEMENTATION_PLAN.md)，待计划审核及执行方式选择。

本增补归属于 [当前权威设计](PHASE2_MUJOCO_DESIGN.md) 的任务 8 和任务 9，不重写其 18 章/10 项任务，不替换 [M1.2 收尾记录](M1_2_CLOSEOUT.md)。这里仅细化新增接口与验收边界；审核通过后再形成两个可独立交付的实施计划。

## 1. 已确认意图、基线与不做事项

目标：用户能用已有 GLB/OBJ 配合自备凸碰撞代理输出 MuJoCo 包；能通过一个正式命令调用第一阶段原有 API，再调用第二阶段转换。第一阶段完全独立，第二阶段失败不要求重新生成。

只读核对：

- 第二阶段 `/home/mcl/workspace/3D-Assets-Mujoco`，main，HEAD `bb0a702984e0441bd589a0c2a9a94aa270f067dc`，origin `https://github.com/gungnir33/3D-Assets-Mujoco.git`。
- 第二阶段唯一原有未跟踪文件为 `PHASE2_M1_1_CODEX_FIX_INSTRUCTIONS.md`，不修改或提交。
- 已审核代码定位 `746949a90953ad88e774aec689a71124707a1f06`；之后仅收尾文档。
- 第一阶段 HEAD `c78d96ea41a692917918af3d9ce4d3821be64f2b`，工作区干净；只读检查 schemas/app，不导入服务应用或加载模型。
- 现有独立解释器 `/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python`；Python 3.10.21、MuJoCo 3.4.0、numpy 2.2.6、scipy 1.15.3、trimesh 4.7.4、pydantic 2.11.7、pytest 8.4.1；导入位于该环境 site-packages。
- 当前实现仅 hull/none，验证器和范围投影固定单个 asset_collision；scripts/chain.py 尚不存在。

不做：CoACD、减面、质量积分、mass_geometry、watertight、孔洞专项、自动代理生成、真实宿主接入、新服务/GUI、材料标定、地面调参。supplied 碰撞代理与现有 supplied 惯量是不同概念，后者契约不变。

默认 preserve、full 验证及工程候选参数/适用范围不变。engineering_static_v1 仍仅 static+hull，不扩展到 supplied。地面观察非必需且失败如实保留。没有用户真实外观结论就保持 pending。

不修改第一阶段代码、环境、Skill、权重或既有资产；不修改宿主、驱动或历史包。真实生成 POST 本轮不执行，默认测试仅用模拟服务；将来真实串联需明确指定生成输入并授权新增 job。不自动 push。

## 2. 两个独立交付单元与取舍

采用：8A 在现有转换管线增加碰撞资源列表；9 以独立 CLI 编排 HTTP 和现有转换 Python API。共享的是稳定 ConversionRequest、convert() 与 checked_report，不共享第一阶段 Python 对象。

不采用把两阶段装进同一环境/直接 import 第一阶段：会破坏冻结边界。也不将上一轮临时 shell 示例直接当生产串联器：其缺少正式参数、错误恢复和测试契约。

8A 和 9 各自单独测试、分阶段提交；9 默认 hull，无需用户准备代理；串联可显式使用 8A，但已有代理必须与新生成资产原始坐标匹配，不能假定文本生成会自动与代理对齐。

新增能力计划使用新的第二阶段验证环境：从当前锁文件创建唯一 `asset_mujoco_m1_1_rebuild_8a9_<id>`，不覆盖现有环境；保持 Python 3.10 及锁定版本。HTTP 使用标准库，无新增推理或分解依赖。安装未执行，若依赖获取失败如实记录，不改原环境绕过。

## 3. 8A 输入与坐标契约

新增请求字段 `collision_proxy_path: Path | None`、`validation_collision_part: int | None`。CLI 增加 `--collision-mode supplied`、`--collision-proxy PATH`、`--validation-collision-part INDEX`。

- supplied 必须提供普通 GLB/OBJ 代理文件；hull/none 不接受代理参数，避免静默忽略。
- 代理与视觉输入必须共享同一原始世界坐标、尺度和 up-axis。不是已经单独归一化过的代理，不自动估计配准。
- 展开代理自身节点世界矩阵后，应用由视觉资产计算的一次全局 G：`G × T_proxy_node_world`；G 为 `T_origin × S_scale × R_yaw × R_axis`。
- 代理不独立居中、计算目标尺寸或再次归一化；原有视觉 mesh、UV、材质、法线不因代理改变。
- 视觉最终尺寸及 free 的显式惯量继续来自视觉请求/用户输入，不由代理改变；所有代理 geom 的 mass=0。
- 代理走与已有输入等效的受限 resolver；记录主文件及全部实际读取依赖路径/哈希。OBJ 依赖失败不能回退到不受限加载器；不解析或读取未使用资源时也不得声称已经校验其内容。

部件规则：每个展开的节点/geometry 实例按连通分量形成部件。只允许在该代理实例副本内合并坐标完全相同的顶点（容差 0，记录数量），不跨实例焊接、不触碰视觉副本。材质切块没有形成闭合部件时明确拒绝，建议用户提供无材质、闭合代理；不猜测跨 primitive 拼接。

每个部件必须是有限、三维、非退化、闭合、方向一致、正体积的凸三角网格。凸性与拓扑一起检查，不能仅凭 is_watertight 接受。不得静默取整体凸包、填孔、修面或丢部件。比较几何容差采用既有 rtol=1e-6/atol=1e-7 m，记录检查结果；拓扑索引合法性不使用数值容差放过。无法确认合法凸体则拒绝，具体谓词与负向夹具在实施计划中锁定。

限制：最多 32 个部件、总三角面不超过 50,000；每部件顶点不超过 10,000；超限直接错误，不自动减面。这些是新接口资源预算，不是精度或真实材料保证。

不要求代理包住所有视觉顶点：用户代理可以有意简化或保留开口。报告 collision_fidelity=user_supplied，记录各 AABB 和部件数，不声称视觉覆盖或孔洞已验证。不从多个代理的重叠体积计算质量。

## 4. 8A 导出、多部件范围与证据

新增 collision_proxy.py；复用/小幅抽取 scene.py 的原始解码边界，使视觉规范化与代理变换不重复。collision.py 的旧 hull 路径保持。

supplied 导出 `meshes/collision_000.obj` 等，相应 mesh/geom 名固定为 `collision_mesh_000` / `asset_collision_000`；索引按源节点名、geometry 名与连通分量最小原始面索引稳定排序，映射写入 conversion_manifest。旧 hull 的 collision.obj、asset_collision 命名不变。

mjcf.document 接收可选碰撞资源列表，为每个部件创建独立 mesh/geom，视觉 group=2、碰撞 group=3、原碰撞位/摩擦等保持。model.xml/scene.xml 都编译、mj_forward。不扩大 engineering_static_v1 的范围，不为 supplied 生成该候选的 contact_scene。

**多部件验收不能把“任一部件碰到探针”写成全部代理通过。** 本次采用显式单目标：

- supplied 的 compile 可不指定目标，输出部件映射，physics=not_run。
- supplied 的 physics/full 必须显式指定零起始 validation_collision_part；运行前校验索引存在。
- static 的必需对为所选 asset_collision_NNN 与 probe；free 为所选部件与 ground。
- 其他部件仍参与真实仿真，分别记录接触观察，但不替代选定的必需对；报告限制 SELECTED_COLLISION_PART_ONLY，其余部件不标为独立验收通过。
- 探针质量、半径、由视觉尺寸确定的初始位置、dt、步数及穿透阈值保持现有规则；不朝选择的部件自动重新瞄准。固定路径未接触就失败，不因此改写代理或验收工况。
- 使用新 case_id：native_supplied_part_probe_v1 / native_supplied_part_ground_v1。旧 hull case_id、必需对和报告逻辑继续兼容。

conversion_manifest 的碰撞清单绑定代理来源、G、源实例到导出部件映射、部件资源路径/哈希、校验结果和目标索引。编译证据绑定全部导出部件，不仅目标部件；物理证据绑定整个夹具及清单。native、contact_result_manifest、fixture、范围摘要必须一致，删目标/改任何碰撞资源均使旧证据失效。

采用单一范围解析辅助逻辑供 validation 和 manifest 共用，不通过名字猜测 passed。native 与 benchmark 隔离、渲染异常状态同步、发布门槛、人工指纹及只读旧包兼容全部保留。只声明 supplied compile 的包不能升级为物理通过；真实输入无孔洞探针路径继续 hole_validation=not_tested。

## 5. 9 命令与配置契约

新增可安装入口 `python -m asset_mujoco.chain`，同时提供薄包装 `scripts/chain.py`，二者同一实现，不创建另一套转换/状态逻辑。

计划提供两类互斥输入：

1. `--prompt TEXT`、`--image PATH` 或 `--mesh PATH --condition-image PATH` 三选一；分别调用 text、image、texture。
2. `--request request.json`，内容为 `{"endpoint":"text|image|texture","payload":{...}}`；不得同时提供上述简写。

公共参数：`--output PARENT` 必需；`--base-url` 默认 http://127.0.0.1:8080；`--conversion-config JSON` 可选；`--dry-run` 仅参数预检、打印解析请求，不联网、不创建任务目录。简写支持 seed=12345、face-count=40000、shape-steps=50、默认 texture=true、format=glb，可显式 --no-texture 或 --format obj。request 文件内容与简写参数不得重复覆盖。

conversion-config 使用现有 ConversionRequest 字段名（name/source_up/yaw_deg/scale/target_size_m/body_mode/collision_mode/contact_profile/validation_level/mass/inertia_mode/supplied_inertia），加上 8A 字段；禁止包含 input/output（由串联结果/唯一目录提供）。相对代理路径相对于配置文件父目录解析；命令行文件路径相对于调用 cwd。未知键或冲突先报错，不发送生成请求。JSON 文件用严格非有限数值校验。

默认配置继续 static+hull+preserve+full，不把工程候选自动启用；需要候选时用户写入转换配置。OBJ 输出必须提前指定 source_up 和 scale/target_size_m；GLB 仍沿用现有缺省尺度语义，不自动识别真实尺寸。

未来命令示例（尚未实现、未执行）：

```bash
python -m asset_mujoco.chain --prompt "A red road barrier" --conversion-config convert.json --output /absolute/output-parent
python -m asset_mujoco.chain --image /absolute/input.png --conversion-config convert.json --output /absolute/output-parent
python scripts/chain.py --request request.json --conversion-config convert.json --output /absolute/output-parent
```

当前 schemas 已核对：prompt 1..1000 字符且非空；seed 0..2^63-1；face_count 100..1,000,000；shape_steps 1..200；图片 PNG/JPG/JPEG/WEBP；texture 输入 mesh/condition_image。第一阶段 API 虽支持 FBX 输出，chain 仅允许 GLB/OBJ，默认 GLB。成功响应 job_id/file/type/metadata，file 和 metadata 为服务端路径。

## 6. 9 请求、输出和恢复

仅支持共享本地文件系统和 loopback HTTP。base-url 限定 127.0.0.1、localhost 或 [::1] 与显式端口，不接受认证信息、查询串或任意 URL 路径；localhost 解析须为 loopback。不支持 LAN 上传/下载；不跟随 HTTP 重定向，避免重发或将本地路径泄漏到其他服务；本客户端不使用环境代理，不改系统代理。

流程：先验证输入/输出配置与代理路径 → GET /health（10 秒）→ 记录请求 → 单次生成 POST（1800 秒等待超时）→ 保存响应与第一阶段来源 → 调用现有 convert → checked_report → 统一 chain_manifest/JSON 输出。1800 秒不是两个阶段合计完成承诺；超时中断客户端等待，不声称取消服务端任务。

health 不可访问时返回 LOCAL_3D_SERVER_NOT_RUNNING 和原启动脚本路径，不启动/daemonize 服务。health HTTP 成功但内容不是可识别健康响应时也不得盲目 POST。

每次非 dry-run 创建 `output/chain_<unique-id>/`，里面分别保存 request.json、phase1_response.json、chain_manifest.json、packages/。不会以固定 model.glb 文件名复制覆盖第一阶段输出。提示词和私人图片路径可能敏感；遵循当前 outputs 跟踪策略，提交时只挑公开合成证据，不自动提交真实请求日志/生成资产，不改 .gitignore。

成功响应必须是对象，job_id/file/type 类型有效，输出类型与请求一致，file 是本机可读绝对普通文件，实际格式由第二阶段解析再确认。metadata 缺失/不存在/不可读只警告，不代替必需资产；不把 metadata 路径字符串当内嵌 JSON。主要响应与错误正文读取上限 1 MiB，超过限制停止解析、报告原 HTTP 状态和截断事实，不输出大量 HTML。

接收到有效第一阶段成功响应后立即记录 job_id、file、type、metadata 和输入主文件哈希；GLB/OBJ 的完整实际依赖哈希由转换器受限 resolver 记录。phase2 失败仍保留 phase1=passed、来源路径、第二阶段诊断目录和可执行的原文件 convert 恢复命令；恢复不调用生成 API。

FastAPI 422 的 detail、业务 error.code/message/details、非 JSON 响应分别保存；不将所有错误包装成 connection refused。生成 POST 只发一次，不自动重试；POST 后连接中断、超时或无法确认成功响应时 phase1=unknown，不假定无 job。明确服务端业务拒绝记录 failed 及原错误，但不声称服务没有留下失败 job。

退出码：0 仅请求的第二阶段必需等级通过；本地请求配置错误 2；持久化故障 3；第一阶段 HTTP/连接/结果未知或响应契约错误 6；第二阶段保留既有 2/3/4/5/7 分类。人工 pending 不要求非零。stdout 为一个结构化 JSON，进度写 stderr；所有阶段有独立状态，不能仅因 HTTP 200 宣称资产完成。

chain_manifest 位于资源包外，不在发布后向包追加来源导致审核指纹变化。它引用第一阶段响应和包路径/指纹/checked_report，不给旧包补签，不把 benchmark、人工或宿主结论提升。

## 7. 交付与验收安排

8A 涉及 contracts、cli、scene、collision_proxy（新）、mjcf、pipeline、validation、contact_statistics、manifest；必要时新增轻量 collision_scope 共用逻辑，不重构无关模块。9 新增 chain/chain_contracts 模块及 scripts/chain.py；复用转换 API，不 import local_3d_agent、torch 或 hy3dgen。

| 测试文件（计划） | 必需断言 |
|---|---|
| tests/unit/test_contracts.py | supplied 缺代理、无关代理参数、候选+supplied、full 缺目标、非法索引/配置均明确拒绝 |
| tests/integration/test_collision_proxy.py | 多凸体、节点世界变换、yaw/fit_axes/原点共用 G、无二次居中；非法/开放/凹/重复面/平面/超预算拒绝；源/视觉不变；依赖越界读取前拒绝 |
| tests/integration/test_proxy_evidence.py | 全部部件真实编译/forward；选择的必需对准确；碰撞位清零/移走负向失败；非目标接触不顶替目标；修改非目标资源也失效；迁移后范围一致 |
| tests/integration/test_proxy_evidence.py | free 的 box_approx/supplied 惯量编译值不因代理改变；compile 与 full 状态不混淆；真实引擎结果无论通过/失败均按原阈值报告 |
| tests/unit/test_chain_contracts.py | 三种 payload、两种输入形式互斥、1000字符、格式限制、OBJ尺度、输出/输入字段保护、URL/重定向规则、dry-run零请求 |
| tests/integration/test_chain.py | 模拟 200/422/503/非JSON/超时/断连、无重试、source恢复、metadata警告、输出唯一、I/O失败不报成功 |
| tests/integration/test_chain.py | 临时本机模拟生成服务返回合成 GLB，真实 convert 编译及完整已有候选配置验证，检查CLI退出/包/report一致；不是 Hunyuan3D 真实 E2E |

保留现有发布门槛、渲染异常、旧包只读兼容、范围/指纹、benchmark隔离、材质/法线/资源安全测试；不删测试、不放宽阈值。完整 pytest 与 pip check 结果重新记录，不复用 183 passed 充当新结果。

8A 不以人为降低落点/阈值使默认 preserve 达标；转换/编译能力与特定工况物理达标分别报告。用户尚未提供真实代理时，用合成资产及代理完成通用回归，真实代理适配=not_tested；当前企鹅继续只读保留，不拿自动生成的代理冒充用户输入。

交付更新当前设计受影响契约和 README，新增使用说明及实现报告，分别记录代码测试、模拟串联、真实第一阶段生成（本轮 not_executed）、人工 pending、宿主 pending。阶段提交后停止，不自动 push；不将 8A 完成称为整个任务 8 完成。

## 8. 设计审核检查与下一步

本文件已将代理坐标、部件选择、旧证据兼容、默认参数、错误/恢复、HTTP限制和未验证边界分开说明。具体几何谓词、函数签名及逐步失败测试由审核后的实施计划展开；本文件不声称任何新增算法已验证。

本设计已获用户确认，现已分别编写 8A 与 9 的实施计划；确认计划和执行方式后再开始失败回归→实现→验证。当前阶段不安装依赖、不写生产代码、不执行生成 POST。
