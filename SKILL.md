---
name: onboarding-gen
description: Analyze any project and auto-generate a new engineer onboarding document — tech stack, structure, setup steps, scripts, env vars, key files, team, recent activity. Zero dependencies.
metadata: {"openclaw":{"emoji":"🎓","requires":{"bins":["python3","git"]},"homepage":"https://github.com/li96112/Onboarding-Gen"}}
---

# Onboarding-Gen — 新人入职文档生成器

> 5 分钟搞定新人 onboarding 文档

分析项目的文件结构、技术栈、依赖、脚本、环境变量、git 历史，自动生成一份完整的新人入职指南。

## Agent 调用方式

```bash
# 分析当前项目
python3 {baseDir}/scripts/onboarding.py -o /tmp/onboarding.md

# 分析指定目录
python3 {baseDir}/scripts/onboarding.py -d /path/to/project -o /tmp/onboarding.md

# 同时导出分析 JSON
python3 {baseDir}/scripts/onboarding.py --json /tmp/analysis.json -o /tmp/onboarding.md
```

### 触发关键词
- "生成入职文档" / "新人 onboarding" / "项目介绍"
- "Onboarding-Gen"
- "给新人写个指南" / "项目怎么跑起来"
- "这个项目用了什么技术" / "怎么搭开发环境"

## 自动分析内容

| 分析项 | 说明 |
|--------|------|
| **Tech Stack** | 语言 / 框架 / 工具 / 数据库（从 config 文件推断） |
| **Project Structure** | 目录树 + 每个目录文件数 |
| **Setup Steps** | 根据技术栈生成 clone + install + env 步骤 |
| **Scripts** | 从 package.json / Makefile / manage.py 提取所有可用命令 |
| **Env Vars** | 从 .env.example 提取 + 猜测每个变量的用途 |
| **Key Files** | 推荐新人优先阅读的文件列表 |
| **Team** | git shortlog 贡献者列表 |
| **Recent Activity** | 最近 10 条 commit |
| **Tips** | 新人上手建议 |

## 支持的技术栈检测

JavaScript/TypeScript, Python, Go, Rust, Java, Dart/Flutter, Ruby, PHP, Swift

框架: React, Next.js, Vue.js, Nuxt.js, Angular, Svelte, Express, Fastify, NestJS,
Django, Flask, FastAPI, Electron, Tailwind, Vite, Webpack...

工具: Docker, GitHub Actions, GitLab CI, ESLint, Prettier, Vercel, Fly.io, Netlify...

## 零依赖

纯 Python 标准库 + git CLI。

## 文件说明

| 文件 | 作用 |
|------|------|
| `scripts/onboarding.py` | 核心引擎：项目分析 + 技术栈检测 + 文档生成 |
