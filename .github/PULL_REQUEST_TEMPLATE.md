# 拉取请求

## 说明

（用简体中文说明改了什么、为什么改。不要把未执行的安装或行为验证写成通过。）

## 交付清单

- 修改文件：
- 验证命令与实际结果（`python3.12 -m pytest tests/ -q`、`python3.12 scripts/validate-docs.py`）：
- 未运行 / 未验证项目：
- 待用户决定事项：

## 检查

- [ ] 未擅自改变技能名称、20 项集合范围或固定上游基线提交
- [ ] 人读文档与 `skills/<技能名>/SKILL.md` 分开，用户文档不带技能 frontmatter
- [ ] 共享参考仍只有一个所有者，消费者用同级相对路径引用，没有复制副本
- [ ] frontmatter 只用标准字段：8 个用户入口按契约带 `disable-model-invocation: true` 与 `agents/openai.yaml`，按需方法不带宿主开关或宿主文件
- [ ] 目录或技能集合变化时已同步测试与 `provenance/`，没有靠删除检查过关
- [ ] 中英双语镜像（`README.en.md`、`AGENTS.zh-CN.md`）在同一批改动里对齐
- [ ] 提交说明至少包含简体中文
