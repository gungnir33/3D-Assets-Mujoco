# 3D Assets → MuJoCo

独立第二阶段转换器。只读使用已有 GLB/OBJ，不 import 第一阶段、不加载 CUDA 模型。
模型、真实输入及 outputs 不提交 Git。MuJoCo、trimesh 等依赖遵循各自许可证；本仓库尚未选择项目许可证，不推定 MIT 授权。

环境：Conda asset_mujoco、Python 3.10.21、MuJoCo 3.4.0。
requirements.lock.txt 为本次独立环境实测锁文件；不要安装到 hunyuan3d 或现有宿主。

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

## 验证和人工审核

```bash
python -m asset_mujoco.cli report ./outputs/package_name
python -B -m pytest -p no:cacheprovider -q
```

compile/physics/full 为请求的自动验证等级。full 自动通过仍为 PHYSICS_VALIDATED，人工审核默认 pending。
人工查看 previews 后才可记录：

```bash
python -m asset_mujoco.cli review ./outputs/package_name \
  --reviewer YOUR_NAME --decision approved \
  --images previews/front.png previews/side.png previews/iso.png
```

审核记录绑定包内容哈希；改变 XML、资源、预览或证据后旧批准失效。report 每次重新判定，不依赖旧总状态。
VISUAL_ONLY 仅 --collision-mode none --validation-level compile，physics=not_applicable。

退出码：0 请求自动等级通过（不等于人工批准）；2 输入错误；3 转换错误；4 XML 编译错误；
5 物理/渲染内容失败；7 渲染后端不可用。失败 staging 保留诊断，未发布包不能作为成功输出。

## 当前边界与故障排查

- M1 示例是举 HY3D 牌子的企鹅；scale=0.5 是演示尺寸，不是对真实物理尺寸的测量。
- hull 包住全部原始顶点，但会填平孔洞；hole_validation=not_tested。
- 单三角形 primitive 暂不支持，不静默增加厚度。平面 shell 仅3.4.0实测可用，3.2.3不识别该属性。
- EGL 已通过；OSMesa 当前 OpenGL 加载不可用，没有修改系统包或驱动。
- 透明、顶点色、额外 UV、压缩、骨骼/morph 和扩展材质严格拒绝；非完整 PBR 等价转换器。
- 非默认宿主 compiler 冲突会报 HOST_COMPILER_CONFLICT，不自动修正宿主。
- CoACD、supplied 碰撞代理、watertight 积分和 HTTP 串联尚未实施。

权威设计与具体证据：[设计](docs/design/PHASE2_MUJOCO_DESIGN.md)、[M1 报告](docs/design/M1_IMPLEMENTATION_REPORT.md)、[编译矩阵](docs/design/visual_mesh_compatibility.md)。
