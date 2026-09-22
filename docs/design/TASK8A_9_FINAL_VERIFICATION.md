# 任务 8A + 9 最终验证与交接

日期：2026-09-21–22。按批准计划方式 1 顺序执行，最后一次独立整体审核及一次修复通道；仅本地提交，不 push。

## 版本、范围与入口

- 起点：`b0419beb8e86a3663bd5ee09df755c861f99d6e7`。
- 最终代码：`6310ea0faed1eafe0932f2b884a05cfed284f8a1`，分支 main。
- origin：`https://github.com/gungnir33/3D-Assets-Mujoco.git`。
- 8A：受限读取 supplied 凸代理、实例/分量验证、共享视觉规范化矩阵、多部件导出、指定碰撞部件验收与证据绑定。
- 9：独立请求契约、本机 HTTP 单次生成、真实转换器调用、失败来源保留和无再次生成的恢复命令。
- 使用：[代理说明](../usage/COLLISION_PROXY.md)、[一个命令生成并转换](../usage/CHAIN.md)。
- 阶段记录：[8A](TASK8A_IMPLEMENTATION_REPORT.md)、[9](TASK9_IMPLEMENTATION_REPORT.md)。当前总体规格仍为 PHASE2_MUJOCO_DESIGN.md，增补为 TASK8A_9_DESIGN.md。

阶段提交依次：6c91ffb、873dcd0、db42a76、b8e4f25、f12b501、d8b2f1b、9461519、7c3d9f5；最后修复 6310ea0。文档自身提交不写入本文。

## 独立审核与修复

独立审核发现 0 Critical、3 Important，全部经失败回归复现后最小修复：

| 问题 | 修复 | 本轮证据 |
|---|---|---|
| HTTP 错误正文中断被误归为本地 I/O，丢失已发 POST 状态 | chain_http.py 捕获错误正文读取异常，保留 HTTP 状态、部分响应、原因和 unknown，不重试 | timeout/incomplete 两例 RED→GREEN，退出 6、503 保留 |
| 重复/非流形面在拒绝前构造平方级邻接 | collision_proxy.py 在边出现第三个面时拒绝，线性遍历分量起点 | 1000 重复面 RED 峰值 37,476,642 bytes；修复后通过 <12 MiB 回归 |
| 加载器强制整数化掩盖浮点面索引 | asset_decode.py 在 Trimesh 构造前验证源索引类型、形状、范围 | 真二进制畸形 GLB RED→GREEN，不用下游伪对象代替 |

对应 tests/integration/test_chain_http.py、test_collision_proxy.py。新增 4 项先得到 4 failed，修复后 4 passed（0.26 s）；最终全量见下。README 过期的“supplied/HTTP 未实施”描述同步修正，无遗留 Minor。

## 最终安装包验证

独立环境：

`/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild_8a9_20260921_5Ibcv05j`

Python 3.10.21、MuJoCo 3.4.0、trimesh 4.7.4、numpy 2.2.6、scipy 1.15.3、pydantic 2.11.7、pytest 8.4.1。27 项锁文件版本逐项匹配，无升级；25 个安装源码模块与仓库逐字节一致。

在仓库根目录，使用上述环境的 python：

```bash
python -m pip install --no-deps --no-build-isolation .
env -u PYTHONPATH python -B -m pytest -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs
python -m pip check
```

安装退出 0；完整回归 **298 passed, 1 skipped，63.59 s，退出 0**；pip check：`No broken requirements found.`。pip 仅提示当前沙箱不能写用户 cache，不影响依赖检查。

唯一 skip：OSMesa OpenGL loader 的 glGetError 不可用；未改驱动，EGL 原生渲染通过。[完整最终 pytest 输出](evidence/TASK8A_9_FINAL_PYTEST.txt)。

测试包含受限资源读取、法线/材质、发布门槛、范围报告、碰撞负向、证据失效、迁移、合成资产真实 MuJoCo 编译/forward/接触/渲染；串联覆盖两个安装入口和三种端点。HTTP 仅临时 loopback 模拟服务器，未调用第一阶段真实生成服务。模拟 HTTP 成功不能称为真实 GPU 生成 E2E 通过。

## 保护与未验证边界

前后检查一致：

- 第一阶段 HEAD：`c78d96ea41a692917918af3d9ce4d3821be64f2b`，工作区干净且未改变。
- 原始 GLB SHA256：`12f1ed66a874efbdb3c350d819c1f6e076de469e7dc191d236de82073fdd2e12`。
- 已跟踪 outputs/example_outputs 中 1,580 个历史文件哈希不变。
- requirements.lock.txt、pyproject.toml、.gitignore、contact_profiles.py 相对起点无变化。
- 原有未跟踪 PHASE2_M1_1_CODEX_FIX_INSTRUCTIONS.md 保留且未提交。

未修改旧环境、第一阶段、宿主或驱动；未转换真实企鹅 GLB、未发送真实生成 POST。用户代理配准/真实孔洞 not_tested，appearance_review=pending，host_integration=pending，robot_contact_safety=not_validated，application_force_limit=not_specified。默认 preserve/full 不变；engineering_static_v1 仍仅 static+hull 显式可选，历史地面失败不改写。

本次软件实现与回归完成，不表示整个任务 8、第二阶段、用户真实资产或机器人安全验收完成。

## 执行裁决与剩余工作

1. 沿用已批准 main，不另建 worktree；精准暂存以保护用户修改，代价是不具备额外工作树隔离。
2. 临时账本/阶段日志在 /tmp/task8a9-5Ibcv05j；不为技能脚本修改 .gitignore。最终证据已归档；保留临时诊断供追溯，但其生命周期不保证持久。
3. 探针位置数学断言允许 1e-14 m 舍入误差，替代相差约 2e-16 的浮点精确相等；未改生产阈值或工况。
4. 真实 Hunyuan3D POST 未执行，须用户单独批准；风险是尚无真实生成到 XML 的端到端证据。
5. 无用户真实代理，配准、孔洞、外观不推定通过；风险是合成测试不能保证实际资产适用。
6. 宿主、安全和材料标定不在授权范围，必须独立验证。
7. 按既有不 push 的决定保留本地 main 和环境；不启动 CoACD、质量积分或其他任务 8 扩展。无延后 Minor 修复项。

下一步由用户选择：先提供真实代理进行验证，或批准一次真实生成串联测试。此处仅列待验证事项，不自动执行。
