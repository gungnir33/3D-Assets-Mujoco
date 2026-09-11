# 3D Assets → MuJoCo

独立第二阶段转换器。只读使用已有 GLB/OBJ，不 import 第一阶段、不加载 CUDA 模型。
模型、真实输入及 outputs 不提交 Git。MuJoCo、trimesh 等依赖遵循各自许可证；本仓库尚未选择项目许可证，不推定 MIT 授权。

环境：Conda asset_mujoco、Python 3.10.21、MuJoCo 3.4.0。
requirements.lock.txt 为本次独立环境实测锁文件；不要安装到 hunyuan3d 或现有宿主。

M1.1 已用独立 `asset_mujoco_m1_1_rebuild` 重建安装并完成回归。新环境安装示例（名称已存在时另选唯一名称）：

```bash
conda create -n asset_mujoco_m1_1_rebuild python=3.10 -y
conda run -n asset_mujoco_m1_1_rebuild python -m pip install -r requirements.lock.txt
conda run -n asset_mujoco_m1_1_rebuild python -m pip install --no-deps --no-build-isolation .
conda run -n asset_mujoco_m1_1_rebuild python -m pip check
```

锁文件 stdout 与 stderr 分开生成，不把 WARNING 写入依赖；没有修改原有环境或系统驱动。

## 使用

在本仓库根目录运行：

```bash
conda activate asset_mujoco
export PYTHONPATH="$PWD/src"
python -m asset_mujoco.cli inspect /absolute/input.glb
python -m asset_mujoco.cli convert /absolute/input.glb \
  --output ./outputs --name example --source-up y --yaw-deg 0 \
  --scale 0.5 --validation-level full
```

--output 是父目录，每次创建唯一包，不覆盖旧任务。最终包包含 model.xml、scene.xml、meshes、textures、previews 和 JSON 证据。移动时复制整个目录。
model.xml 是无地面的完整模型；scene.xml 为独立查看场景。不要直接把 scene.xml include 到用户宿主。

static 默认不需要质量或惯量。free 使用：

```bash
python -m asset_mujoco.cli convert /absolute/input.glb \
  --output ./outputs --body-mode free --mass 2 --inertia-mode box_approx
```

box_approx 不代表真实质量分布。supplied 使用 --supplied-inertia /path/inertia.json，字段见 contracts.SuppliedInertia；
必须是最终 normalized_body 坐标系、关于 COM、m 和 kg*m^2，不再应用 yaw/scale。
OBJ 必须指定 --source-up 及 --scale 或 --target-size-m。
target-size-m 是最终 XYZ；与 scale 互斥。uniform 用单一最小二乘比例，尺寸近似误差2%；fit_axes 会改变形状，必须显式选用。
显式倍率/目标尺寸只代表用户声明，`physical_scale_verified=false`；`scale_evidence` 记录来源、已应用参数及空的确认依据。历史 M1 包曾将显式倍率误标为已验证，不能用作物理尺寸证明。

## 验证和人工审核

```bash
python -m asset_mujoco.cli report ./outputs/package_name
python -B -m pytest -p no:cacheprovider -q
```

compile/physics/full 为请求的自动验证等级，正常资产默认 **full**；compile-only 必须显式指定。渲染不可用返回 7，不自动降级 compile。full 自动通过仍为 PHYSICS_VALIDATED，人工审核默认 pending。
物理验收运行当前导出资产的原始碰撞配置，不添加强制 contact/pair，不修改资产碰撞位、摩擦或接触参数。受控 benchmark 独立记录，不能覆盖原始配置失败。
native完成后立即保存独立结果和哈希；benchmark为非强制诊断项，其异常不覆盖native、不阻止独立渲染。证据I/O失败单独报EVIDENCE_IO_ERROR并禁止发布。新physics层不绑定benchmark或可变汇总文件。
人工查看 previews 后才可记录：

```bash
python -m asset_mujoco.cli review ./outputs/package_name \
  --reviewer YOUR_NAME --decision approved \
  --images previews/front.png previews/side.png previews/iso.png
```

审核记录绑定包内容哈希；改变 XML、资源、预览或证据后旧批准失效。report 每次重新判定，不依赖旧总状态。
`evidence_manifest.json` 分别绑定编译资源、物理夹具/结果、渲染配置/预览；`report` 仅检查旧证据，不重新编译或仿真，不给变化后的内容补签通过。缺少新证据的旧包保守显示 not_run。原样迁移不失效。
VISUAL_ONLY 仅 --collision-mode none --validation-level compile，physics=not_applicable。

退出码：0 请求自动等级通过（不等于人工批准）；2 输入错误；3 转换错误；4 XML 编译错误；
5 物理/渲染内容失败；7 渲染后端不可用。失败 staging 保留诊断，未发布包不能作为成功输出。

## 当前边界与故障排查

- M1 示例是举 HY3D 牌子的企鹅；scale=0.5 是演示尺寸，不是对真实物理尺寸的测量。
- hull 包住全部原始顶点，但会填平孔洞；hole_validation=not_tested。
- 单三角形 primitive 暂不支持，不静默增加厚度。平面 shell 仅3.4.0实测可用，3.2.3不识别该属性。
- EGL 已通过；OSMesa 当前 OpenGL 加载不可用，没有修改系统包或驱动。
- 透明、顶点色、额外 UV、压缩、骨骼/morph 和扩展材质严格拒绝；非完整 PBR 等价转换器。
- OBJ/MTL/纹理在实际读取 resolver 层限制于输入文件父目录，禁止越界和符号链接越界，无不受限 fallback。必需资源缺失直接失败。
- 有 PBR 材质但省略 baseColorFactor 时使用白色全 1；真正无材质使用默认灰色。源法线按完整组合变换的逆转置导出，缺失才计算并记录来源。
- 非默认宿主 compiler 冲突会报 HOST_COMPILER_CONFLICT，不自动修正宿主。
- CoACD、supplied 碰撞代理、watertight 积分和 HTTP 串联尚未实施。

历史M1.1结果：94 passed、1 skipped（OSMesa）；当时失败包保留于 `outputs/penguin_m1_1_20260911_final/.staging-396kwwx1`。不作为新一轮验收证据。

最新验收补强/接触诊断：安装包模式107 passed、1 skipped，真实验收命令仍退出5；原始配置重测最大穿透11.795mm > 5mm，首次接触/首次超限/最大穿透分别为第144/146/153步。两份XML、EGL渲染、迁移通过；人工审核和真实宿主集成pending。**软件回归通过不等于真实资产自动验收通过。**

## 显式验收与接触诊断

安装新源码到独立环境后执行（不要运行旧site-packages）：

```bash
conda run -n asset_mujoco_m1_1_rebuild python -m pip install --no-deps --no-build-isolation .
conda run -n asset_mujoco_m1_1_rebuild python -m asset_mujoco.acceptance --output ./outputs/contact_diagnosis
# 诊断的 --package 使用上一步返回的新package路径，不指向历史目录写文件
conda run -n asset_mujoco_m1_1_rebuild python -m asset_mujoco.contact_diagnostics \
  --package /absolute/new/package --output ./outputs/contact_diagnosis
```

acceptance默认只读使用指定原始GLB，可显式--input；缺失时not_executed/退出2，不达标退出5。它检查compile/native/render及迁移，和test_real_asset_native_failure_is_reported的失败处理回归分开。
diagnostics先重测基线、一致后运行预先保存的小规模A–D参数组；仅修改新副本，输出fixture/逐步trace/summary/hash。诊断执行成功或某实验达标都不改变原始验收状态。正式接触配置仍未更改，下一步建议待用户批准。
最新完整结论：[接触诊断报告](docs/design/M1_1_CONTACT_DIAGNOSIS_REPORT.md)，[本轮机器证据](docs/design/M1_1_CONTACT_DIAGNOSIS_EVIDENCE.json)。

权威设计与历史证据：[设计](docs/design/PHASE2_MUJOCO_DESIGN.md)、[历史M1.1报告](docs/design/M1_1_IMPLEMENTATION_REPORT.md)、[历史M1.1机器证据](docs/design/M1_1_EVIDENCE.json)、[历史M1报告](docs/design/M1_IMPLEMENTATION_REPORT.md)、[编译矩阵](docs/design/visual_mesh_compatibility.md)。历史报告保留，不作为当前成功证据。
