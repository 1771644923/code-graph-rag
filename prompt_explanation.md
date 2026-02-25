# Prompt 使用机制说明

## 整体流程

```
用户请求
    ↓
CypherGenerator.generate(natural_language_query)
    ↓
Agent.run(natural_language_query)
    ↓
[系统提示 system_prompt] + [用户输入 natural_language_query]
    ↓
LLM 处理并返回结果
    ↓
验证结果是否包含 MATCH 关键字
    ↓
清理结果并返回
```

## 1. System Prompt 的选择机制

在 `codebase_rag/services/llm.py` 的 `CypherGenerator.__init__()` 方法中：

```python
system_prompt = (
    LOCAL_CYPHER_SYSTEM_PROMPT
    if config.provider in [cs.Provider.OLLAMA, cs.Provider.OPENAI_COMPATIBLE]
    else CYPHER_SYSTEM_PROMPT
)
```

### 选择逻辑

| Provider 类型 | 使用的 Prompt | 原因 |
|------------|--------------|--------|
| `ollama` | `LOCAL_CYPHER_SYSTEM_PROMPT` | 本地模型通常能力较弱，需要更简单直接的提示 |
| `openai_compatible` | `LOCAL_CYPHER_SYSTEM_PROMPT` | 兼容端点（如京东言犀）可能需要简化提示 |
| `openai` | `CYPHER_SYSTEM_PROMPT` | OpenAI 模型能力强，可以使用复杂的系统提示 |
| `google` | `CYPHER_SYSTEM_PROMPT` | Google 模型能力强，可以使用复杂的系统提示 |

## 2. 两种 Prompt 的区别

### CYPHER_SYSTEM_PROMPT（完整版）

**特点**：
- 包含详细的图数据库 Schema 定义
- 包含复杂的查询规则和最佳实践
- 包含大量的示例和模式
- 适合能力强的大型模型

**结构**：
```python
CYPHER_SYSTEM_PROMPT = f"""
You are an expert translator that converts natural language questions 
about code structure into precise Neo4j Cypher queries.

{GRAPH_SCHEMA_AND_RULES}  # 包含图数据库的节点类型、关系等

**3. Query Optimization Rules**
- LIMIT Results: ALWAYS add `LIMIT 50`...
- Aggregation Queries: When asked "how many"...

**4. Query Patterns & Examples**
Pattern: Counting Items
Pattern: Finding Decorated Functions
Pattern: Finding Content by Path
Pattern: Finding a Specific File
...（大量示例）

**4. Output Format**
Provide only the Cypher query.
"""
```

**长度**：约 2000-3000 字符

### LOCAL_CYPHER_SYSTEM_PROMPT（简化版）

**特点**：
- 移除了复杂的 Schema 定义
- 只保留最核心的规则
- 提供简单的示例
- 适合能力较弱的本地/兼容模型

**结构**：
```python
LOCAL_CYPHER_SYSTEM_PROMPT = f"""
You are a Neo4j Cypher query generator. 
You ONLY respond with a valid Cypher query. 
Do not add explanations or markdown.

**CRITICAL RULES:**
1. Return ONLY Cypher query - no explanations
2. Your query must start with MATCH
3. Your query must end with RETURN
4. For count queries: MATCH (n:NodeType) RETURN count(n) AS total
5. For list queries: MATCH (n:NodeType) RETURN n.property LIMIT 50

**Node Types available:**
- Class (has: name, path, qualified_name)
- Function (has: name, path, qualified_name)
- File (has: name, path, extension)

**Examples:**
User: How many classes are there?
MATCH (c:Class) RETURN count(c) AS total

User: Find all classes
MATCH (c:Class) RETURN c.qualified_name LIMIT 50

...（几个简单示例）
"""
```

**长度**：约 800-1000 字符

## 3. Prompt 组合机制

使用 `pydantic-ai` 的 `Agent` 类：

```python
self.agent = Agent(
    model=llm,                    # 配置好的 LLM 模型
    system_prompt=system_prompt,       # 系统提示（角色定义、规则）
    output_type=str,                 # 期望的输出类型
    retries=settings.AGENT_RETRIES,   # 重试次数
)
```

### 实际调用时

```python
# 用户输入
natural_language_query = "List all classes in the codebase"

# Agent.run() 会自动组合
result = await self.agent.run(natural_language_query)

# 实际发送给 LLM 的完整输入：
"""
{system_prompt}

{natural_language_query}
"""
```

### LLM 看到的完整示例

**使用 CYPHER_SYSTEM_PROMPT**：
```
You are an expert translator that converts natural language questions 
about code structure into precise Neo4j Cypher queries.

The database contains information about a codebase, structured with 
the following nodes and relationships.

[此处有 500+ 行的 Schema 定义、规则、示例]

**4. Output Format**
Provide only the Cypher query.

List all classes in the codebase
```

**使用 LOCAL_CYPHER_SYSTEM_PROMPT**：
```
You are a Neo4j Cypher query generator. 
You ONLY respond with a valid Cypher query. 
Do not add explanations or markdown.

**CRITICAL RULES:**
1. Return ONLY Cypher query - no explanations
2. Your query must start with MATCH
3. Your query must end with RETURN
4. For count queries: MATCH (n:NodeType) RETURN count(n) AS total
5. For list queries: MATCH (n:NodeType) RETURN n.property LIMIT 50

**Node Types available:**
- Class (has: name, path, qualified_name)
- Function (has: name, path, qualified_name)
- File (has: name, path, extension)

**Examples:**
User: How many classes are there?
MATCH (c:Class) RETURN count(c) AS total

User: Find all classes
MATCH (c:Class) RETURN c.qualified_name LIMIT 50

List all classes in the codebase
```

## 4. 为什么京东言犀模型失败了？

### 问题分析

| 测试场景 | Prompt 长度 | 结果 | 原因 |
|---------|------------|------|------|
| test_model_directly.py | ~200 字符 | ✅ 成功 | Prompt 简单，模型能理解核心任务 |
| test_cypher_generation.py | ~2500 字符（CYPHER_SYSTEM_PROMPT）| ❌ 失败 | Prompt 太长，模型被信息"淹没" |

### 失败原因

1. **上下文过长**：CYPHER_SYSTEM_PROMPT 包含大量 Schema 定义、复杂规则、多个示例
2. **信息过载**：模型无法从 2500+ 字符中提取核心任务
3. **训练偏差**：模型可能被训练为总是提供解释性文本
4. **指令冲突**：复杂的规则和示例可能导致模型混淆

### 为什么简化版本也不行？

即使修改为 `LOCAL_CYPHER_SYSTEM_PROMPT`，测试仍然失败，因为：

1. 仍然包含相对较长的说明（~1000 字符）
2. 模型对"代码查询"这个场景的理解能力有限
3. 模型的训练数据可能主要包含通用对话，而非特定任务执行

## 5. 如何解决？

### 解决方案 1：使用专门优化的 Prompt（当前尝试）

进一步简化 `LOCAL_CYPHER_SYSTEM_PROMPT`：

```python
LOCAL_CYPHER_SYSTEM_PROMPT = """
Generate Cypher query. Start with MATCH, end with RETURN.
No explanations, only query.

Examples:
How many classes? -> MATCH (c:Class) RETURN count(c) AS total
Find classes -> MATCH (c:Class) RETURN c.name LIMIT 50
"""
```

**问题**：过于简化可能导致模型生成不准确的查询

### 解决方案 2：使用更强的模型（推荐）

使用 GPT-4o-mini、Gemini 2.5-flash 等模型：

- 能够处理长上下文
- 理解复杂的指令
- 有良好的代码生成能力

### 解决方案 3：Few-Shot Learning（少样本学习）

在每次请求时提供几个示例，而不是在系统提示中：

```python
query = f"""
Generate a Cypher query for: {natural_language_query}

Examples:
User: How many classes?
Assistant: MATCH (c:Class) RETURN count(c) AS total

User: Find all files
Assistant: MATCH (f:File) RETURN f.path LIMIT 50

User: {natural_language_query}
Assistant:"""
```

## 6. 总结

Prompt 使用机制的核心要点：

1. **分层设计**：根据模型能力选择不同复杂度的系统提示
2. **上下文管理**：系统提示 + 用户输入的组合方式
3. **模型适配**：不同模型需要不同的提示策略
4. **平衡原则**：在详细说明和简洁指令之间找到平衡

对于 Cypher 查询生成这样的特定任务：
- 强模型（GPT-4o、Gemini）→ 完整 Prompt
- 中等模型 → 简化 Prompt
- 弱模型（当前京东言犀）→ 需要更换模型或极简 Prompt