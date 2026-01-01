# 贡献指南 (CONTRIBUTING)

> 版本: 1.0.0 | 更新: 2024-12-30 | 状态: 生效

## 协作原则

### 单一真源 (Single Source of Truth)
- 所有文档统一存放于 `docs/` 目录
- 唯一入口: `docs/index.md`
- 散落文档必须迁移并留索引

### 文档同步规则
任何以下变更必须同步更新文档:
- 依赖更新 → `docs/changelog/`
- 运行命令变更 → `docs/index.md` + `README.md`
- 配置字段调整 → 相关设计文档
- 目录/模块增删 → `docs/index.md`
- REST/WS 流程改动 → `AGENTS.md`

## Git 工作流

### 启用 Git 钩子
```bash
git config core.hooksPath .githooks
```

### 提交规范 (Conventional Commits)
```
<type>(<scope>): <subject>

[body]

[footer]
```

类型: `feat` | `fix` | `docs` | `refactor` | `test` | `chore`

### PR 要求
1. 关联 `docs/` 链接
2. 填写 Prompt 编号（如有）
3. 验收结果截图/日志
4. 风险与回滚方案

## 代码规范

- Python: PEP 8 + 类型标注
- 注释/日志/文档用中文，变量/函数名用英文
- 禁止硬编码密钥，配置通过 `config/local.json`

## 验证流程

提交前执行: `./scripts/verify.sh`
