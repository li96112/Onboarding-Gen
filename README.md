# Onboarding-Gen — 新人入职文档生成器

> 5 分钟搞定新人入职文档

## 怎么用

```bash
# 在 Claude Code 里直接说
给新人写个项目入职指南

# 或命令行
python3 scripts/onboarding.py -o onboarding.md
```

## 输出示例

```markdown
# my-project — 新人入职指南

## 1. 项目概述
一个全栈 Web 应用...

## 2. 技术栈
语言: TypeScript
框架: Next.js, Tailwind CSS, Prisma
工具: Docker, GitHub Actions, ESLint

## 3. 项目结构
my-project/
├── src/          (47 个文件)
├── prisma/       (3 个文件)
├── public/       (12 个文件)
├── tests/        (15 个文件)

## 4. 环境搭建
### 前置条件
- Node.js 18+
- Docker

### 搭建步骤
git clone ...
npm install
cp .env.example .env
docker-compose up -d

## 5. 常用命令
| 命令              | 说明             |
|-------------------|------------------|
| npm run dev       | 启动开发服务器    |
| npm run build     | 生产构建         |
| npm run test      | 运行测试         |

## 6. 新人优先阅读
1. README.md — 项目概述和搭建说明
2. package.json — 依赖和脚本
3. .env.example — 需要配置的环境变量

## 7. 团队成员
| 贡献者   | 提交次数 |
|----------|---------|
| 张伟     | 234     |
| 李明     | 156     |
```

## 自动分析内容

- 技术栈：从配置文件推断（package.json/go.mod/Cargo.toml 等）
- 框架：React/Vue/Next.js/Django/Flask/FastAPI 等 30+ 框架
- 目录结构：带文件数的项目树
- 开发命令：npm scripts / Makefile targets / manage.py
- 环境变量：从 .env.example 提取 + 猜测用途
- Git 信息：贡献者、最近活动

## 零依赖

Python 3.9+ 标准库 + git CLI
