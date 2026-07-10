# 通用约束

本发布包面向 `efficiency-label-rate` 场景，只用于打标率低效治理的调试态和发布态运行。

## 唯一事实来源

- 根目录场景包是业务事实来源。
- 本发布包由打包脚本生成，不手工维护业务口径。
- `package_manifest.json` 记录每个文件的来源路径和 sha256。

## 安全边界

- 默认 `debug_only`。
- 只读优先。
- 不真实通知、不拉群、不写线上状态。
- 真实外部动作必须由 calling_agent 或 external_executor 完成人工确认。
