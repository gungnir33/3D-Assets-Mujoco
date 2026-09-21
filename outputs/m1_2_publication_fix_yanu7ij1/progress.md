# SDD ledger — plan: docs/design/M1_2_PUBLICATION_STATE_FIX_PLAN.md

Base 75b7a7a，main；只有用户原有审核文件未跟踪；环境与代码版本已核对，before.json记录保护哈希。
Pre-flight：任务1的完整状态与异常类型由任务2门槛/CLI消费；复用唯一报告，不创建第二聚合。任务3必须安装最终代码。
Ruling: 沿用用户指定并持续授权的现有main/工程目录，不新建worktree；精准暂存与保护快照避免混入用户修改，代价是无分支隔离。
Ruling: 用户禁止改.gitignore且要求保留证据，使用/tmp独立账本并最终归档，不运行会改忽略规则/删工作区的技能脚本；代价是手工维护账本。
任务1/2：先分别复现A发布旁路及B渲染异常缓存过期，再按用户顺序先修同步后补门槛。
Task 1: complete — 实际锁定环境基线153 passed/1skip；两路径初始8项RED。完整result同步、结构化渲染错误、失败证据和双重I/O因果后，render/benchmark/layered 21 passed。A门槛测试尚待任务2，未宣称全量完成。
Task 2: complete — 门槛矩阵先10 RED/4GREEN，扩展不可读报告和成功渲染证据I/O后13RED/13GREEN；补末端只读checked_report准入，27项定向GREEN。全量源码179 passed/1skip（后加1项CLI I/O矩阵将于安装完整套件再跑）。atomic_publish实现未改。
Task 3: installing current project only; full installed suite and unique-output real checks next. Final review required once, no per-task subagents.
Final review: 独立审核发现1项Important：绑定render状态not_run/未知时跳过校验，沿用缓存passed可发布。3项RED（not_run/unexpected/null）复现后，改为not_run+invalid_bound_layer_status，拒绝继承缓存通过。无其他Critical/Important或deferred minor。
Final: Ruling: 审核未重复全量/真实复测及未扩审物理算法/并发发布/第一阶段宿主 — 主执行独立完成前两项，后四项按用户边界保持冻结；代价是不能据本轮宣称宿主或物理算法全面验收。
Final: fixed 非法绑定层状态继承缓存passed — test_nonterminal_bound_render_status_never_inherits_cached_pass三项RED→GREEN，最终30项定向通过。
Task 3: complete — 最终f1b91b0安装包183 passed/1skip(OSMesa)、pip check通过、19个源码与安装文件匹配。真实2profile和5类真实native后的故障注入输出outputs/m1_2_publication_fix_yanu7ij1；所有fault均publish调用0，原1185个输出未变。文档已更新，最终仅本地归档提交，不push。
