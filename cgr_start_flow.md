# CGR Start 命令问题回答逻辑流程文档

## 概述

本文档详细说明了 `cgr start --repo-path` 命令启动后，用户提问后系统的回答逻辑流程。

## 1. 启动流程

### 1.1 命令入口

```bash
cgr start --repo-path <repository_path>
```

**入口文件**: [codebase_rag/cli.py](codebase_rag/cli.py#L81-L197)

### 1.2 启动步骤

```
用户执行命令
    ↓
cli.start() 函数
    ↓
检查是否 --update-graph 模式
    ├─ 是: 执行图更新流程
    └─ 否: 执行问答流程
         ↓
      main_async()
```

### 1.3 main_async 初始化 ([codebase_rag/main.py#L1024-L1041](codebase_rag/main.py#L1024-L1041))

```python
async def main_async(repo_path: str, batch_size: int) -> None:
    # 1. 通用初始化设置
    project_root = _setup_common_initialization(repo_path)
    
    # 2. 创建并显示配置表格
    table = _create_configuration_table(repo_path)
    app_context.console.print(table)
    
    # 3. 连接 Memgraph 数据库
    with connect_memgraph(batch_size) as ingestor:
        # 4. 初始化服务和 Agent
        rag_agent, tool_names = _initialize_services_and_agent(repo_path, ingestor)
        
        # 5. 启动聊天循环
        await run_chat_loop(rag_agent, [], project_root, tool_names)
```

## 2. 服务和 Agent 初始化

### 2.1 _initialize_services_and_agent ([codebase_rag/main.py#L971-L1021](codebase_rag/main.py#L971-L1021))

此函数初始化所有必要的工具并创建 RAG Agent：

```python
def _initialize_services_and_agent(repo_path: str, ingestor: QueryProtocol):
    # 1. 验证模型配置
    _validate_provider_config(cs.ModelRole.ORCHESTRATOR, ...)
    _validate_provider_config(cs.ModelRole.CYPHER, ...)
    
    # 2. 创建核心服务
    cypher_generator = CypherGenerator()
    code_retriever = CodeRetriever(project_root=repo_path, ingestor=ingestor)
    file_reader = FileReader(project_root=repo_path)
    file_writer = FileWriter(project_root=repo_path)
    file_editor = FileEditor(project_root=repo_path)
    shell_commander = ShellCommander(project_root=repo_path, ...)
    directory_lister = DirectoryLister(project_root=repo_path)
    document_analyzer = DocumentAnalyzer(project_root=repo_path)
    
    # 3. 创建工具
    query_tool = create_query_tool(...)
    code_tool = create_code_retrieval_tool(...)
    file_reader_tool = create_file_reader_tool(...)
    file_writer_tool = create_file_writer_tool(...)
    file_editor_tool = create_file_editor_tool(...)
    shell_command_tool = create_shell_command_tool(...)
    directory_lister_tool = create_directory_lister_tool(...)
    document_analyzer_tool = create_document_analyzer_tool(...)
    semantic_search_tool = create_semantic_search_tool()
    function_source_tool = create_get_function_source_tool()
    
    # 4. 创建 RAG Agent
    rag_agent = create_rag_orchestrator(tools=[...])
    
    return rag_agent, confirmation_tool_names
```

### 2.2 可用工具列表

| 工具名称 | 用途 |
|---------|------|
| `query_graph` | 通过自然语言查询图数据库 |
| `code_retrieval` | 代码检索 |
| `read_file` | 读取文件内容 |
| `create_file` | 创建新文件 |
| `replace_code` | 精确替换代码 |
| `execute_shell_command` | 执行 shell 命令 |
| `list_directory` | 列出目录内容 |
| `analyze_document` | 分析文档（如 PDF） |
| `semantic_code_search` | 语义代码搜索 |
| `get_function_source` | 获取函数源码 |

### 2.3 RAG Agent 创建 ([codebase_rag/services/llm.py#L78-L92](codebase_rag/services/llm.py#L78-L92))

```python
def create_rag_orchestrator(tools: list[Tool]) -> Agent:
    config = settings.active_orchestrator_config
    llm = _create_provider_model(config)
    
    return Agent(
        model=llm,
        system_prompt=build_rag_orchestrator_prompt(tools),
        tools=tools,
        retries=settings.AGENT_RETRIES,
        output_retries=settings.ORCHESTRATOR_OUTPUT_RETRIES,
        output_type=[str, DeferredToolRequests],
    )
```

## 3. 问答循环流程

### 3.1 主循环结构 ([codebase_rag/main.py#L617-L691](codebase_rag/main.py#L617-L691))

```
┌─────────────────────────────────────┐
│   _run_interactive_loop             │
│   无限循环等待用户输入               │
└──────────────┬──────────────────────┘
               ↓
      ┌────────────────┐
      │ 获取用户问题   │
      └───────┬────────┘
              ↓
      ┌────────────────┐
      │ 检查特殊命令   │
      │ - exit 退出    │
      │ - /model 换模型│
      │ - /help 帮助   │
      └───────┬────────┘
              ↓
      ┌────────────────┐
      │ 处理图片路径   │
      └───────┬────────┘
              ↓
      ┌────────────────┐
      │_run_agent_     │
      │response_loop   │
      └───────┬────────┘
              ↓
        等待下一个问题
```

### 3.2 Agent 响应循环 ([codebase_rag/main.py#L388-L438](codebase_rag/main.py#L388-L438))

```python
async def _run_agent_response_loop(rag_agent, message_history, question, ...):
    while True:
        # 1. 运行 Agent
        response = await rag_agent.run(question, ...)
        
        # 2. 检查是否被取消
        if isinstance(response, CancelledResult):
            break
        
        # 3. 处理延迟工具请求（需要用户确认）
        if isinstance(response.output, DeferredToolRequests):
            deferred_results = _process_tool_approvals(...)
            message_history.extend(response.new_messages())
            continue  # 继续循环，使用确认结果再次调用
        
        # 4. 输出最终答案
        output_text = response.output
        app_context.console.print(Markdown(output_text))
        
        # 5. 更新消息历史并退出
        message_history.extend(response.new_messages())
        break
```

## 4. 问题回答核心逻辑

### 4.1 System Prompt 指导原则 ([codebase_rag/prompts.py#L61-L130](codebase_rag/prompts.py#L61-L130))

Agent 的行为由 `build_rag_orchestrator_prompt` 定义的 system prompt 控制：

#### 关键规则

1. **仅基于工具回答**
   - 必须只使用工具返回的信息
   - 不得使用外部知识
   - 工具失败必须明确报告

2. **自然语言查询**
   - 使用 `query_graph` 工具时，始终使用自然语言
   - 系统会自动将自然语言转换为 Cypher 查询

3. **选择正确的工具**
   - 源代码文件 (`.py`, `.ts` 等) → `read_file`
   - 文档文件 (PDF) → `analyze_document`

#### 通用方法

##### 1. 文档分析
```
用户问文档问题
    ↓
使用 analyze_document 工具
    ↓
提供 file_path 和 question
    ↓
返回分析结果
```

##### 2. 深入代码分析
```
用户问代码问题
    ↓
a. 检查文档文件 (README.md)
    ↓
b. 检查配置文件
    ↓
c. 深入源代码
    ↓
d. 综合所有信息回答
```

##### 3. 搜索策略（语义优先）

**何时优先使用语义搜索** (`semantic_search`)：
- "main entry point", "startup", "initialization"
- "error handling", "validation", "authentication"
- "where is X done", "how does Y work"
- 任何关于目的、意图、功能的问题

**何时直接使用图查询** (`query_graph`)：
- 已知具体名称的结构查询
- "What does function X call?" (已知 X)
- "List methods of User class" (已知 User)

**推荐的混合方法**：
```
1. semantic_search - 按意图/含义查找相关代码
2. query_graph - 探索结构关系
3. read_file - 检查实际源代码
```

##### 4. 工具链示例

**查询 "main entry point 和它调用的内容"**：
```
1. semantic_search("main entry startup")
   → 找到候选函数
   
2. query_graph("找到函数调用关系")
   → 探索结构关系
   
3. read_file("main.py", specific_sections)
   → 读取实际源代码
   
4. 分析并总结执行流程
```

### 4.2 工具调用流程

```
用户问题
    ↓
Agent 分析问题
    ↓
根据 Prompt 规则选择工具
    ↓
执行工具调用
    ├─ query_graph: 自然语言 → Cypher → 查询结果
    ├─ semantic_search: 向量搜索 → 相关代码
    ├─ read_file: 读取文件内容
    ├─ analyze_document: 分析文档
    └─ 其他工具...
    ↓
收集工具返回结果
    ↓
Agent 综合分析
    ↓
生成最终答案
    ↓
返回 Markdown 格式回答
```

### 4.3 危险操作确认流程

对于需要确认的操作（如修改文件、执行 shell 命令）：

```
Agent 决定需要执行危险操作
    ↓
返回 DeferredToolRequests
    ↓
_process_tool_approvals()
    ↓
显示确认提示给用户
    ├─ 用户确认: 执行操作
    └─ 用户拒绝: 取消操作
    ↓
使用确认结果再次调用 Agent
    ↓
继续生成最终答案
```

## 5. 关键文件索引

| 功能 | 文件路径 |
|------|---------|
| CLI 命令入口 | [codebase_rag/cli.py#L81-L197](codebase_rag/cli.py#L81-L197) |
| 主异步函数 | [codebase_rag/main.py#L1024-L1041](codebase_rag/main.py#L1024-L1041) |
| 交互循环 | [codebase_rag/main.py#L617-L691](codebase_rag/main.py#L617-L691) |
| Agent 响应循环 | [codebase_rag/main.py#L388-L438](codebase_rag/main.py#L388-L438) |
| 服务初始化 | [codebase_rag/main.py#L971-L1021](codebase_rag/main.py#L971-L1021) |
| Agent 创建 | [codebase_rag/services/llm.py#L78-L92](codebase_rag/services/llm.py#L78-L92) |
| System Prompt | [codebase_rag/prompts.py#L61-L130](codebase_rag/prompts.py#L61-L130) |

## 6. Agent 工具调用详细机制

### 6.1 工具注册与初始化

在 `_initialize_services_and_agent` 中，所有工具被创建并传递给 Agent：

```python
# tools/codebase_query.py
def create_query_tool(ingestor, cypher_gen, console) -> Tool:
    async def query_codebase_knowledge_graph(natural_language_query: str) -> QueryGraphData:
        # 1. 使用 CypherGenerator 将自然语言转换为 Cypher 查询
        cypher_query = await cypher_gen.generate(natural_language_query)
        
        # 2. 在 Memgraph 中执行查询
        results = ingestor.fetch_all(cypher_query)
        
        # 3. 格式化并显示结果
        if results:
            table = Table(...)
            console.print(Panel(table, title=QUERY_RESULTS_PANEL_TITLE))
        
        return QueryGraphData(query_used=cypher_query, results=results, summary=...)
    
    return Tool(
        function=query_codebase_knowledge_graph,
        name="query_codebase_knowledge_graph",
        description=td.CODEBASE_QUERY,
    )
```

### 6.2 各工具的调用细节

#### 6.2.1 query_graph 工具 ([codebase_rag/tools/codebase_query.py#L32-L89](codebase_rag/tools/codebase_query.py#L32-L89))

**调用流程**：
```
Agent: "查询所有函数"
    ↓
query_codebase_knowledge_graph(natural_language_query="查询所有函数")
    ↓
CypherGenerator.generate("查询所有函数")
    ↓
生成 Cypher: "MATCH (f:Function) RETURN f.name AS name LIMIT 50"
    ↓
ingestor.fetch_all(cypher_query)
    ↓
返回: QueryGraphData { query_used, results, summary }
```

**特点**：
- 接收自然语言查询
- 内部调用 LLM 生成 Cypher 查询
- 查询结果会以表格形式在控制台显示
- 返回结构化数据供 Agent 使用

#### 6.2.2 code_retrieval 工具 ([codebase_rag/tools/code_retrieval.py#L86-L88](codebase_rag/tools/code_retrieval.py#L86-L88))

**调用流程**：
```
Agent: "获取 MyClass.my_method 的源代码"
    ↓
get_code_snippet(qualified_name="MyClass.my_method")
    ↓
code_retriever.find_code_snippet(qualified_name)
    ↓
执行 Cypher 查询: CYPHER_FIND_BY_QUALIFIED_NAME
    ↓
从数据库获取: { path, start_line, end_line, docstring }
    ↓
读取文件并提取指定行
    ↓
返回: CodeSnippet { source_code, file_path, line_start, line_end }
```

**特点**：
- 通过 qualified_name 查询代码片段
- 自动读取文件并提取特定行
- 返回包含源代码、文件路径和行号的结构化数据

#### 6.2.3 read_file 工具 ([codebase_rag/tools/file_reader.py#L56-L60](codebase_rag/tools/file_reader.py#L56-L60))

**调用流程**：
```
Agent: "读取 src/main.py 的内容"
    ↓
read_file_content(file_path="src/main.py")
    ↓
file_reader.read_file(file_path)
    ↓
验证: 文件存在? 是二进制文件?
    ↓
读取文件内容
    ↓
返回: 文件内容字符串
```

**特点**：
- 直接读取文件完整内容
- 自动检测二进制文件并拒绝读取
- 返回纯文本内容供 Agent 分析

#### 6.2.4 semantic_search 工具 ([codebase_rag/tools/semantic_search.py#L122-L140](codebase_rag/tools/semantic_search.py#L122-L140))

**调用流程**：
```
Agent: "搜索与用户认证相关的函数"
    ↓
semantic_search_functions(query="user authentication", top_k=5)
    ↓
semantic_code_search(query, top_k)
    ↓
Qdrant 向量搜索
    ↓
返回: 格式化的搜索结果列表
```

**特点**：
- 使用向量嵌入进行语义搜索
- 可指定返回结果数量 (top_k)
- 返回带相关性评分的结果

#### 6.2.5 create_file 工具 ([codebase_rag/tools/file_writer.py#L43-L44](codebase_rag/tools/file_writer.py#L43-L44))

**调用流程**：
```
Agent 决定创建新文件
    ↓
create_new_file(file_path="src/utils.py", content="...")
    ↓
返回 DeferredToolRequests (需要用户确认)
    ↓
用户确认后执行
    ↓
file_writer.create_file(file_path, content)
    ↓
创建目录并写入文件
    ↓
返回: FileCreationResult { file_path }
```

**特点**：
- 标记为 `requires_approval=True`
- 自动创建父目录
- 需要用户确认后才能执行

#### 6.2.6 replace_code 工具 ([codebase_rag/tools/file_editor.py#L280-L282](codebase_rag/tools/file_editor.py#L280-L282))

**调用流程**：
```
Agent 决定修改代码
    ↓
replace_code_surgically(
    file_path="src/main.py",
    target_code="def old_func():\n    pass",
    replacement_code="def new_func():\n    return 42"
)
    ↓
返回 DeferredToolRequests (需要用户确认)
    ↓
用户确认后执行
    ↓
file_editor.replace_code_block(file_path, target_code, replacement_code)
    ↓
精确替换代码块
    ↓
返回: 成功/失败消息
```

**特点**：
- 精确匹配目标代码块
- 需要用户确认
- 使用差异显示帮助用户理解修改

#### 6.2.7 execute_shell_command 工具 ([codebase_rag/tools/shell_command.py#L437-L443](codebase_rag/tools/shell_command.py#L437-L443))

**调用流程**：
```
Agent 决定执行命令
    ↓
run_shell_command(ctx, command="pytest tests/")
    ↓
检查是否需要确认
    ↓
返回 DeferredToolRequests (对于危险命令)
    ↓
用户确认后执行
    ↓
shell_commander.execute(command)
    ↓
执行命令并捕获输出
    ↓
返回: ShellCommandResult { return_code, stdout, stderr }
```

**特点**：
- 内置危险命令检测 (如 rm, format 等)
- 超时保护机制
- 捕获 stdout 和 stderr

#### 6.2.8 list_directory 工具 ([codebase_rag/tools/directory_lister.py#L54-L56](codebase_rag/tools/directory_lister.py#L54-L56))

**调用流程**：
```
Agent: "列出 src 目录的内容"
    ↓
directory_lister.list_directory_contents("src")
    ↓
验证路径安全性 (防止目录遍历攻击)
    ↓
os.listdir(target_path)
    ↓
返回: 目录内容列表字符串
```

**特点**：
- 安全路径验证
- 防止访问项目外目录
- 返回简单列表

### 6.3 工具调用审批流程 ([codebase_rag/main.py#L219-L249](codebase_rag/main.py#L219-L249))

当 Agent 需要执行需要确认的操作时：

```
Agent.run(question)
    ↓
返回 response.output = DeferredToolRequests
    ↓
_process_tool_approvals()
    ├─ 遍历每个需要确认的工具调用
    ├─ 显示工具名称和参数
    ├─ 显示差异 (对于文件修改)
    ├─ 询问用户: "Do you want to proceed?"
    │   ├─ 用户确认: deferred_results.approvals[id] = True
    │   └─ 用户拒绝: deferred_results.approvals[id] = ToolDenied(message)
    └─ 如果 confirm_edits=False: 自动批准
    ↓
再次调用 Agent.run(..., deferred_tool_results=deferred_results)
    ↓
Agent 使用批准的工具调用结果继续生成答案
```

**审批提示示例**：
```
Tool: create_new_file
File: src/utils.py

Do you want to proceed? [y/N]: y
```

### 6.4 Agent 工具调用循环 ([codebase_rag/main.py#L388-L438](codebase_rag/main.py#L388-L438))

完整的工具调用循环：

```python
while True:
    # 1. 调用 Agent
    response = await rag_agent.run(question, message_history, ...)
    
    # 2. 检查是否取消
    if isinstance(response, CancelledResult):
        break
    
    # 3. 如果需要工具确认
    if isinstance(response.output, DeferredToolRequests):
        # 获取用户批准
        deferred_results = _process_tool_approvals(...)
        
        # 更新消息历史
        message_history.extend(response.new_messages())
        
        # 继续循环，使用批准结果再次调用
        continue
    
    # 4. 得到最终答案
    output_text = response.output
    app_context.console.print(Markdown(output_text))
    
    # 5. 更新消息历史并退出
    message_history.extend(response.new_messages())
    break
```

### 6.5 语义搜索的工作原理和常见问题

#### 6.5.1 语义搜索的工作流程

```
用户问题: "list all structs"
    ↓
Agent 调用 semantic_search("struct definition")
    ↓
1. 检查依赖
   - qdrant-client ✓
   - torch ✓
   - transformers ✓
    ↓
2. 生成查询的向量嵌入
   embed_code("struct definition")
   → 使用 UniXcoder 模型生成向量
    ↓
3. 在 Qdrant 中搜索相似向量
   search_embeddings(query_embedding, top_k=5)
    ↓
4. 从 Qdrant 返回匹配结果
   - 如果有结果: 返回 node_id 和相似度分数
   - 如果无结果: 返回 []
    ↓
5. 查询 Memgraph 获取节点详细信息
   build_nodes_by_ids_query(node_ids)
    ↓
6. 返回格式化的结果
```

#### 6.5.2 向量嵌入的存储流程

向量嵌入是在**图更新阶段**生成的，不是在问答阶段：

```
执行: cgr start --update-graph --repo-path <path>
    ↓
GraphUpdater.run()
    ↓
1. 解析代码文件
    ↓
2. 构建代码图 (存入 Memgraph)
    ↓
3. 生成向量嵌入
   _generate_and_store_embeddings()
    ↓
   a. 查询所有需要嵌入的节点
      CYPHER_QUERY_EMBEDDINGS
      ↓
   b. 提取源代码
      _extract_source_code()
      ↓
   c. 生成向量嵌入
      embed_code(source_code)
      ↓
   d. 存储到 Qdrant
      store_embedding(node_id, embedding, qualified_name)
      ↓
   完成！嵌入向量可用于语义搜索
```

**关键点**：如果只执行 `cgr start` 而没有 `--update-graph`，则不会生成新的向量嵌入。

#### 6.5.3 语义搜索失败的常见原因

##### 原因 1: 依赖缺失

```
症状: 工具调用时显示警告
     [Tool:SemanticSearch] Semantic search requires extra dependencies

原因: 缺少 qdrant-client, torch, 或 transformers

解决: 安装依赖
     pip install qdrant-client torch transformers
```

##### 原因 1.5: Cypher 查询错误（已修复）

```
症状: 执行 cgr start --update-graph 时出现
     "Cypher Error: Invalid types: bool and string for '+'"
     "Failed to generate semantic embeddings"

原因: Cypher 查询中使用了无效的字符串拼接语法
     $project_name + '.'  ← 错误

已修复: 代码已更新，问题已解决
     正确做法: 在 Python 中拼接好字符串后传入
     "project_name_prefix": self.project_name + "."
```

##### 原因 2: 向量嵌入未生成 (最常见)

```
症状: "No semantic matches found for query: ..."
     但代码库中确实有相关内容

原因:
  - 只执行了 cgr start，没有 --update-graph
  - 或者更新图时嵌入生成失败

解决:
  1. 执行图更新并生成嵌入
     cgr start --update-graph --repo-path <path>
     
  2. 检查日志确认嵌入生成
     [INFO] PASS 4: EMBEDDINGS
     [INFO] Generating embeddings for X functions
     [INFO] Embeddings complete: X embedded
```

##### 原因 2.5: Qdrant 数据库被锁定

```
症状: 更新图时出现警告
     "Storage folder is already accessed by another instance of Qdrant client"
     "Failed to store embedding for ..."

原因:
  - 有另一个 CGR 实例正在运行（如 cgr start）
  - Qdrant 本地客户端使用文件锁防止并发访问

解决:
  方案 1: 关闭正在运行的 CGR 实例
    - 按 Ctrl+C 关闭 cgr start
    - 然后再执行 cgr start --update-graph
  
  方案 2: 按正确顺序操作
    1. 先执行 cgr start --update-graph
    2. 等待完成（看到 "Graph update completed!"）
    3. 然后执行 cgr start
  
  方案 3: 使用 Qdrant 服务器（高级）
    - 需要部署 Qdrant 服务器
    - 修改配置使用远程 Qdrant 实例
```

##### 原因 3: Qdrant 数据库为空

```
症状: 依赖检查通过，但搜索总是返回空结果

检查:
  from qdrant_client import QdrantClient
  from codebase_rag.config import settings
  
  client = QdrantClient(path=settings.QDRANT_DB_PATH)
  if client.collection_exists(settings.QDRANT_COLLECTION_NAME):
      info = client.get_collection(settings.QDRANT_COLLECTION_NAME)
      print(f"Points count: {info.points_count}")
  else:
      print("Collection does not exist")

解决:
  - 如果 collection 不存在: 执行 cgr start --update-graph
  - 如果 count 为 0: 执行 cgr start --update-graph
```

##### 原因 4: 查询词不匹配

```
症状: 部分查询有结果，部分没有

原因: 向量相似度是基于语义的，不是关键词匹配

示例:
  ✓ "function that handles authentication" (语义清晰)
  ✗ "auth" (太简短)
  ✓ "database connection management" (具体)
  ✗ "db" (太简短)

解决: 使用更具体的自然语言描述
```

#### 6.5.4 调试语义搜索问题

##### 步骤 1: 检查依赖

```python
from codebase_rag.utils.dependencies import has_semantic_dependencies

if has_semantic_dependencies():
    print("✓ All semantic dependencies are available")
else:
    print("✗ Missing semantic dependencies")
    print("  Install: pip install qdrant-client torch transformers")
```

##### 步骤 2: 检查 Qdrant 数据

```bash
# 检查 Qdrant 目录
ls -la .qdrant_code_embeddings/

# 应该看到:
# .lock
# collection/
# meta.json
```

##### 步骤 3: 检查嵌入生成日志

执行 `cgr start --update-graph` 时，查找以下日志：

```
[INFO] PASS 4: EMBEDDINGS
[INFO] Generating embeddings for 150 functions
[DEBUG] Embedding progress: 50/150
[DEBUG] Embedding progress: 100/150
[INFO] Embeddings complete: 150 embedded
```

如果看到：
```
[INFO] No functions found for embedding
```
说明图数据库中没有可嵌入的函数节点。

##### 步骤 4: 测试向量搜索

```python
from codebase_rag.embedder import embed_code
from codebase_rag.vector_store import get_qdrant_client

# 测试嵌入生成
embedding = embed_code("def hello(): print('world')")
print(f"Embedding dimension: {len(embedding)}")

# 检查集合
client = get_qdrant_client()
info = client.get_collection(settings.QDRANT_COLLECTION_NAME)
print(f"Collection points: {info.points_count}")
print(f"Vector dimension: {info.config.params.vectors.size}")
```

#### 6.5.5 语义搜索与图查询的对比

| 特性 | 语义搜索 | 图查询 |
|-----|----------|--------|
| 查询方式 | 向量相似度 | 精确匹配 |
| 输入 | 自然语言描述 | Cypher 或自然语言 |
| 优点 | 理解意图，模糊匹配 | 精确，快速 |
| 缺点 | 需要预生成嵌入 | 需要知道结构 |
| 适用场景 | "如何做 X", "在哪里实现 Y" | "类 X 有哪些方法", "函数 Z 调用了什么" |
| 依赖 | qdrant-client, torch, transformers | Memgraph |
| 数据准备 | 需要 --update-graph 生成嵌入 | 需要构建图 |

### 6.6 工具调用示例：完整流程

**用户问题**："在项目中创建一个新的工具函数文件，包含一个计算斐波那契数列的函数"

```
1. Agent 分析问题
   ↓
2. 决定需要创建新文件
   ↓
3. 调用 create_new_file(
       file_path="src/fibonacci.py",
       content="def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
   )
   ↓
4. 返回 DeferredToolRequests
   ↓
5. _process_tool_approvals() 处理
   - 显示: "Tool: create_new_file"
   - 显示文件路径和内容预览
   - 询问用户确认
   ↓
6. 用户输入 "y" 确认
   ↓
7. deferred_results = {tool_call_id: True}
   ↓
8. 再次调用 Agent.run(..., deferred_tool_results=deferred_results)
   ↓
9. Agent 执行工具调用
   - FileWriter 创建文件
   - 返回 FileCreationResult
   ↓
10. Agent 生成最终答案
    - "已成功创建 src/fibonacci.py 文件"
    ↓
11. 输出给用户
```

### 6.6 工具调用优先级规则

Agent 在处理用户问题时，根据 System Prompt 中的严格规则来决定工具调用的优先级。

#### 6.6.1 最高优先级：文件类型判断

```
用户问题
    ↓
判断目标文件类型
    ├─ 文档文件 (PDF, DOCX 等) → analyze_document (最高优先级)
    └─ 源代码文件 (.py, .ts, .js 等) → read_file
```

**规则**：
- 对于 PDF 等文档，**必须**使用 `analyze_document`，不要尝试作为纯文本读取
- 对于源代码文件，使用 `read_file` 读取内容

#### 6.6.2 搜索策略优先级：语义优先

Agent 根据问题类型决定搜索策略：

**优先使用 semantic_search 的情况**：

| 问题模式 | 示例 | 工具优先级 |
|---------|------|-----------|
| 入口点查询 | "main entry point", "startup", "initialization", "bootstrap" | **semantic_search** → query_graph → read_file |
| 功能性查询 | "error handling", "validation", "authentication" | **semantic_search** → query_graph → read_file |
| 意图查询 | "where is X done", "how does Y work", "find Z logic" | **semantic_search** → query_graph → read_file |
| 目的查询 | "what is the purpose of...", "why does..." | **semantic_search** → query_graph → read_file |

**直接使用 query_graph 的情况**：

| 问题模式 | 示例 | 工具选择 |
|---------|------|---------|
| 已知具体名称 | "What does function X call?" | **query_graph** 直接使用 |
| 结构查询 | "List methods of User class" | **query_graph** 直接使用 |
| 路径查询 | "Show files in folder src/utils" | **query_graph** 直接使用 |

#### 6.6.3 推荐的混合方法（适用于大多数查询）

对于复杂查询，Agent 遵循以下**标准工具链**：

```
用户问题
    ↓
1. semantic_search (按意图/含义查找)
   - 使用聚焦的查询词（不要太宽泛）
   - 返回相关代码元素
   ↓
2. query_graph (探索结构关系)
   - 基于语义搜索的结果
   - 探索函数调用关系
   - 查找相关类和方法
   ↓
3. read_file (读取实际源代码)
   - 自动读取主要文件（如 main.py）
   - 检查实际实现细节
   - 不需要用户许可
   ↓
4. 综合分析并生成答案
   - 解释代码的功能
   - 说明执行流程
   - 引用来源（文件路径）
```

**示例：查询 "main entry point and what it calls"**

```
1. semantic_search("main entry startup")
   返回: [main_app, initialize, setup...]

2. query_graph("查找 main_app 调用的函数")
   返回: [main_app → initialize → start_server]

3. read_file("src/main.py")
   读取: 实际的启动代码实现

4. 综合分析
   - 总结执行流程
   - 说明初始化步骤
   - 引用相关文件和行号
```

#### 6.6.4 深度代码分析流程

当用户询问某个组件的详细信息时：

```
用户问题: "解释 authentication 模块如何工作"
    ↓
a. 检查文档
   read_file("README.md")
   read_file("docs/authentication.md")
    ↓
b. 检查配置
   read_file("config/settings.py")
   read_file("pyproject.toml")
    ↓
c. 深入源代码
   semantic_search("authentication implementation")
   query_graph("find authentication classes")
   read_file("src/auth/auth_manager.py")
    ↓
d. 综合分析
   - 不只是描述文件
   - 解释代码**做什么**
   - 综合所有信息来源
```

#### 6.6.5 入口点查询的特殊流程

对于入口点相关的问题，Agent 有更严格的流程：

```
用户问题: "程序的入口点是什么？"
    ↓
a. semantic_search("main entry startup")
   → 找到候选函数
    ↓
b. query_graph("查找函数调用关系")
   → 探索入口点的调用链
    ↓
c. 自动读取主文件
   read_file("main.py")  ← 强制执行，无需用户许可
    ↓
d. 识别实际的启动代码
   - 查找 `if __name__ == "__main__"`
   - 查找 `main()` 函数
   - 查找 CLI 命令
    ↓
e. 检查 CLI 框架
   - 如果使用 typer/click/argparse
   → 读取相关命令函数
    ↓
f. 区分真实入口点
   - 区分辅助函数和真实入口
   - 找到实际的应用启动点
    ↓
g. 展示完整执行流程
   - 从入口点到初始化
   - 不显示所有细节
   - 专注于关键流程
```

#### 6.6.6 Token 管理优先级

为了高效使用上下文，Agent 优先处理：

```
优先级 1: 最相关的发现
   - 聚焦的语义搜索查询
   - 读取关键文件部分
   ↓
优先级 2: 高效的信息获取
   - 使用 offset/limit 读取文件片段
   - 总结大结果而非完整内容
   ↓
优先级 3: 避免不必要的操作
   - 不读取不相关的文件
   - 不执行过于宽泛的搜索
   - 及时总结和返回答案
```

#### 6.6.7 工具调用优先级总结

| 优先级 | 工具 | 触发条件 |
|-------|------|---------|
| **P0** | analyze_document | 目标是 PDF 等文档 |
| **P0** | semantic_search | 意图性问题、入口点、功能性查询 |
| **P1** | query_graph | 已知名称的结构查询 |
| **P1** | query_graph | 语义搜索后的结构探索 |
| **P2** | read_file | 读取源代码文件 |
| **P2** | read_file | 语义搜索和图查询后读取实际代码 |
| **P3** | create_file | 修改代码前的文件创建 |
| **P3** | replace_code | 修改代码（需确认） |
| **P3** | execute_shell_command | 执行命令（需确认） |
| **P4** | list_directory | 列出目录内容 |
| **P4** | code_retrieval | 通过 qualified_name 获取代码 |

#### 6.6.8 完整优先级决策树

```
用户提问
    ↓
判断问题类型
    │
    ├─ 文档相关?
    │   └─ analyze_document (P0)
    │
    ├─ 意图/目的/功能性问题?
    │   ├─ semantic_search (P0)
    │   ├─ query_graph (P1)
    │   └─ read_file (P2)
    │
    ├─ 已知名称的结构查询?
    │   └─ query_graph (P1) → read_file (P2)
    │
    ├─ 入口点查询?
    │   ├─ semantic_search (P0)
    │   ├─ query_graph (P1)
    │   ├─ read_file main.py (P2) 强制执行
    │   └─ read_file CLI sections (P2)
    │
    ├─ 需要修改代码?
    │   ├─ 先探索代码库
    │   │   ├─ semantic_search (P0)
    │   │   └─ read_file (P2)
    │   └─ create_file/replace_code (P3, 需确认)
    │
    ├─ 需要执行命令?
    │   └─ execute_shell_command (P3, 需确认)
    │
    └─ 需要列出目录?
        └─ list_directory (P4)
```

### 6.7 工具错误处理

每个工具都有完善的错误处理机制：

```python
# 示例：query_graph 的错误处理
try:
    cypher_query = await cypher_gen.generate(natural_language_query)
    results = ingestor.fetch_all(cypher_query)
    return QueryGraphData(query_used=cypher_query, results=results, summary=...)
except ex.LLMGenerationError as e:
    # Cypher 生成失败
    return QueryGraphData(
        query_used=QUERY_NOT_AVAILABLE,
        results=[],
        summary=QUERY_SUMMARY_TRANSLATION_FAILED.format(error=e)
    )
except Exception as e:
    # 数据库查询错误
    return QueryGraphData(
        query_used=cypher_query,
        results=[],
        summary=QUERY_SUMMARY_DB_ERROR.format(error=e)
    )
```

Agent 会根据返回的错误信息调整策略：
- 如果查询失败，尝试其他工具
- 如果文件不存在，提示用户或尝试其他路径
- 如果工具执行成功，继续使用结果生成答案

## 7. 总结

整个问答流程的核心是：

1. **初始化阶段**：创建包含多种工具的 RAG Agent
2. **循环等待**：持续等待用户输入
3. **智能路由**：Agent 根据 Prompt 规则选择合适的工具
4. **工具链**：可以组合多个工具（语义搜索 → 图查询 → 文件读取）
5. **安全确认**：危险操作需要用户确认
6. **综合回答**：基于工具返回的客观信息生成答案

这个设计确保了答案的准确性和可追溯性，同时提供了灵活的工具组合能力来应对各种复杂问题。