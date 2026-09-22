# 自备凸碰撞代理（任务 8A）

全项目能力、环境、已有模型转换和模块索引见 [完整使用手册](USER_MANUAL.md)。本文专注 supplied 代理。

视觉输入和代理必须共享原始世界坐标、单位与 up-axis。代理先展开自身节点变换，再应用视觉确定的全局矩阵，不会自动配准或重新居中。不要传入已经独立归一化的代理。

每个节点/geometry 实例按共享边拆成闭合凸部件。仅在代理副本内精确焊接同位置顶点，容差 0；不跨实例或材质 primitive 拼接，不修改视觉 UV/法线。开放、平面、逆向、重复面、非凸或数值无法判定的部件均拒绝，不自动修复、简化或取凸包。预算：最多 32 部件、总 50,000 三角面、每部件 10,000 顶点。

## 先编译并检查部件映射

在安装本项目的独立 Python 3.10 环境执行：

```bash
python -m asset_mujoco.cli convert /absolute/visual.glb \
  --output /absolute/new-output-parent --source-up y --scale 1 \
  --collision-mode supplied --collision-proxy /absolute/proxy.glb \
  --validation-level compile
python -m asset_mujoco.cli report /absolute/returned-package
```

`conversion_manifest.json` 的 `collision_proxy.parts` 按节点名、geometry、原始最小面索引排序，列出资源、来源、边界框和检查记录。XML 使用 `asset_collision_000` 等独立 geom；所有部件均绑定证据，不仅选定部件。

## 显式选择验证对象

```bash
python -m asset_mujoco.cli convert /absolute/visual.glb \
  --output /absolute/new-output-parent --source-up y --scale 1 \
  --collision-mode supplied --collision-proxy /absolute/proxy.glb \
  --validation-collision-part 0 --validation-level full
```

physics/full 必须选择零起始索引。static 必需对为选定部件与 probe，free 为选定部件与 ground。探针仍按视觉尺寸和原规则放置，不会自动瞄准部件；其他部件接触不能替代目标。`SELECTED_COLLISION_PART_ONLY` 限定结论，`per_collision_part` 仅记录其他部件观察。compile 不是物理验收通过。

默认仍为 preserve/full；engineering_static_v1 仅支持 static+hull，不能用于 supplied。原生穿透超限会失败并保留 staging，不为代理调参。free 仍必须提供质量及已有 box_approx/supplied 惯量；代理 geom mass=0，不参与质量积分。

当前未提供真实用户代理，验证基于合成资产。`collision_fidelity=user_supplied` 不保证包住视觉或孔洞可通过；`hole_validation=not_tested`。人工外观、真实宿主与机器人安全不因代理编译通过而升级。
