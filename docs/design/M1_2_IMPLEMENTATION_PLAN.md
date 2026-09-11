# M1.2 显式双方配置与受限验收

依据本轮用户已批准方案。起始main@c8690d1，asset_mujoco_m1_1_rebuild，依赖不升级。
默认preserve；engineering_static_v1仅static+hull，solref=[.006,1]、solimp=[.9,.95,.001,.5,2]。
不改摩擦/碰撞位/priority/solmix、基线探针、dt、阈值；无应用力限，不声明材料标定或机器人安全。

- [ ] 配置契约：contracts/cli/config；contact_profiles.py公开工程约定，mjcf导出资产与ground参数，新增公开contact_scene.xml供原生验收读取。tests/integration/test_contact_profiles.py先失败再修复，覆盖默认/受限模式/不匹配实际混合/禁用碰撞位/移动碰撞体。
- [ ] manifest：声明配置来源和使用对象；独立contact_result_manifest保存实际解析结果并绑定physics证据，不循环修改已签名conversion_manifest。旧preserve兼容。
- [ ] 力/冲量/反弹/ground：共享只读接触统计，保持同次求解时间语义；测试解析夹具及冲量独立求和。application_force_limit=not_specified。
- [ ] acceptance新增显式profile参数；先重测preserve，再从原GLB新建candidate包，两份XML及公开验收场景编译、native/full、迁移哈希，任何失败保留。
- [ ] 独立扩展副本：候选基线、dt=.001/.0005、解析切平面、x落点偏移0.05m、质量0.2kg、半径1.2倍、单方参数不匹配；固定非全排列组，事前写计划，2秒时长，记录ground及所有失败。不改变正式dt和探针。
- [ ] 安装新项目代码到指定重建环境，不改依赖；安装源码哈希、pip check、全量回归；重新执行真实验收和扩展并生成机器证据。
- [ ] 对照第一阶段/历史包哈希，更新必要设计、README、deployment_manifest，新M1_2_CONTACT_PROFILE_REPORT.md；分阶段本地提交，输出按现有用户Git策略跟踪，不自动push。
