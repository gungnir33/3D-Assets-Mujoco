# 第二阶段 R2 修订对照、只读证据与待实测清单

检查日期：2026-09-10（Asia/Shanghai）。本轮只修改设计文档及其追溯记录；表中的“已落实”仅指文档修订，不代表功能已实现或测试通过。

## 1. 文件与权威版本

- 当前权威设计：[PHASE2_MUJOCO_DESIGN.md](PHASE2_MUJOCO_DESIGN.md)，R2，保留原有 18 章结构。
- 主要依据：[完整修订指令](PHASE2_MUJOCO_CODEX_REVISION_INSTRUCTIONS.md)。完整阅读后逐项落实；该文件未修改。
- 原稿：[PHASE2_MUJOCO_DESIGN.original.md](PHASE2_MUJOCO_DESIGN.original.md)，只归档不维护。
- 原稿 SHA256：`c164ad9790ca0705758de8b28f8a6ae564e74b12188505086ee648503d92c1ee`，与修订前文件一致。
- 修改记录：[统一差异文件](PHASE2_MUJOCO_DESIGN.r2.diff)。本报告补充修订理由与验证边界。

第二阶段初始化后，唯一权威正文迁入 `/home/mcl/workspace/3D-Assets-Mujoco/docs/design/PHASE2_MUJOCO_DESIGN.md`。原 tasks 位置改为指针，记录迁移路径、版本、提交与 SHA256；原稿和修订记录作为历史归档，不进行双份正文维护。

## 2. 本轮只读环境与仓库检查

| 项目 | 实际检查结果 | 解释和边界 |
|---|---|---|
| 原设计文件 | 存在并已完整读取 | 非重新创建的替代稿 |
| 指令文件 | 存在并完整读取 | 主执行依据 |
| 默认新目录 /home/mcl/workspace/3D-Assets-Mujoco | 不存在 | 拟用路径，尚未初始化 |
| 旧目录 /home/mcl/workspace/3D-Assets-MuJoCo | 不存在 | 未删除、重命名或另建目录 |
| 第二阶段 remote | https://github.com/gungnir33/3D-Assets-Mujoco.git | 精确固定，未改 owner/name |
| git ls-remote（沙箱内） | 退出 128，Could not resolve host: github.com | DNS 错误不表示空仓库 |
| git ls-remote（沙箱外只读重试） | 退出 0，无输出 refs | 检查时没有公布 refs；后续初始化前重新检查 |
| 第一阶段 HEAD | c78d96ea41a692917918af3d9ce4d3821be64f2b | 本轮前后核对，不写入第一阶段 |
| 第一阶段 status --porcelain | 无输出 | 未 reset 或清理用户数据 |
| asset_mujoco 环境 | Conda 清单未列出 | 未创建、未安装 |
| acs_test 候选环境 MuJoCo | 安装元数据 3.2.3（Python 3.8 路径） | 只读 METADATA，未加载引擎 |
| sim_test 候选环境 MuJoCo | 安装元数据 3.4.0（Python 3.11 路径） | 只读 METADATA，未加载引擎 |
| 实际目标宿主 | 尚未确认 | host_compatibility=pending；不将候选安装版本当目标确认 |
| EGL/OSMesa/GLFW | 未探测 | 本轮不做渲染实验 |
| MuJoCo/CoACD/shell 策略 | 未运行 | 均列为后续任务 |

版本信息来源为现有环境的 dist-info/METADATA，而非执行安装或升级。未全面扫描每个磁盘环境，不宣称本机只有这两个 MuJoCo 版本。

第一阶段协议已只读检查 `src/local_3d_agent/service/schemas.py` 与 `service/app.py`：三个端点字段为 prompt / image / mesh+condition_image，响应 job_id/file/type/metadata；metadata 为字符串路径；错误处理存在 error.code/message/details，Pydantic 422 使用 FastAPI detail。本轮没有发送 HTTP 请求。

### 三份真实资产原始格式检查

只读标准库解析 GLB JSON 及文件哈希，没有转换或导入 MuJoCo。资源特征不是转换兼容性证明。

| job | 大小（bytes） | 原始 primitive 特征 | 材质/图片 |
|---|---:|---|---|
| 20260909_210330_6c804545 | 13706092 | POSITION，无 COLOR_0 | 0 / 0 |
| 20260909_210532_fe231a7e | 22404152 | POSITION，无 COLOR_0 | 0 / 0 |
| 20260909_210805_9dfdcdd0 | 3076972 | POSITION、TEXCOORD_0，无 COLOR_0 | 1 / 1 |

第三份原始材质含 baseColorTexture，baseColorFactor 为 [1,1,1,1]，roughnessFactor 约 0.9036；本轮仅确认字段，不宣称 MuJoCo 已保留其 PBR 效果。三者 extensionsUsed 均未声明扩展。

源文件哈希：

```text
18659f94dcc66ba4d80a95c637f2bbe2194501cad54bd4fd3574c170f7d31fa4  20260909_210330_6c804545/model.glb
62d7be2ff354320570674c67fdf07dfc011b05830b492ef3bbc2801892c85554  20260909_210532_fe231a7e/model.glb
12f1ed66a874efbdb3c350d819c1f6e076de469e7dc191d236de82073fdd2e12  20260909_210805_9dfdcdd0/model.glb
```

## 3. 审核问题—原章节—修改—测试—状态

| 审核问题 | 原章节 | R2 修改内容 | 对应计划测试 | 当前状态 |
|---|---|---|---|---|
| 固定仓库、新旧目录 | 2、4、16 | 精确 remote 与 Mujoco 大小写；旧目录工作保护，非零访问不当空库 | 任务1 test_isolation.py；初始化重查 refs | 只读检查完成，未初始化 |
| 原稿和多个正文漂移 | 开头、18 | 字节一致原稿、差异、唯一权威迁移指针 | 归档哈希；任务1迁移记录 | 文档已落实 |
| 冻结和新增 job 语义 | 2、13 | 既有源码/资产冻结；后续显式 API 可新增唯一 job | 任务1/9/10 基线与哈希、独立运行 | 协议及现状已查，独立运行未测 |
| 双副本职责不够 | 3、4、9 | visual/collision/mass 三副本，mass 可内存处理 | 任务8 test_mass_geometry.py | 未实现 |
| scale 默认值冲突 | 4、6 | None 与显式 scale 区分；OBJ 必须单位参数 | 任务1 test_contracts.py | 未测 |
| yaw 和 XYZ 语义 | 4、6 | axis→yaw→scale，target 最终 XYZ，不排序 | 任务2 test_scene_transform.py | 未测 |
| supplied 碰撞独立归一化 | 6、8 | 代理自身节点展开后共享视觉 G | 任务8 test_collision_proxy.py | 未测 |
| 平面/三角 primitive 编译 | 7、15 | 真实编译实验前移到任务3；shell 候选；禁止改厚或丢 primitive | test_visual_mesh_compile.py 四类夹具 | 未编译，候选未验证 |
| 视觉 mesh 影响刚体惯量 | 7、9、15 | 显式 inertial 独立；编译重建张量比对 | 任务5/6 test_inertia.py、test_mjcf_compile.py | 未测 |
| supplied frame/unit 不清 | 4、9 | normalized_body/com、m/kg·m²、最终质量尺寸；不作二次变换 | 任务1/5 frame 拒绝及张量映射 | 文档契约已落实，未测 |
| watertight 不等于可信积分 | 9 | 单闭合无自交实体前提，拒绝重叠/嵌套/不可信 | 任务8 test_mass_geometry.py | 后端待实测，未测 |
| seam 焊接、薄壁与原点 | 9 | mass 专用副本与记录容差，不改视觉，COM 张量不重复平移 | seam/重叠/双倍尺寸四倍惯量/原点测试 | 未测 |
| 加载器静默丢材质信息 | 5、7 | 原始 GLB JSON 清单+trimesh 映射核对 | 任务2 test_raw_features.py、任务4 | 已检查三份原始字段，解析转换未测 |
| UV/sampler/颜色因子 | 7 | 显式支持矩阵、颜色因子只一次、多材质共享图 | 任务4 test_visual_assets.py | 未测 |
| 纯色纹理误判 | 7、13 | 删除通用非单色要求；四色仅夹具断言 | 纯色贴图和四色用例 | 文档已落实，未测 |
| hull 包含性失真 | 8 | 原始规范化全部顶点取 hull，预算不够失败 | 任务5 test_hull.py 逐点包含性 | 未测 |
| CoACD 预算等同精度 | 8、14 | 分开预算/阈值语义，记录处理与最终合法性 | 任务8 test_decomposition.py | 参数未锁定，未测 |
| 孔洞测试顺序与真实结论 | 8、13、15 | 任务8依赖仿真；真实资产没路径为 not_tested | test_hole_contact.py | 三份资产 hole_validation=not_tested |
| autoreset/末态 finite 假通过 | 13 | energy 开启，逐步 qacc/time/warning/首异常，禁 autoreset 并核对 | 任务7 test_physics_render.py | 未运行 |
| ncon 不能证明目标接触 | 13 | 具体 geom 对、阶段、路径和穿透断言 | 任务7/8 接触夹具 | 未运行 |
| 渲染/物理/人工混同 | 13、14 | 四维状态，validation_level、退出码与人工 pending 区分 | test_validation_states.py | 文档矩阵已落实，未测 |
| chain 请求和响应 | 11 | 精确端点字段、响应路径、本地共享 FS、GLB/OBJ 前置检查 | 任务9 test_chain.py | 当前协议只读已确认，未调用 |
| 422/503/超时信息 | 11 | detail 与 error 兼容，POST 无重试，超时 unknown，恢复来源保留 | 任务9 错误与恢复 mock | 未实现 |
| 渲染后端与宿主版本 | 12、13 | 后端独立子进程、OSMesa 有效、converter/host 分列 | 任务3/7/10 | 候选宿主安装版本已查，兼容 pending |
| 真实减面依赖 | 12、15 | 可选 CoACD/fast-simplification 依赖核实，独立环境 | 任务1/8 lock 与后端测试 | 未安装、未锁定 |
| output 父目录/staging | 5、10、11 | 父目录可含任务，唯一包，原子发布，最终路径重验 | 任务6 test_package_publish.py | 未测 |
| 最小宿主合并与 fixture | 2、10、15 | 合成合并示例，不改真实 ACS；保留 XML/OBJ/PNG fixture | test_host_merge.py、git ignore 测试 | 未测 |
| 先闭环再扩展 | 15 | 十任务，任务7真实 static+hull M1 门槛 | test_milestone_static.py | 计划已调整，未执行 |

## 4. 实施顺序和里程碑

1. 独立仓库、环境、冻结基线、完整契约。
2. 原始格式、Scene、尺度和 yaw。
3. 最小真实 MuJoCo 编译实验。
4. 视觉资源和材质。
5. 原始顶点 hull、box_approx、supplied 惯量。
6. static/free XML 与可移植包、最小宿主合并。
7. 物理/渲染/状态检查与 M1。
8. CoACD、supplied 碰撞代理、mass_geometry/watertight、孔洞。
9. 原有 HTTP 协议串联。
10. 三份真实资产验收、文档与清单。

M1：一份已存在的真实 GLB → 经确认的方向/尺度/颜色/贴图 → static+hull → 两份 XML 编译 → 具体动态探针接触正确 → MuJoCo 原生渲染 → 换目录仍可加载。该自动闭环通过前不优先进入任务 8/9；人工外观结论单独记录，不能因为自动通过而代填批准。

详细模块、测试文件、断言、前置依赖和每项通过条件在主设计第 15 节，避免两套详细计划漂移。

## 5. 尚需实测的兼容策略与失败处理

| 策略/疑点 | 验证任务 | 需要的证据 | 失败处理 |
|---|---|---|---|
| converter 与真实宿主版本 | 1、3、10 | 明确目标解释器/加载版本、同资产编译和仿真 | compatibility=pending/failed，不改第一阶段环境 |
| shell 处理平面/开放 mesh | 3 | 四类子网格真实编译+forward | 不支持错误或经测无损细分；阻断 M1 则报告 |
| 少顶点 primitive 细分适配 | 3 | 表面/UV/法线保持及编译成功 | 不加厚/删面/删材质；报不支持 |
| 多材质/UV/sampler/因子保留 | 4 | 原始/解析映射、四色及纯色原生渲染 | 严格拒绝或用户明确允许的损失，不静默忽略 |
| supplied fullinertia 映射 | 5、6 | 非对角张量编译重建、质量/COM 比对 | 报惯量错误，不自动坐标补偿 |
| 原始顶点 hull 预算与包络 | 5 | 所有源点包含性及资源耗用 | 超预算失败，不先简化假称完整包络 |
| mass 几何焊接及自交检测后端 | 8 | seam、薄壁、重叠/开放/自交/嵌套壳 fixture | 无法证明则拒绝 watertight，由用户另选策略 |
| CoACD 实际参数和精度语义 | 8 | 锁版本真实参数、凸体合法性与数量、接触专项 | 失败默认退出，仅显式 fallback=hull 并记原原因 |
| 当前资产孔洞可穿过 | 8、10 | 当前资产配置的探针路径与明确接触对 | 无路径 not_tested；失败不外推标准夹具结论 |
| autoreset 与数值/资源 warning | 7 | 开关生效、逐步时间和首异常检查、异常注入 | 任何假重置/异常失败，不只看最终 finite |
| EGL/OSMesa/GLFW | 4（材质小测试）、7 | 分进程导入前选后端，实际渲染和 viewer | OSMesa 可正常通过；均不可用 full 退出7，保留物理通过 |
| 包移动和最小宿主合并 | 6、10 | 原子发布后/不同 CWD/新目录加载，宿主属性不变 | 不发布请求等级未达标包；诊断保留 |
| 真实串联与超时 | 9、10 | mock 完整错误结构；显式真实测试共享路径 | unknown 不重试，保留成功 job 恢复入口 |
| 人工外观 | 7、10 | 审核人、时间、资产哈希、图片和明确结论 | pending/rejected 时不 FULLY_VALIDATED |

## 6. 本轮执行边界和文档验收

本轮未安装/修改 Python 或 Conda，未执行 MuJoCo 编译/forward/step/render，未运行资产转换，未调用第一阶段生成 API，未改第一阶段源码/Skill/模型/配置，未初始化第二阶段工程，未 git push/force push 或创建远端。

文档检查包括：原稿哈希一致、18章保留、10项任务顺序、相对链接、Markdown 围栏、无未完成占位符、旧冲突表述扫描、第一阶段 HEAD/status 前后对比以及三份源资产 SHA256 前后复核。这些是文档及只读检查，不记为第二阶段工程测试通过。

修订完成后停止，等待用户审核，不自动进入任务 1。
