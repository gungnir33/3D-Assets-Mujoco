# 一个命令：描述/图片 → GLB → MuJoCo XML

任务 9 通过本机 HTTP 调用第一阶段，随后调用本项目转换器；不 import 第一阶段包、不加载 CUDA、不修改其环境或资产。要求两个服务共享本地文件系统。

## 安装与服务准备

本次已验证环境：

```bash
conda activate asset_mujoco_m1_1_rebuild_8a9_20260921_5Ibcv05j
cd /home/mcl/workspace/3D-Assets-Mujoco
python -m asset_mujoco.chain --help
```

换机器部署时使用独立 Python 3.10 环境，按 requirements.lock.txt 安装，再 `python -m pip install --no-deps --no-build-isolation .`。不要安装到 hunyuan3d 或现有宿主环境。

第一阶段服务需用户自行启动；本命令不会后台启动或遗留服务：

```bash
/home/mcl/workspace/3D-Assets-Agent/scripts/start_server.sh
```

缺服务时返回 LOCAL_3D_SERVER_NOT_RUNNING 和启动提示，不会自动发送后续生成。默认地址 `http://127.0.0.1:8080`；只允许 HTTP、显式端口及 127.0.0.1/localhost/[::1]，不使用环境 HTTP 代理，不跟随重定向。

## 转换配置与一条生成命令

新建 `convert.json`：

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

scale=1 只表示应用用户倍率，不能证明真实物理尺寸。已知尺寸可使用 target_size_m（三轴 X/Y/Z），与 scale 互斥；OBJ 必须显式提供 source_up 和 scale/target_size_m。默认 preserve 可能因穿透超限失败，不会自动改成工程候选或降低等级。

先预检（不联网、不解析 DNS、不创建任务目录）：

```bash
python -m asset_mujoco.chain --prompt "A red road barrier" \
  --conversion-config convert.json --output /absolute/output-parent --dry-run
```

以下命令由用户主动执行时会发送一次真实生成 POST，可能耗时较长：

```bash
# 描述 → 模型 → XML
python -m asset_mujoco.chain --prompt "A red road barrier" \
  --conversion-config convert.json --output /absolute/output-parent

# 图片 → 模型 → XML
python -m asset_mujoco.chain --image /absolute/input.png \
  --conversion-config convert.json --output /absolute/output-parent

# 已有 mesh + 条件图 → 纹理模型 → XML
python -m asset_mujoco.chain --mesh /absolute/model.glb --condition-image /absolute/condition.png \
  --conversion-config convert.json --output /absolute/output-parent
```

可设置 --seed、--face-count、--shape-steps、--no-texture、--format obj；默认 12345/40000/50/带纹理/GLB。prompt 最多 1000 字符。图片支持 PNG/JPG/JPEG/WEBP，输入文件遵循第一阶段 100 MiB 上限。

工程候选只在用户明确将配置改为 `contact_profile=engineering_static_v1` 时采用，且仅 static+hull。它不是测得材料参数，只支持交付工况内的受限结论；后续地面观察、外观、宿主和机器人安全仍独立报告。

## JSON 请求和脚本入口

```json
{"endpoint":"image","payload":{"image":"input.png","texture":true,"seed":12345,"format":"glb"}}
```

```bash
python scripts/chain.py --request /absolute/request.json \
  --conversion-config /absolute/convert.json --output /absolute/output-parent
```

请求文件内相对路径以请求文件父目录为基准；命令行相对路径以当前目录为基准；代理路径以转换配置父目录为基准。`--request` 不可与 prompt/image/mesh 或 seed 等简写覆盖参数混用。两入口共用同一实现，不修改 sys.path。

转换配置不能包含 input/output 或未知键；不支持 decompose/watertight。supplied 代理用法见 [COLLISION_PROXY.md](COLLISION_PROXY.md)，它必须匹配新资产原始坐标，不能假定生成模型自动匹配已有代理。

## 结果、失败与恢复

每次建立唯一 `output/chain_<id>/`，包含 request.json、phase1_response.json、chain_manifest.json 和 packages/。`--output` 是父目录，不覆盖已存在任务。文件可能包含提示词/本机路径，提交前检查隐私；本工具不自动提交文件。

stdout 是一个 JSON，含独立 phase1/phase2 状态、第二阶段完整受限 validation、包路径、恢复 argv 和退出码。成功 XML 在 phase2.package 下。metadata 是第一阶段文件路径，不是内嵌对象；缺失只警告。生成资源保持原位置，不复制覆盖第一阶段 job。

第一阶段 POST 最多等待 1800 秒且不自动重试。超时、断连、无法确认的成功响应标记 unknown，不表示服务取消或没有生成 job；请先定位服务端结果。

第二阶段失败时保留 phase1=passed、原文件哈希、staging 诊断及 recovery_argv/recovery_command。复制恢复命令执行只会重新转换原文件，不再次生成。若参数需要更改，可据此编辑转换命令。

退出码：0 请求等级通过（外观可以 pending）；2 参数/输入；3 转换或持久化；4 XML 编译；5 物理或渲染内容；6 第一阶段 HTTP/响应/结果未知；7 full 渲染不可用。compile 成功不表示 physics 成功。SCOPED_PHYSICS_VALIDATED 只对应报告中指定工况，不能解读为整个场景或机器人安全通过。

## 本轮实测范围

模拟 HTTP + 真实 MuJoCo 转换/渲染/迁移已测；真实 Hunyuan3D HTTP 生成本轮未执行。不要把模拟服务测试理解成 GPU 生成端到端已验证。详见 [任务 9 实施报告](../design/TASK9_IMPLEMENTATION_REPORT.md)。
