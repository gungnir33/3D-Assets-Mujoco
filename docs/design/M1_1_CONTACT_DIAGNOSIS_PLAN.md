# M1.1 验收补强与接触诊断实施清单

依据：本轮用户详细审核指令；保留18章和10项任务，不开展任务8/9。
起始66bd6bc，main，origin=gungnir33/3D-Assets-Mujoco。
环境asset_mujoco_m1_1_rebuild/Python3.10/MuJoCo3.4.0，依赖不升级。
开发显式PYTHONPATH=src；最终安装包复测。历史输入/包只读，新增输出唯一目录。

## 1. benchmark隔离

- [ ] tests/integration/test_benchmark_isolation.py 故障注入：native通过/失败+benchmark异常，native异常，正常benchmark，证据I/O失败。
- [ ] 先运行失败测试；validation.py立即保存physics_native_evidence.json及独立physics层，benchmark_evidence.json单独保存。physics_evidence.json仅汇总，不作为新native证据依赖。
- [ ] pipeline.py不重签native，manifest.py兼容历史证据但新证据不依赖benchmark。持久化失败抛明确EVIDENCE_IO_ERROR且不发布；native异常保存失败并允许独立渲染。
- [ ] 运行故障注入及原分层证据测试，再本地提交。

## 2. 验收入口

- [ ] 重命名test_real_m1为test_real_asset_native_failure_is_reported。
- [ ] tests/integration/test_acceptance_entry.py先断言缺输入返回未执行/非零；独立acceptance.py重新转换GLB，检查compile/native/render/迁移，失败返回5，不用raises或xfail冒充达标。
- [ ] 真实失败也复制新包到唯一迁移目录验证资源；保存acceptance.json，人工/宿主pending。
- [ ] 回归通过后本地提交。

## 3. trace和控制变量

- [ ] tests/integration/test_contact_diagnostics.py：真实解析夹具验证trace时刻、接触点相对速度/力坐标、摘要事件步与文件hash、无接触记录、固定总时长与参数隔离。
- [ ] 独立contact_diagnostics.py，读取新副本physics_native.xml；采用mj_step1→mj_step2，在step1缓存当前位姿/速度/接触，step2读该次求解接触力，明确状态时间与积分后时间，不修改生产验收循环。
- [ ] 基线dt=.002、1000步先对照历史；若明显不一致停止扫描检查版本/输入/加载位置。
- [ ] 执行前写计划：A dt=.001/.0005同2秒；B解析平面匹配首次接触切平面和入射条件；C固定solimp仅timeconst .01/.006；D固定solref，d0=.95及独立dwidth=.99。所有实验副本，不新增强制pair，两个geom使用相同参数以避免混合掩盖控制变量。
- [ ] 每实验存fixture、1000或对应步trace、summary、配置和hash；失败也保留。先查目标版本官方参数语义/混合规则。

## 4. 最终验证与交付

- [ ] 原始GLB新包full验收命令，退出码不得变成成功；基线与扫描结果分开。
- [ ] 安装新代码到本轮允许的独立重建环境、pip check、全量回归和证据迁移检查。
- [ ] 对比第一阶段与历史包hash；新增M1_1_CONTACT_DIAGNOSIS_REPORT.md，更新受影响契约/README，保留历史报告。
- [ ] 明确数值稳定/接触存在/穿透达标独立，提出待批准配置建议，不改正式参数。本地提交后停止，不push。
