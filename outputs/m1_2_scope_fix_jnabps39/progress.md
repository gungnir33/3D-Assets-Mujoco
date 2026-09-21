# SDD ledger — plan: docs/design/M1_2_SCOPE_FIX_PLAN.md

Spec：用户当前完整scope fix指令与后续“继续”。实现者原生执行，最终一次独立审核。
Pre-flight：任务1的ValidationResult由任务2构建，任务3所有入口消费；共同投影由manifest生成，禁止复制聚合逻辑。
Ruling: 沿用用户指定且已确认继续工作的当前main检出和固定工程路径，不创建另一工作树；不覆盖原有未跟踪审核文件。若判断错误的成本是分支隔离不足，已用精确stage和保护快照控制。
Ruling: 用户禁止修改.gitignore且要求保留证据，因此不运行会新建忽略规则/清理工作区的技能脚本；执行日志存本轮/tmp目录、最终复制到新outputs并本地提交。成本是人工维护执行账本。
起始HEAD a4fa889d60ba6370c76bd1493b421239d8f9ad64；原工作区仅PHASE2_M1_1_CODEX_FIX_INSTRUCTIONS.md未跟踪。
只读复现已完成：隔离旧候选包pending输出PHYSICS_VALIDATED，测试approved后FULLY_VALIDATED，真实包未变/pending。

Task 1: complete — 新9项聚合测试RED，19项contracts/review/scoped测试GREEN；旧仅凭哈希裸通过断言按新增契约改为INVALID_EVIDENCE。完整基线119 passed/1 skipped(OSMesa)，尚未宣称实施后完整回归通过。

Task 2: complete — scope投影、历史只读、缓存版本防删除、跨JSON矛盾检查；阶段提交7519f3c。
Task 3: complete — convert/report/acceptance统一报告，失败CLI保留报告，acceptance读取绑定native；27项定向通过。首次安装全量146 passed/1 skipped。
Final review: 只读独立审核发现缓存可掩盖native failed及fixture语义缺口，新增7项RED后修复；39项定向GREEN，提交8db4eef。report失败/证据问题统一exit5，人工pending不影响成功exit0。审查无物理参数变更。
Task 4: 最终安装全量153 passed/1 skipped(OSMesa loader)，最终代码两组原GLB复测完成，preserve exit5、candidate exit0；迁移和各入口一致；人工/host pending。输出目录outputs/m1_2_scope_fix_jnabps39。文档/证据归档及最终本地提交收尾中，不push。
Ruling: 独立重渲染不要求字节相同；最初过严的预览哈希比较触发断言后，检查得到单通道最大差1。几何、原贴图、XML和渲染配置仍严格逐字节相同；预览差异单列，不改原验收标准或历史输出。
