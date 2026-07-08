# Git 开发流程规范

## 仓库

```text
https://github.com/hardyai716/human_review_agent_skill_hub.git
```

## 分支

- `main`：稳定主分支。
- `feat/*`：功能开发。
- `docs/*`：文档调整。
- `chore/*`：目录、脚本、配置调整。

## 提交前检查

- 确认没有提交密钥、Token、真实线上数据明细。
- 确认 `docs/implementation_plan.md` 与实际目录保持一致。
- 如果修改场景包，同步检查 Skill 内调试快照是否需要更新。
- 如果修改 Skill 行为，同步更新调试样例或检查清单。

## 首次接入

```text
git init
git remote add origin https://github.com/hardyai716/human_review_agent_skill_hub.git
git add .
git commit -m "chore: initialize human review agent skill hub"
git branch -M main
git push -u origin main
```

如果 push 失败，先确认 GitHub 认证和网络，再重试。
