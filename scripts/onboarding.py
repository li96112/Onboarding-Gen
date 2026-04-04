#!/usr/bin/env python3
"""Onboarding-Gen: Analyze a project and generate new engineer onboarding docs.

Scans: file structure, tech stack, dependencies, scripts, git history,
README/config files to produce a comprehensive onboarding document.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def run_git(args, cwd=None):
    result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
    return result.stdout if result.returncode == 0 else ""


def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.stdout if result.returncode == 0 else ""


# ---------------------------------------------------------------------------
# Project analyzers
# ---------------------------------------------------------------------------

def detect_tech_stack(project_dir):
    """Detect technology stack from config files."""
    p = Path(project_dir)
    stack = {"languages": [], "frameworks": [], "tools": [], "databases": []}

    # Language detection
    indicators = {
        "package.json": ("JavaScript/TypeScript", "language"),
        "tsconfig.json": ("TypeScript", "language"),
        "requirements.txt": ("Python", "language"),
        "setup.py": ("Python", "language"),
        "pyproject.toml": ("Python", "language"),
        "Pipfile": ("Python", "language"),
        "go.mod": ("Go", "language"),
        "Cargo.toml": ("Rust", "language"),
        "pom.xml": ("Java", "language"),
        "build.gradle": ("Java/Kotlin", "language"),
        "Gemfile": ("Ruby", "language"),
        "composer.json": ("PHP", "language"),
        "pubspec.yaml": ("Dart/Flutter", "language"),
        "Package.swift": ("Swift", "language"),
    }

    for file, (tech, category) in indicators.items():
        if (p / file).exists():
            stack[f"{category}s"].append(tech)

    # Framework detection from package.json
    pkg_path = p / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            fw_map = {
                "react": "React", "next": "Next.js", "vue": "Vue.js",
                "nuxt": "Nuxt.js", "@angular/core": "Angular",
                "svelte": "Svelte", "express": "Express.js",
                "fastify": "Fastify", "koa": "Koa",
                "nestjs": "NestJS", "@nestjs/core": "NestJS",
                "electron": "Electron", "tailwindcss": "Tailwind CSS",
                "vite": "Vite", "webpack": "Webpack",
                "jest": "Jest", "mocha": "Mocha", "vitest": "Vitest",
                "prisma": "Prisma", "typeorm": "TypeORM",
                "mongoose": "Mongoose", "sequelize": "Sequelize",
            }
            for dep, fw in fw_map.items():
                if dep in deps:
                    stack["frameworks"].append(fw)
        except:
            pass

    # Python framework detection
    req_files = [p / "requirements.txt", p / "Pipfile"]
    for req_path in req_files:
        if req_path.exists():
            try:
                content = req_path.read_text()
                py_fw = {
                    "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
                    "celery": "Celery", "sqlalchemy": "SQLAlchemy",
                    "pytest": "pytest", "numpy": "NumPy", "pandas": "Pandas",
                }
                for dep, fw in py_fw.items():
                    if dep in content.lower():
                        stack["frameworks"].append(fw)
            except:
                pass

    # Tool detection
    tool_files = {
        "Dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
        "docker-compose.yaml": "Docker Compose",
        ".github/workflows": "GitHub Actions",
        ".gitlab-ci.yml": "GitLab CI",
        "Jenkinsfile": "Jenkins",
        ".eslintrc": "ESLint",
        ".prettierrc": "Prettier",
        "nginx.conf": "Nginx",
        "Makefile": "Make",
        ".env.example": "dotenv",
        "fly.toml": "Fly.io",
        "vercel.json": "Vercel",
        "netlify.toml": "Netlify",
    }
    for file, tool in tool_files.items():
        if (p / file).exists() or (p / file).is_dir():
            stack["tools"].append(tool)

    # Deduplicate
    for k in stack:
        stack[k] = sorted(set(stack[k]))

    return stack


def analyze_structure(project_dir, max_depth=3):
    """Analyze project directory structure."""
    p = Path(project_dir)
    skip = {
        "node_modules", ".git", "__pycache__", "venv", ".venv",
        "dist", "build", ".next", ".nuxt", "vendor", "target",
        ".tox", "coverage", ".cache", ".parcel-cache",
    }

    structure = []
    important_dirs = []

    for item in sorted(p.iterdir()):
        if item.name.startswith(".") and item.name not in (".github", ".env.example"):
            continue
        if item.name in skip:
            continue

        if item.is_dir():
            count = sum(1 for _ in item.rglob("*") if _.is_file() and
                       not any(s in _.parts for s in skip))
            structure.append({
                "name": item.name + "/",
                "type": "directory",
                "file_count": count,
            })
            if count > 0:
                important_dirs.append(item.name)
        elif item.is_file():
            structure.append({
                "name": item.name,
                "type": "file",
                "size_kb": round(item.stat().st_size / 1024, 1),
            })

    return {"tree": structure, "important_dirs": important_dirs}


def extract_scripts(project_dir):
    """Extract npm/make/python scripts from config files."""
    p = Path(project_dir)
    scripts = {}

    # package.json scripts
    pkg_path = p / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text())
            npm_scripts = pkg.get("scripts", {})
            for name, cmd in npm_scripts.items():
                scripts[f"npm run {name}"] = cmd
        except:
            pass

    # Makefile targets
    makefile = p / "Makefile"
    if makefile.exists():
        try:
            content = makefile.read_text()
            for m in re.finditer(r'^([a-zA-Z_-]+)\s*:', content, re.M):
                target = m.group(1)
                scripts[f"make {target}"] = ""
        except:
            pass

    # Python manage.py
    if (p / "manage.py").exists():
        scripts["python manage.py runserver"] = "启动 Django 开发服务器"
        scripts["python manage.py migrate"] = "运行数据库迁移"

    return scripts


def extract_env_vars(project_dir):
    """Extract required environment variables from .env.example."""
    p = Path(project_dir)
    env_vars = []

    for env_file in [".env.example", ".env.sample", ".env.template"]:
        env_path = p / env_file
        if env_path.exists():
            try:
                for line in env_path.read_text().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        m = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=', line)
                        if m:
                            env_vars.append(m.group(1))
            except:
                pass
            break

    return env_vars


def analyze_git_info(project_dir):
    """Get git-based project insights."""
    cwd = str(project_dir)

    # Basic info
    remote = run_git(["remote", "get-url", "origin"], cwd).strip()
    branch = run_git(["branch", "--show-current"], cwd).strip()
    total_commits = run_git(["rev-list", "--count", "HEAD"], cwd).strip()

    # Recent contributors
    contributors = run_git(
        ["shortlog", "-sne", "--no-merges", "HEAD"],
        cwd,
    ).strip().split("\n")
    contributors = [c.strip() for c in contributors if c.strip()][:10]

    # Recent activity
    recent = run_git(
        ["log", "--oneline", "-10", "--no-merges"],
        cwd,
    ).strip().split("\n")

    return {
        "remote": remote,
        "branch": branch,
        "total_commits": total_commits,
        "contributors": contributors,
        "recent_commits": [c.strip() for c in recent if c.strip()],
    }


def find_documentation(project_dir):
    """Find existing documentation files."""
    p = Path(project_dir)
    docs = []

    doc_patterns = [
        "README*", "CONTRIBUTING*", "CHANGELOG*", "LICENSE*",
        "docs/*", "doc/*", "wiki/*",
        "ARCHITECTURE*", "DESIGN*", "API*",
        "CLAUDE.md", ".claude/*",
    ]

    for pattern in doc_patterns:
        for f in p.glob(pattern):
            if f.is_file():
                docs.append({
                    "path": str(f.relative_to(p)),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                })

    return docs


# ---------------------------------------------------------------------------
# Onboarding document generator
# ---------------------------------------------------------------------------

def generate_onboarding(project_dir):
    """Generate complete onboarding document."""
    p = Path(project_dir).resolve()
    project_name = p.name

    # Run all analyzers
    tech = detect_tech_stack(p)
    structure = analyze_structure(p)
    scripts = extract_scripts(p)
    env_vars = extract_env_vars(p)
    git = analyze_git_info(p)
    docs = find_documentation(p)

    # Read README for context
    readme_content = ""
    for readme in ["README.md", "README.rst", "README.txt", "README"]:
        readme_path = p / readme
        if readme_path.exists():
            readme_content = readme_path.read_text(encoding="utf-8", errors="ignore")[:3000]
            break

    lines = []

    # Header
    lines.append(f"# {project_name} — 新人入职指南\n")
    lines.append(f"> 由 Onboarding-Gen 自动生成")
    lines.append(f"> 更新时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}\n")

    # Project overview
    lines.append("## 1. 项目概述\n")
    if readme_content:
        # Extract first paragraph from README
        first_para = readme_content.split("\n\n")[0] if "\n\n" in readme_content else readme_content[:300]
        # Remove markdown headers
        first_para = re.sub(r'^#+\s+.*\n', '', first_para).strip()
        if first_para:
            lines.append(f"{first_para[:500]}\n")

    if git.get("remote"):
        lines.append(f"- 仓库地址: `{git['remote']}`")
    lines.append(f"- 主分支: `{git.get('branch', 'main')}`")
    lines.append(f"- 总提交数: {git.get('total_commits', '未知')}")
    lines.append(f"- 贡献者数: {len(git.get('contributors', []))}")
    lines.append("")

    # Tech stack
    lines.append("## 2. 技术栈\n")
    if tech["languages"]:
        lines.append(f"**语言:** {', '.join(tech['languages'])}")
    if tech["frameworks"]:
        lines.append(f"**框架:** {', '.join(tech['frameworks'])}")
    if tech["tools"]:
        lines.append(f"**工具:** {', '.join(tech['tools'])}")
    if tech["databases"]:
        lines.append(f"**数据库:** {', '.join(tech['databases'])}")
    lines.append("")

    # Project structure
    lines.append("## 3. 项目结构\n")
    lines.append("```")
    lines.append(f"{project_name}/")
    for item in structure["tree"]:
        if item["type"] == "directory":
            lines.append(f"├── {item['name']:<30} ({item['file_count']} 个文件)")
        else:
            lines.append(f"├── {item['name']}")
    lines.append("```\n")

    # Getting started
    lines.append("## 4. 环境搭建\n")
    lines.append("### 前置条件\n")

    if "JavaScript/TypeScript" in tech["languages"] or "TypeScript" in tech["languages"]:
        lines.append("- Node.js（版本见 `.nvmrc` 或 `package.json` 的 `engines` 字段）")
        lines.append("- npm / yarn / pnpm")
    if "Python" in tech["languages"]:
        lines.append("- Python 3.9+（具体版本见 `pyproject.toml` 或 `runtime.txt`）")
        lines.append("- pip / pipenv / poetry")
    if "Go" in tech["languages"]:
        lines.append("- Go（版本见 `go.mod`）")
    if "Dart/Flutter" in tech["languages"]:
        lines.append("- Flutter SDK")
    if "Docker" in tech["tools"]:
        lines.append("- Docker & Docker Compose")

    lines.append("\n### 搭建步骤\n")
    lines.append("```bash")
    lines.append(f"# 1. 克隆仓库")
    if git.get("remote"):
        lines.append(f"git clone {git['remote']}")
        lines.append(f"cd {project_name}")
    lines.append("")

    if "JavaScript/TypeScript" in tech["languages"] or "TypeScript" in tech["languages"]:
        lines.append("# 2. 安装依赖")
        lines.append("npm install  # 或: yarn / pnpm install")
        lines.append("")

    if "Python" in tech["languages"]:
        lines.append("# 2. 创建虚拟环境并安装依赖")
        lines.append("python3 -m venv venv")
        lines.append("source venv/bin/activate")
        if (p / "requirements.txt").exists():
            lines.append("pip install -r requirements.txt")
        elif (p / "pyproject.toml").exists():
            lines.append("pip install -e .")
        lines.append("")

    if env_vars:
        lines.append("# 3. 配置环境变量")
        lines.append("cp .env.example .env")
        lines.append("# 编辑 .env 填入你的配置值")
        lines.append("")

    if "Docker" in tech["tools"]:
        lines.append("# 也可以用 Docker 启动")
        lines.append("docker-compose up -d")
        lines.append("")

    lines.append("```\n")

    # Environment variables
    if env_vars:
        lines.append("### 环境变量\n")
        lines.append("将 `.env.example` 复制为 `.env`，并填入以下值:\n")
        lines.append("| 变量 | 说明 |")
        lines.append("|------|------|")
        for var in env_vars[:20]:
            desc = _guess_env_description(var)
            lines.append(f"| `{var}` | {desc} |")
        lines.append("")

    # Available scripts
    if scripts:
        lines.append("## 5. 常用命令\n")
        lines.append("| 命令 | 说明 |")
        lines.append("|------|------|")
        for cmd, desc in scripts.items():
            desc_short = desc[:60] if desc else _guess_script_description(cmd)
            lines.append(f"| `{cmd}` | {desc_short} |")
        lines.append("")

    # Key files
    lines.append("## 6. 新人优先阅读\n")
    lines.append("按顺序阅读以下文件:\n")
    priority_files = []
    if docs:
        for d in docs:
            if "readme" in d["path"].lower():
                priority_files.append((d["path"], "项目概述和搭建说明"))
    priority_files.extend([
        ("package.json", "依赖和脚本") if (p / "package.json").exists() else None,
        ("tsconfig.json", "TypeScript 配置") if (p / "tsconfig.json").exists() else None,
        (".env.example", "需要配置的环境变量") if (p / ".env.example").exists() else None,
    ])
    priority_files = [f for f in priority_files if f]

    for i, (file, desc) in enumerate(priority_files[:8], 1):
        lines.append(f"{i}. **`{file}`** — {desc}")
    lines.append("")

    # Existing documentation
    if docs:
        lines.append("## 7. 项目文档\n")
        for d in docs:
            lines.append(f"- `{d['path']}` ({d['size_kb']}KB)")
        lines.append("")

    # Team
    if git.get("contributors"):
        lines.append("## 8. 团队成员\n")
        lines.append("| 贡献者 | 提交次数 |")
        lines.append("|--------|---------|")
        for c in git["contributors"][:10]:
            m = re.match(r'\s*(\d+)\s+(.*)', c)
            if m:
                lines.append(f"| {m.group(2)} | {m.group(1)} |")
        lines.append("")

    # Recent activity
    if git.get("recent_commits"):
        lines.append("## 9. 近期动态\n")
        lines.append("最近 10 条提交:\n")
        for c in git["recent_commits"]:
            lines.append(f"- `{c}`")
        lines.append("")

    # Tips
    lines.append("## 10. 新人上手建议\n")
    lines.append("1. **先读 README** — 了解项目目标和搭建流程")
    lines.append("2. **先跑通项目** — 在改代码之前确保本地能运行")
    lines.append("3. **从小任务开始** — 改个 typo、补个注释、加个测试")
    lines.append("4. **大胆提问** — 新人没有蠢问题")

    if structure.get("important_dirs"):
        top_dir = structure["important_dirs"][0]
        lines.append(f"5. **多看 `{top_dir}/`** — 项目核心代码在这里")

    lines.append("")
    return "\n".join(lines)


def _guess_env_description(var):
    """Guess what an environment variable is for."""
    var_lower = var.lower()
    if "key" in var_lower or "secret" in var_lower or "token" in var_lower:
        return "API 密钥或密码（找团队负责人获取）"
    if "url" in var_lower or "host" in var_lower:
        return "服务地址"
    if "port" in var_lower:
        return "端口号"
    if "db" in var_lower or "database" in var_lower:
        return "数据库连接"
    if "redis" in var_lower:
        return "Redis 连接"
    if "mail" in var_lower or "smtp" in var_lower or "email" in var_lower:
        return "邮件/SMTP 配置"
    if "debug" in var_lower:
        return "调试模式（true/false）"
    if "log" in var_lower:
        return "日志配置"
    return "配置项"


def _guess_script_description(cmd):
    """Guess what a script command does."""
    cmd_lower = cmd.lower()
    if "start" in cmd_lower or "serve" in cmd_lower:
        return "启动开发服务器"
    if "build" in cmd_lower:
        return "生产构建"
    if "test" in cmd_lower:
        return "运行测试"
    if "lint" in cmd_lower:
        return "代码检查"
    if "format" in cmd_lower or "prettier" in cmd_lower:
        return "代码格式化"
    if "dev" in cmd_lower:
        return "启动开发模式"
    if "deploy" in cmd_lower:
        return "部署到生产环境"
    if "migrate" in cmd_lower:
        return "运行数据库迁移"
    if "seed" in cmd_lower:
        return "填充数据库种子数据"
    if "clean" in cmd_lower:
        return "清理构建产物"
    return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Onboarding-Gen: 自动生成新人入职文档")
    parser.add_argument("--dir", "-d", default=".", help="项目目录")
    parser.add_argument("--output", "-o", help="输出 Markdown 文件路径")
    parser.add_argument("--json", dest="json_output", help="输出分析 JSON 文件路径")
    args = parser.parse_args()

    project_dir = Path(args.dir).resolve()
    print(f"[*] 正在分析项目: {project_dir.name}")

    doc = generate_onboarding(project_dir)

    if args.output:
        Path(args.output).write_text(doc)
        print(f"[+] 入职文档已生成: {args.output}")
    else:
        print(doc)

    if args.json_output:
        analysis = {
            "tech_stack": detect_tech_stack(project_dir),
            "structure": analyze_structure(project_dir),
            "scripts": extract_scripts(project_dir),
            "env_vars": extract_env_vars(project_dir),
            "git": analyze_git_info(project_dir),
            "docs": find_documentation(project_dir),
        }
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"[+] 分析 JSON 已生成: {args.json_output}")


if __name__ == "__main__":
    main()
