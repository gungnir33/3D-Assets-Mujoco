# M1.2 发布与异常状态局部修复计划

> 原生顺序执行，使用 executing-plans；用户已授权直接修改，无需逐项审核。

Goal：Python convert在请求层和证据不满足时拒绝发布；渲染异常不覆盖已验证的物理范围。
Spec：本轮用户完整“M1.2 发布门槛与渲染异常状态同步”要求。未发现同名补充指令或复现ZIP。
Architecture：沿用checked_report/refresh_report、ValidationResult、EvidenceIOError和atomic_publish；只在现有流程同步完整结果、持久化失败并增加末端准入，不改变物理算法。
Tech Stack：独立asset_mujoco_m1_1_rebuild，Python3.10.21 / MuJoCo3.4.0 / Pydantic2.11.7，依赖不升级。

## 全局约束

固定仓库与现有main，不回退，不覆盖用户文件；第一阶段/宿主/历史包只读；不改任何物理参数、必需接触对或地面非必需定位；不改.gitignore、不push、不进入任务8/9。保留当前18章/10任务。

## Review Focus

1. 正常native结束但渲染后端不可用：scope/ground/profile不能被旧缓存覆盖（任务1）。
2. 渲染失败后诊断写入也失败：原错误与I/O错误同时可见，不伪称持久化（任务1）。
3. 哈希核对产生scope矛盾而physics仍passed：Python核心拒绝，不能靠CLI兜底（任务2）。
4. 请求full但render未完成：聚合显示物理局部通过不能授权发布（任务2）。
5. compile-only和VISUAL_ONLY不要求物理/人工批准；候选地面非必需失败不阻塞（任务2/3）。

## 任务1：完整状态同步和异常持久化

文件：pipeline.py、manifest.py（失败渲染证据契约的最小适配）、必要的contracts/cli/acceptance；测试tests/integration/test_render_failure_state.py。

- [ ] 真实小箱体+engineering_static_v1跑native，仅注入render_package异常和发布spy。先断言磁盘/checked_report均physics passed、scope verified，unavailable时CLI7、failed时FAILED；assert not published且staging存在。
- [ ] 运行定向pytest，记录旧摘要冲突失败。
- [ ] native完成后采用持久化完整result；异常仅更新render，绑定失败证据，保留原错误与目录。诊断I/O抛EvidenceIOError并保留因果，不掩盖初始render异常。
- [ ] 测试异常矩阵和acceptance不冒充通过，提交本地修复。

## 任务2：统一发布门槛

文件：pipeline.py；测试tests/integration/test_publication_gate.py。

- [ ] 渲染后故障注入修改真实contact结果、去掉必需证据层/资源；不得mock门槛或原native。记录convert错误发布的失败回归。
- [ ] `result=checked_report(staging)`后按请求compile/physics/full/visual检查必需层、scope、证据问题；失败抛结构化ValidationFailed（分类/阶段/原因/result/package），成功才atomic_publish，保持原并发防覆盖实现。
- [ ] 每项拒绝都断言无成功目录、未调用publish、staging保留和准确原因；正常compile/visual/physics/full均真实运行。
- [ ] 定向及完整源码回归，本地提交。

## 任务3：安装、真实复测、审核和报告

- [ ] `python -m pip install --no-deps --no-build-isolation .`仅重装本项目；逐文件校验site-packages后运行完整pytest与pip check。
- [ ] 原GLB两种profile在新唯一目录各跑一次acceptance，保留原请求，候选迁移并核对分层报告。保存新数值、状态、命令、退出码和保护快照。
- [ ] 一次独立只读整体审核；必要问题先失败测试再最小修复，不重复参数诊断。
- [ ] 更新README、权威设计局部契约、M1_2_PUBLICATION_STATE_FIX_REPORT.md和部署记录，保留历史；分阶段本地提交后停止。

定向命令：`env PYTHONPATH=src /home/mcl/anaconda3/envs/asset_mujoco_m1_1_rebuild/bin/python -B -m pytest -p no:cacheprovider -q tests/integration/test_render_failure_state.py tests/integration/test_publication_gate.py`；先观察预期失败，再达到全绿。
