# Agent Memory Enhance — MCP 记忆服务器

> **3 分钟给任何 AI Agent 装上长期记忆系统。**
>
> 基于 MCP（Model Context Protocol）协议的记忆服务器，提供结构化记忆存储、三层漏斗检索、
> 自我维护（合并 + 衰减遗忘），兼容 Claude Desktop、Cursor、TRAE、Windsurf 等所有 MCP 客户端。

## 核心特性

- **结构化记忆**：每条记忆是一个结构化对象（名称 / 关键词 / 摘要 / 触发场景 / 重要度 1-5）
- **三层漏斗检索**：语义匹配（embedding / TF-IDF）→ LLM 相关性精筛 → 原始内容展开
- **自我维护**：自动合并相似记忆（相似度 ≥ 0.9）+ 自动遗忘低重要度过期记忆（30 天未访问且重要度 < 3）
- **零外部依赖**：SQLite 存储，不需要外部数据库
- **向量可选**：配置了 embedding 模型走语义向量检索，不配自动回退字符 bigram TF-IDF 余弦相似度
- **通用兼容**：支持 Claude Desktop、Cursor、TRAE、Windsurf 等所有 MCP 客户端

## 快速开始

### 1. 安装

```bash
pip install agent-memory-enhance
```

或从源码安装：

```bash
git clone https://github.com/asf9sf/agent-memory-enhance-skill.git
cd agent-memory-enhance-skill
pip install -e .
```

### 2. 配置

通过环境变量配置，所有参数都有默认值，开箱即用：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `MEMORY_LLM_BASE_URL` | `http://localhost:1234/v1` | OpenAI 兼容 API 地址 |
| `MEMORY_LLM_API_KEY` | `no-key` | API 密钥 |
| `MEMORY_LLM_MODEL` | `local-model` | LLM 模型名称 |
| `MEMORY_EMBEDDING_MODEL` | `""`（空 = 用 TF-IDF） | Embedding 模型名称（可选） |
| `MEMORY_DB_PATH` | `./memory.db` | SQLite 数据库路径 |
| `MEMORY_LLM_TIMEOUT` | `30` | LLM 请求超时（秒） |

示例：
```bash
set MEMORY_LLM_BASE_URL=http://localhost:1234/v1
set MEMORY_LLM_MODEL=qwen2.5:7b
set MEMORY_EMBEDDING_MODEL=    # 留空则使用 TF-IDF 回退方案
```

### 3. 连接到你的 Agent

#### Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "agent_memory_enhance.server"],
      "env": {
        "MEMORY_LLM_BASE_URL": "http://localhost:1234/v1",
        "MEMORY_LLM_MODEL": "local-model"
      }
    }
  }
}
```

#### Cursor

在 `~/.cursor/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "agent_memory_enhance.server"],
      "env": {
        "MEMORY_LLM_BASE_URL": "http://localhost:1234/v1"
      }
    }
  }
}
```

#### TRAE

在 TRAE 的 MCP 设置中添加：

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "agent_memory_enhance.server"]
    }
  }
}
```

#### 直接运行（测试用）

```bash
python -m agent_memory_enhance.server
```

## 工具列表

服务器暴露 9 个 MCP 工具：

| 工具 | 说明 |
|------|------|
| `memory_add` | 从对话文本中提取记忆并存储（LLM 自动提取名称/关键词/摘要/触发场景/重要度） |
| `memory_search` | 三层漏斗检索相关记忆（语义匹配 → LLM 精筛 → 返回完整内容） |
| `memory_list` | 列出所有活跃记忆（按重要度降序排列） |
| `memory_get` | 按 ID 获取单条记忆的完整详情 |
| `memory_delete` | 软删除一条记忆（可恢复） |
| `memory_update_importance` | 更新记忆的重要度（1-5） |
| `memory_maintenance` | 执行维护：合并相似记忆 + 衰减遗忘 |
| `memory_count` | 获取活跃记忆总数 |
| `memory_build_context` | 检索 + 格式化为可直接注入 LLM 的上下文文本 |

## 工作原理

### 记忆写入（`memory_add`）

```
对话文本
  ↓
LLM 提取（结构化 JSON：名称、关键词、摘要、触发场景、重要度）
  ↓
生成 Embedding 向量（可选，用于语义检索）
  ↓
写入 SQLite
```

### 记忆检索（`memory_search`）

```
用户当前消息
  ↓
第一层：语义匹配（embedding 余弦相似度 / TF-IDF）→ 取 Top-5 候选
  ↓
第二层：LLM 精细筛选 → 选出 0-3 条真正相关的
  ↓
第三层：返回含完整原始内容的记忆 + 更新访问记录
```

### 记忆维护（`memory_maintenance`）

```
所有活跃记忆
  ↓
合并：相似度 ≥ 0.9 → LLM 合并为一条更完整的记忆 → 旧记忆归档
  ↓
衰减：重要度 < 3 且 30 天未访问 → 归档
```

## 项目结构

```
agent-memory-enhance-skill/
├── src/agent_memory_enhance/
│   ├── __init__.py
│   ├── llm_client.py      # 轻量级 OpenAI 兼容 LLM + Embedding 客户端
│   ├── memory_core.py     # 记忆系统核心（MemorySkill + MemoryStore + MemSkillManager）
│   └── server.py          # MCP 服务器，暴露 9 个工具
├── pyproject.toml
└── README.md
```

## 许可证

MIT
