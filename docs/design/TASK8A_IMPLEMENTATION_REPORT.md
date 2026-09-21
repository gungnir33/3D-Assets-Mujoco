# 任务 8A 实施记录

2026-09-21，起点 `b0419beb8e86a3663bd5ee09df755c861f99d6e7`，main；origin 保持 `https://github.com/gungnir33/3D-Assets-Mujoco.git`。用户原有未跟踪审核文件未修改或提交，不自动 push。

实现提交：`6c91ffb` 受限解码与凸性检查，`873dcd0` 多部件导出和编译证据，`db42a76` 显式目标接触及证据绑定。

## 实现与验证

- asset_decode.py 抽取原受限读取，scene.py 保留视觉变换和法线算法。
- collision_proxy.py 按实例精确焊接/分组，检查拓扑、朝向、正体积、凸面支持与独立凸包体积；凸包仅用于核对，不替换输入。
- contracts/cli/mjcf/pipeline 接入 supplied；collision_scope 为声明和 native 的唯一部件映射来源。
- validation/contact_statistics/manifest 绑定全部代理资源，仅所选接触对为必需；free 显式惯量不变，力统计明确作用部件。
- 首批测试 RED 10 failed（模块不存在）→ GREEN 10 passed；多部件编译 RED 2 failed→通过；native RED 4 failed→通过。
- 源码阶段全量：205、215、225 passed；各 1 skipped，原因均为 OSMesa OpenGL loader unavailable，EGL 路径通过。
- 安装包全量：225 passed, 1 skipped，42.59 s；随后新增安装包 CLI full/report 用例：1 passed，1.50 s。二者不冒充一次完整运行。
- 包含该新增用例后的最终安装包全量：226 passed, 1 skipped，43.77 s，日志 a4-final.log。
- 测试位置：tests/integration/test_collision_proxy.py、test_proxy_evidence.py，包含资源越界读取前拒绝、多实例镜像、预算、非法部件、真实 XML forward/迁移、碰撞位清零/移走、非目标不能替代目标、映射语义冲突及 free 惯量。

新独立环境 `/home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild_8a9_20260921_5Ibcv05j`，Python 3.10.21；MuJoCo 3.4.0、trimesh 4.7.4、numpy 2.2.6、scipy 1.15.3、pydantic 2.11.7。按原 requirements.lock.txt 安装，无依赖升级；项目 `pip install --no-deps --no-build-isolation .`。pip check 无冲突；22 个安装模块与源码逐字节一致。

日志及保护清单暂存 `/tmp/task8a9-5Ibcv05j/`；阶段保护核对：第一阶段 HEAD/status、原 GLB SHA256 以及 1,580 个已跟踪历史输出文件哈希未变。旧环境未安装项目或依赖。

## 边界与裁决

沿用获批工程 main，未创建额外 worktree；技能账本放临时目录，避免修改 .gitignore。探针位置断言采用绝对误差 1e-14 m，仅容纳二进制浮点舍入，不改变生产条件和穿透阈值。

所有新增资产测试为合成代理，不是用户真实代理验收。原生 preserve 仍可能穿透超限；失败处理通过不是物理达标。未执行 CoACD、质量积分、孔洞专项、第一阶段生成或真实宿主集成。appearance_review=pending、host_integration=pending；整个任务 8 尚未完成。

使用入口：[COLLISION_PROXY.md](../usage/COLLISION_PROXY.md)。任务 9 独立继续，不复用代理测试冒充真实生成串联。
