# SDD ledger — plan: docs/design/M1_2_SCOPE_FIX_PLAN.md

Spec：用户当前完整scope fix指令与后续“继续”。实现者原生执行，最终一次独立审核。
Pre-flight：任务1的ValidationResult由任务2构建，任务3所有入口消费；共同投影由manifest生成，禁止复制聚合逻辑。
Ruling: 沿用用户指定且已确认继续工作的当前main检出和固定工程路径，不创建另一工作树；不覆盖原有未跟踪审核文件。若判断错误的成本是分支隔离不足，已用精确stage和保护快照控制。
Ruling: 用户禁止修改.gitignore且要求保留证据，因此不运行会新建忽略规则/清理工作区的技能脚本；执行日志存本轮/tmp目录、最终复制到新outputs并本地提交。成本是人工维护执行账本。
起始HEAD a4fa889d60ba6370c76bd1493b421239d8f9ad64；原工作区仅PHASE2_M1_1_CODEX_FIX_INSTRUCTIONS.md未跟踪。
只读复现已完成：隔离旧候选包pending输出PHYSICS_VALIDATED，测试approved后FULLY_VALIDATED，真实包未变/pending。

Task 1: complete — 新9项聚合测试RED，19项contracts/review/scoped测试GREEN；旧仅凭哈希裸通过断言按新增契约改为INVALID_EVIDENCE。完整基线119 passed/1 skipped(OSMesa)，尚未宣称实施后完整回归通过。
