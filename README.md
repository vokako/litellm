# LiteLLM WebSearch Streaming Fix 验证

## PR

https://github.com/BerriAI/litellm/pull/27449

## 问题说明

### 问题 1: WebSearch Streaming 返回空流

**现象**: 通过 `/v1/messages` 发送 `stream=True` + `web_search` tool 的请求，客户端收不到任何 SSE 事件，text 为空。

**根因**: `websearch_interception` 回调在内部将 `stream=True` 转为 `stream=False` 来执行搜索。agentic loop 完成后返回的是一个普通 dict，但客户端期望的是 SSE 流。代码中将 dict 包装为 `FakeAnthropicMessagesStreamIterator` 的逻辑只在"模型没有调用 web_search tool"时执行，当模型实际调用了 tool 并走了 agentic loop 路径时，dict 被直接返回，导致空流。

**修复**: 在 agentic loop 的所有 return 路径上，检查 `websearch_interception_converted_stream` 标志，将 dict 包装为 fake stream iterator。

### 问题 2: Citations 不工作（Bedrock）

**现象**: 通过 LangChain ChatOpenAI 发送带 `document` blocks + `citations: {enabled: true}` 的请求，Bedrock 模型回复"没有收到文档"。

**根因**: 配置使用 `bedrock/` 前缀时走的是 Bedrock **Converse API**，该 API 不支持 Anthropic 的 citation 功能，document blocks 在转换过程中丢失了 `title` 和 `citations` 字段。

**修复**: 配置改为 `bedrock/invoke/` 前缀 + `us-east-1` region，走 Anthropic Messages API（Invoke）路径，原生支持 document blocks 和 citations。

## 前置条件

- AWS 凭证已配置（能访问 Bedrock）
- 环境变量 `TAVILY_API_KEY` 已设置

## 步骤

### 1. 初始化项目并安装依赖

```bash
cd verify
uv init --name litellm-verify
uv add 'litellm[proxy] @ git+https://github.com/vokako/litellm.git@fix/websearch-streaming-v2'
uv add anthropic langchain-openai langchain-core
```

### 2. 启动 LiteLLM Proxy

```bash
uv run litellm --config litellm_config.yaml --port 4002
```

### 3. 运行测试（另开终端）

```bash
uv run python test_streaming_websearch.py
uv run python test_citations.py
```

### 4. 预期结果

**test_streaming_websearch.py:**
- ✅ 文本流式输出，显示 `[PASS]`
- ❌ `[FAIL] text_length=0` 说明 fix 未生效

**test_citations.py:**
- ✅ `citations_raw count: N`（N > 0），显示 `[PASS]`
- ❌ `citations_raw: MISSING` 说明 invoke 路径未生效

## 对比官方版本（可选）

将 `uv add` 改为 `uv add 'litellm[proxy]'`（不带 git 地址），streaming 测试应该 FAIL。
