# Skills

可复用的 Agent Skill 集合。每个 Skill 是一个独立目录，包含 `SKILL.md`（指令）、模板和校验脚本，可直接安装到 Claude Code / Codex / Agents 等 Agent 宿主中使用。

## 安装

将所需 Skill 目录链接到宿主的全局 Skills 路径即可。以 Claude Code 为例：

```bash
# 克隆仓库
git clone https://github.com/Golness/skills.git ~/skills

# 链接到 Claude Code
ln -s ~/skills/technical-solution-html ~/.claude/skills/technical-solution-html

# 链接到 Codex
ln -s ~/skills/technical-solution-html ~/.codex/skills/technical-solution-html
```

Windows 下使用 PowerShell 创建软链接：

```powershell
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\technical-solution-html" -Target "D:\project\skills\technical-solution-html"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.codex\skills\technical-solution-html" -Target "D:\project\skills\technical-solution-html"
```

链接后修改源文件立即生效，无需重新安装。

## Skills 一览

| Skill | 说明 |
|-------|------|
| [technical-solution-html](technical-solution-html/) | 生成中文软件技术方案，交付带滚动跟随目录、代码高亮、Mermaid 图表的单文件 HTML |

## 目录结构

```
skills/
└── technical-solution-html/
    ├── SKILL.md                              # Skill 指令与页面契约
    ├── agents/openai.yaml                    # OpenAI Agents 适配配置
    ├── assets/technical-solution-template.html  # HTML 模板（含 CSS/JS）
    └── scripts/validate_html.py              # 生成文件校验脚本
```

## 许可证

MIT
