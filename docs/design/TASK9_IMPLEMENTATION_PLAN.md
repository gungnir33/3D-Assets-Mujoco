# Task 9 Local HTTP Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供一个正式命令，通过第一阶段既有 HTTP API 生成 GLB/OBJ，再由第二阶段转换，并在失败时保留来源与恢复入口。

**Architecture:** 独立参数契约、标准库本机 HTTP 客户端和串联编排；同环境调用现有 ConversionRequest/convert/checked_report，不 import 第一阶段。串联记录在资源包外，复用原分层状态与发布门槛。

**Tech Stack:** Python 3.10 标准库 urllib/http/json/pathlib、现有 pydantic 2.11.7；第二阶段既有依赖版本不变，无 httpx 或 CUDA 依赖。

**Spec:** [TASK8A_9_DESIGN.md](TASK8A_9_DESIGN.md) 第 1–2、5–7 节（用户已确认）；总体设计 [PHASE2_MUJOCO_DESIGN.md](PHASE2_MUJOCO_DESIGN.md)。

状态：已获用户确认并按方式 1 执行；以下保留原规划步骤，实际提交/测试见 [实施报告](TASK9_IMPLEMENTATION_REPORT.md)。模拟 HTTP 不代表已执行真实生成。supplied 串联测试建立在 [8A 实施计划](TASK8A_IMPLEMENTATION_PLAN.md) 的实现上。

## Global Constraints

- 工程 `/home/mcl/workspace/3D-Assets-Mujoco`，origin `https://github.com/gungnir33/3D-Assets-Mujoco.git`；分阶段本地提交，不自动 push。
- 复用新建的唯一 `asset_mujoco_m1_1_rebuild_8a9_<id>` 环境；Python 3.10，按当前锁文件安装；不安装到 hunyuan3d、宿主或原 M1.2 环境。
- 第一阶段源码/环境/Skill/权重/既有资产冻结；不启动生成服务，不执行真实生成 POST。测试只启动临时 loopback 模拟 HTTP 服务，不是新增生产服务。
- 默认 `http://127.0.0.1:8080`；只支持共享本地文件系统、loopback HTTP；无 LAN 上传/下载、认证系统或服务守护。
- HTTP POST 超时1800秒，不重试、不跟随重定向；超时不代表服务端取消，结果状态 unknown。
- 转换默认 static+hull+preserve+full；不自动启用候选、不降低验证等级、不修改接触参数/阈值。
- stdout 单个 JSON、stderr 进度；第一阶段成功和第二阶段失败分别保存。file/metadata 是服务端文件路径，不是资源下载 URL 或内嵌对象。
- 不修改已发布包来追加串联信息，不补签旧证据，不自动人工 approved；不开展 CoACD/质量积分/孔洞专项/真实宿主集成。
- outputs 当前跟踪策略不变；只提交代码、合成测试与公开文档，真实提示词/图片路径/响应日志需显式审查，不做 git add outputs。

## Review Focus

1. 转换参数错误却先花时间生成：Task B1/B3 确保请求前完成格式、尺度、字段与代理路径检查，零 POST。
2. 第一阶段已生成但断连或响应损坏：Task B2/B3 保留 unknown，不自动重试、不宣称没创建 job。
3. metadata 缺失与必需 file 缺失混淆：Task B1/B3 前者警告，后者失败；不拿旧目录最新文件代替。
4. 第二阶段拒绝发布或渲染不可用被包装为串联成功：Task B3/B4 检查退出码、scope、staging 和恢复来源。
5. 串联清单写入失败或日志改变已发布包指纹：Task B3/B4 I/O 注入和包外记录测试，不能伪报持久化成功。

## 文件与接口地图

| 文件 | 职责 |
|---|---|
| 新增 src/asset_mujoco/chain_contracts.py | generation/response/config 解析与预检，禁用未知/冲突字段 |
| 新增 src/asset_mujoco/chain_http.py | loopback URL、受限响应、health/单次POST，结构化传输错误 |
| 新增 src/asset_mujoco/chain.py | CLI、run_chain、来源持久化、转换调用、统一结果/恢复命令 |
| 新增 scripts/chain.py | 导入已安装 asset_mujoco.chain.main 的薄包装，不加 sys.path 绕过安装 |
| 修改 src/asset_mujoco/cli.py | 仅抽取现有转换错误退出码函数供串联复用，不重写原CLI |
| 新增 tests/unit/test_chain_contracts.py | 纯参数、响应、恢复argv测试 |
| 新增 tests/integration/test_chain_http.py / test_chain.py | 模拟网络、真实转换、错误/证据/迁移 |
| 新增 docs/usage/CHAIN.md | 文本/图片/纹理、JSON配置、失败恢复、隐私说明 |

## Task B1：请求和转换预检契约

**Files:** chain_contracts.py、test_chain_contracts.py。

**Interfaces:**

- `read_json(path: Path) -> dict`：UTF-8、对象根、拒绝 NaN/Infinity 和重复键，输入上限1MiB。
- `validate_generation(endpoint: str, payload: dict, base_dir: Path) -> dict`：返回完整缺省值+规范化本地路径的 payload；endpoint 只允许 text/image/texture。
- `load_conversion_config(path: Path | None, output_format: str) -> dict`：允许 ConversionRequest 除 input/output 的设计字段，加上 collision_proxy_path/validation_collision_part；相对代理路径基于配置所在目录。用占位扩展名路径仅做 Pydantic 参数验证，不读取不存在的视觉输入。
- `validate_response(data: dict, expected_format: str) -> tuple[dict,list[str]]`：返回标准来源与 warnings；job_id 非空字符串，file绝对普通文件，type匹配。metadata 字符串缺失/不可读只警告。
- `ChainSettings` dataclass：`endpoint: str, payload: dict, conversion: dict, output: Path, base_url: str, dry_run: bool=False`。

- [ ] **Step 1：写 RED。**

```python
import json
from pathlib import Path
import pytest

def test_defaults_and_prompt_limit(tmp_path):
    from asset_mujoco.chain_contracts import validate_generation
    data = validate_generation('text', {'prompt':'red barrier'}, tmp_path)
    assert data['format']=='glb' and data['texture'] is True
    assert data['seed']==12345 and data['shape_steps']==50
    with pytest.raises(ValueError):
        validate_generation('text', {'prompt':'x'*1001}, tmp_path)

@pytest.mark.parametrize('config', [{'input':'private.glb'}, {'output':'other'},
    {'scale':1,'target_size_m':[1,1,1]}, {'contact_profile':'unknown'}])
def test_invalid_conversion_before_generation(tmp_path, config):
    from asset_mujoco.chain_contracts import load_conversion_config
    path=tmp_path/'convert.json'; path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_conversion_config(path,'glb')
```

增加真实临时文件检查 image/texture 的后缀、100MiB、普通文件；request JSON 图片/mesh 相对路径基于 request 文件父目录，CLI简写基于cwd；配置代理路径绝对化。OBJ输出省略up/尺度在POST前失败；FBX失败。错误数值、空白prompt、额外payload键、metadata对象警告、主file相对/缺失/目录/不匹配扩展名失败。响应只读取文件存在与类型，完整实际格式由转换器再验证，不把扩展名当安全证明。

- [ ] **Step 2：运行失败。** `"$task89_python" -B -m pytest tests/unit/test_chain_contracts.py -q`，确认新模块缺失/断言失败。
- [ ] **Step 3：实现字段与配置白名单。** generation模型独立定义，不能 import 第一阶段schemas。通用字段 texture=True、seed=[0,2^63-1]、format=glb/obj、face_count=[100,1000000]、shape_steps=[1,200]；text要求prompt，image要求image，texture要求mesh/condition_image，extra=forbid；保留第一阶段当前后缀及大小边界。Pydantic 验证后再做非空/本地文件检查。

```python
ALLOWED_CONVERSION = {
    'name','source_up','yaw_deg','scale','target_size_m','scale_mode',
    'body_mode','collision_mode','contact_profile','validation_level',
    'mass','inertia_mode','supplied_inertia',
    'collision_proxy_path','validation_collision_part',
}
if set(config)-ALLOWED_CONVERSION:
    raise ValueError('CHAIN_INVALID_CONVERSION_FIELDS')
request = ConversionRequest(input=Path('preflight.'+output_format),
                            output=Path('preflight-output'), **config)
conversion = request.model_dump(mode='json', exclude={'input','output'})
```

内部返回缺省seed允许保留为12345，但外部转换配置只接受上列键；第一阶段seed独立。supplied代理在发送前至少检查可读、格式及目标索引非负；内容凸性/变换依赖生成结果，实际由8A转换检查，不声称提前证明与未来生成资产匹配。supplied_inertia在配置中使用内嵌已有契约对象，不把它当文件路径猜测。

metadata路径只记录来源且不要求导入其JSON；读取受限且不执行其内容。`read_json` 使用 parse_constant 抛错及 object_pairs_hook 检测重复键；拒绝不是对象的根，不静默覆盖重复 input 字段。`validate_response` 核对 type、file 后缀和普通文件属性，对无法读取的metadata只返回warnings；实际资产坏文件由第二阶段解析失败处理，不重新请求生成。

- [ ] **Step 4：GREEN。** 参数化全部通过；现有 contracts/CLI 回归保持。此任务没有网络调用，测试通过不表示串联已完成。
- [ ] **Step 5：提交。** `feat: validate local generation chaining requests before execution`。

## Task B2：loopback HTTP 与结果未知语义

**Files:** chain_http.py、tests/integration/test_chain_http.py。

**Interfaces:** `validate_base_url(value: str) -> str` 仅语法规范化；`LocalGenerationClient(base_url: str)`；`health() -> dict`；`generate(endpoint: str, payload: dict) -> bytes`；`Phase1Error` 持有 code/message/http_status/details/raw_body/truncated/result_unknown；标准库 timeout health=10、POST=1800。

- [ ] **Step 1：写实际模拟 HTTP 服务 fixture 和 RED。** fixture 只监听127.0.0.1随机空闲端口，handler在 GET /health 返回 JSON ok，在 POST 记录 path/payload 并返回所设 status/body。使用 ThreadingHTTPServer、threading.Thread、contextlib.contextmanager，finally shutdown/server_close/join，不遗留进程。fixture 返回 `(url, calls, set_response)`，set_response接受status/body/headers。

```python
def test_redirect_is_not_followed(mock_server):
    from asset_mujoco.chain_http import LocalGenerationClient, Phase1Error
    url, calls, set_response = mock_server
    set_response(307, b'forward', {'Location':url+'/other'})
    client=LocalGenerationClient(url)
    with pytest.raises(Phase1Error):
        client.generate('text', {'prompt':'box','format':'glb'})
    assert [c['path'] for c in calls] == ['/generate/text']
```

增加422 detail列表、503 error字典、oversized、短body断连、健康检查非JSON/非ok；检查端点和真实请求body。生成200非JSON在本层仍返回原始bytes，由B3保存响应后判断unknown；不在传输层丢掉响应。timeout测试只替换低层open引发TimeoutError并记录调用数，不等待1800秒；另断言传入的生成 timeout 确为1800。错误不触发第二次POST。

- [ ] **Step 2：RED。** `"$task89_python" -B -m pytest tests/integration/test_chain_http.py -q`。
- [ ] **Step 3：实现不可重定向、无代理的本机客户端。**

```python
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
opener = build_opener(ProxyHandler({}), NoRedirect())
```

URL 必须是 http、显式1..65535端口、host为127.0.0.1/localhost/::1、path空或/、无userinfo/query/fragment。localhost在实际请求前getaddrinfo并要求全部地址loopback；dry-run不解析DNS，不声称网络检查已过。禁止自动重试；只拼接白名单endpoint，不能接受payload里的URL。

读取至多1MiB+1用于识别超限，保存最多1MiB和truncated；HTTPError保留code与body，解析detail或error字段，不把它包装成普通连接失败。generate成功返回原始bytes由编排保存再解析。连接中断/超时/200不能解析为有效响应，标result_unknown=True；明确业务HTTP错误保留failed及status，不保证服务端没创建失败job。health失败提示原start_server.sh，不调用脚本。

- [ ] **Step 4：GREEN 并确认客户端未触达8080。** 网络测试只使用fixture动态端口；环境HTTP_PROXY设置为不可达地址仍应访问模拟loopback服务，不修改进程外代理。远程host、重定向到外网和伪localhost明确拒绝。
- [ ] **Step 5：提交。** `feat: add bounded local generation HTTP transport without retries`。

## Task B3：可恢复编排、CLI 和统一退出码

**Files:** chain.py、scripts/chain.py、cli.py、tests/integration/test_chain.py；扩展test_chain_contracts.py。

**Interfaces:** `run_chain(settings: ChainSettings) -> dict`，返回含 exit_code 的报告；`main(argv=None) -> int` 打印单个JSON；`build_recovery_argv(source: Path, conversion: dict, run: Path) -> list[str]`；从cli原错误分支抽取 `conversion_exit_code(error: Exception) -> int`，供cli和chain同用，不改变原分类。

- [ ] **Step 1：先写编排失败测试。** 模拟服务返回真实合成 box GLB 的绝对路径与可选metadata，chain调用真实转换；full使用既有engineering_static_v1，默认preserve失败也真实执行，不mock发布门槛。

```python
def test_phase2_failure_preserves_generation(tmp_path, mock_server):
    import json
    import trimesh
    from asset_mujoco.chain_contracts import ChainSettings
    from asset_mujoco.chain import run_chain
    source=tmp_path/'box.glb'; trimesh.creation.box().export(source)
    url, calls, set_response=mock_server
    response={'job_id':'synthetic-job','file':str(source),'type':'glb',
              'metadata':str(tmp_path/'missing-metadata.json')}
    set_response(200, json.dumps(response).encode(), {})
    settings=ChainSettings(endpoint='text',payload={'prompt':'synthetic box','format':'glb'},
        conversion={'source_up':'z','validation_level':'physics'}, output=tmp_path/'out',
        base_url=url)
    report=run_chain(settings)
    assert report['phase1']['status']=='passed'
    assert report['phase2']['status']=='failed' and report['exit_code']==5
    assert report['phase1']['file']==str(source) and source.is_file()
    assert report['recovery_argv'] and report['phase2']['package']
    assert len([c for c in calls if c['method']=='POST'])==1
```

fixture GET始终独立返回health ok，set_response只控制POST；B2重定向测试无需health调用。补入dry-run零网络零目录、错误配置零POST、两个同名任务不覆盖、metadata警告不阻塞、file缺失不拿其他文件替代、请求JSON和简写互斥、错误argv仍单个JSON/exit2。

- [ ] **Step 2：RED。** `"$task89_python" -B -m pytest tests/integration/test_chain.py tests/unit/test_chain_contracts.py -q`。
- [ ] **Step 3：实现编排状态机。** 预检在创建输出和网络之前完成。非dry-run用mkdtemp(prefix='chain_',dir=parent)；拒绝输出落在输入文件/代理资源目录内部的危险路径，至少禁止串联任务覆盖来源或以来源目录作为最终包。health成功后将规范化request.json可靠保存，再发一次POST。POST成功先保存raw response，再校验/保存phase1=passed与主文件hash，再转换。

报告固定字段：schema_version=1、run_directory、phase1(status=not_run/passed/failed/unknown，job_id/file/type/metadata/warnings/error)、phase2(status=not_run/passed/failed，package/validation/error)、recovery_argv、exit_code。包外chain_manifest和stdout同一对象，phase2.validation为checked_report.model_dump，不自建聚合结论。

```python
request = ConversionRequest(input=source, output=run/'packages', **settings.conversion)
try:
    package = convert(request)
    validation = publication_report(package, request)
except ValidationFailed as error:
    package = error.package
    validation = checked_report(package)
    phase2 = {'status':'failed','package':str(package),
              'validation':validation.model_dump(),
              'error':{'code':error.code,'stage':error.stage,'message':str(error)}}
    exit_code = error.exit_code
```

actual implementation还必须处理checked_report自身不可读时使用error.result并保留核对失败信息，不重新签名。其他异常按共享conversion_exit_code分类（Pydantic/FileNotFound=2、EvidenceIO=3、XML=4、native/render失败=5、不可用=7、其他=3）；共享函数的旧CLI输出字段不变。对泛型转换异常暂存目录由本次唯一packages目录中唯一staging定位，存在多个或没有则如实给diagnostic_parent，不能猜别的任务路径。

build_recovery_argv使用列表而非shell拼接，包含现有CLI位置输入和完整转换参数；supplied惯量在run目录保存recovery_inertia.json并以--supplied-inertia引用；输出指向run/recovery_packages（每次convert仍唯一发布）。不要用字符串执行prompt/文件名。转换seed固定默认值无需新增CLI参数。生成一行展示命令使用shlex.join，仅展示不自动执行。

任何记录写入失败退出3；报告diagnostic_persisted=false与原异常/写入故障链，不声称已落盘。若生成已成功，stdout尽力保留已知job/file，不能把I/O失败改成生成失败后重试。最终清单失败不删除已发布包，但串联整体不声称成功。所有日志/请求/恢复信息在包外，fingerprint发布前后不因chain记录变化。

- [ ] **Step 4：实现两入口及CLI预检。** argparse互斥组prompt/image/mesh/request；condition-image仅mesh必需，生成选项采用默认None以区分显式覆盖和缺省，不允许request+简写参数。parse错误捕获为JSON/exit2；--help正常。`scripts/chain.py` 仅以下内容：

```python
from asset_mujoco.chain import main
if __name__ == '__main__':
    raise SystemExit(main())
```

main只调用run_chain并打印一次JSON；MuJoCo/转换输出若写stdout，用redirect_stdout(sys.stderr)包裹转换调用，不掩盖异常，不改变验证数据。

- [ ] **Step 5：GREEN 与故障矩阵。** 必须覆盖phase1 success + phase2 2/3/4/5/7；真实compile成功和真实full候选成功；原生失败真实执行，其余故障可注入。参数/网络mock不mock发布门槛。I/O故障分别注入request前、response后、最终manifest；断言不多发POST、不丢已知来源、不假报持久化。
- [ ] **Step 6：提交。** `feat: chain local generation and conversion with recoverable results`。

## Task B4：安装包E2E、8A组合与使用交付

**Files:** test_chain.py、docs/usage/CHAIN.md、README.md、docs/design/PHASE2_MUJOCO_DESIGN.md局部、docs/design/TASK9_IMPLEMENTATION_REPORT.md、deployment_manifest.json追加。

**Interfaces:** `python -m asset_mujoco.chain` 与 `python scripts/chain.py` 输出一致；chain_manifest为包外索引，资源包可独立迁移。

- [ ] **Step 1：新增子进程测试。** mock_server临时返回合成GLB，用安装包子进程执行两个入口；text/image/texture三种payload均检查真实HTTP请求字段，模拟返回不代表GPU生成。默认full候选要真实compile/native/render；复制成功包到另目录，MjModel.from_xml_path/mj_forward及checked_report/fingerprint一致。supplied组合至少真实compile，配置代理相对路径及target映射一致；没有真实用户代理时不声称其接触通过。
- [ ] **Step 2：安装包回归。** 复用A1记录的绝对解释器，不依赖当前base Python。命令如下，缺少环境变量时先从执行记录恢复真实路径，不猜名字：

```bash
"$task89_python" -m pip install --no-deps --no-build-isolation .
"$task89_python" -I -B -m asset_mujoco.chain --help
env -u PYTHONPATH "$task89_python" -B -m pytest -p no:cacheprovider -o pythonpath= --import-mode=importlib -q -rs
"$task89_python" -m pip check
```

安装源码逐字节一致再接受结果；记录真实passed/skip和原因。全量包含8A及旧发布/渲染/范围/安全测试。真实第一阶段E2E明确not_executed，不调用8080生成POST；不复用历史测试数。

- [ ] **Step 3：写可复制文档。** 至少给出如下实际参数配置，并注明未指定实际物理尺寸的限制：

```json
{"name":"generated_asset","source_up":"y","yaw_deg":0,"scale":1,
 "body_mode":"static","collision_mode":"hull","contact_profile":"preserve",
 "validation_level":"full"}
```

```bash
python -m asset_mujoco.chain --prompt "A red road barrier" --conversion-config convert.json --output /absolute/output-parent --dry-run
python -m asset_mujoco.chain --image /absolute/input.png --conversion-config convert.json --output /absolute/output-parent
python -m asset_mujoco.chain --mesh /absolute/model.glb --condition-image /absolute/condition.png --conversion-config convert.json --output /absolute/output-parent
```

文档明确：第一条dry-run不生成，后两条执行会发送真实POST，需用户主动选择；服务手动启动，不装/启动第一阶段；1800秒超时unknown；第二阶段失败按recovery_argv恢复，不重新生成。只读引用第一阶段现有启动脚本，不修改其Skill。说明scope/ground/pending与未标定边界，不能只展示最终XML路径。

- [ ] **Step 4：保护检查与提交。** 核对第一阶段/历史输入输出未变，环境版本未升级；仅暂存代码、测试、文档和公开合成证据。提交 `docs: document one-command generation chaining and scoped validation`。停止，不自动push、不做任务8B/8C/8D、不自动宿主集成。

## 自检映射与执行交接

设计5→B1/B3；设计6→B2/B3；设计7测试/文档→B4。Review Focus1由B1/B3覆盖，2由B2/B3覆盖，3由B1/B3覆盖，4由B3/B4覆盖，5由B3/B4覆盖。B2/B3的mock_server为同一个明确约定的测试fixture；不引用不存在的外部服务。

计划与8A分别交付；完成本计划只能声明模拟HTTP加真实转换回归通过，不能宣布真实Hunyuan3D端到端生成已经验证。用户确认计划及执行方式后开始实施。
