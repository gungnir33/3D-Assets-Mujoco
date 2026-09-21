# M1.2 Scope Fix：已批准审核结论的执行清单

依据：用户本轮完整修订要求、随后审核与“继续”。起始main@a4fa889，远端gungnir33/3D-Assets-Mujoco。

采用原生顺序执行，最后一次独立审核。只修报告/状态及其证据，不修改物理条件，不push。

- [x] 任务1：contracts.py增加结构化范围/观察/限制，aggregate仅返回SCOPED_*；tests/unit/test_scoped_validation_states.py先红后绿。缺范围不裸通过，native失败保持FAILED，compile/VISUAL_ONLY不升级。
- [x] 任务2：manifest.py统一从核对后的native/contact_result派生报告；pipeline/validation仅调整报告写入；历史包只读兼容、新缓存矛盾拒绝、文件失效和迁移测试。范围条件引用当前包XML与native字段，不硬编码资产名称或5mm。
- [x] 任务3：cli.convert/report、acceptance与落盘报告复用同一构建路径；acceptance读绑定的主native而非benchmark汇总；测试实际包+命令输出，隔离外观审核不扩大范围。
- [x] 任务4：只重装本项目，验证源码/安装哈希、全量pytest、pip check；原GLB在新目录复测preserve与candidate，不扫描参数；比较几何/XML/参数/历史保护快照，输出M1_2_SCOPE_FIX_REPORT.md并分阶段本地提交。

最终证据：153 passed / 1 skipped（OSMesa）；preserve FAILED，候选 SCOPED_PHYSICS_VALIDATED 且地面观察 failed。独立审核两项必要修复已通过失败回归；人工和宿主均 pending。详见 M1_2_SCOPE_FIX_REPORT.md。

接口：ValidationResult仍是唯一结果类型，aggregate是唯一状态聚合；manifest.checked_report(root)是只读权威构建器。写路径可用内部refresh_report更新新包缓存，不对历史包回填。新缓存的范围投影必须与已有哈希绑定的源证据一致，不将报告/审核加入自身依赖形成循环。

重点回归：缓存篡改、native/contact清单语义矛盾、失效/缺失不冒充not_tested、非企鹅/不同尺寸、图片变化仅使外观批准失效而不抹掉物理事实。真实人工审核保持pending。
