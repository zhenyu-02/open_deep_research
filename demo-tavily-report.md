**List of Queries and Tool Calls Made**

1. **tavily_search** — Queried: `"LangChain Open Deep Research"`, `"github langchain-ai open_deep_research"`, `"LangChain open deep research architecture"`
2. **tavily_search** — Queried: `"open_deep_research latest updates June 2026"`, `"github langchain-ai open_deep_research issues limitations"`

---

**Fully Comprehensive Findings**

## 1. Purpose and Overview

**Open Deep Research** is an open-source, configurable deep research agent built with LangGraph by LangChain. It is designed to perform autonomous web research and generate comprehensive reports. The project is hosted at `langchain-ai/open_deep_research` on GitHub and is licensed under the MIT License [3][6].

Deep research has broken out as one of the most popular agent applications. This is a simple, configurable, fully open source deep research agent that works across many model providers, search tools, and MCP servers, with performance on par with popular deep research agents [3][6].

The system is designed to address the challenge that research is an open-ended task — the best strategy to answer a user request can't be easily known in advance. It is built to handle different request types such as comparisons, listings/rankings, or validation questions [1][4].

The project draws inspiration from deep research products by OpenAI, Anthropic, Perplexity, and Google, as well as other open-source implementations [6][9].

A free course on building open deep research is available via LangChain Academy (released August 14, 2025) [3][6].

---

## 2. Architecture

The system follows a **three-phase architecture** [1][2][9]:

### Phase 1: Scoping (Brief Generation)
- Gathers user context through optional clarifying questions (the LLM determines if clarification is needed) [1][2][9].
- The `clarify_with_user` node optionally asks clarifying questions, then `write_research_brief` transforms the conversation into a structured research brief [4].
- Compresses the chat history into a single research brief using structured LLM output [1][2].
- This brief serves as the "north star" / focused target for all subsequent research and writing [1][2][4].

### Phase 2: Research
- A **supervisor agent** analyzes the research brief and delegates research tasks to **sub-agents** with isolated context windows [1][2][4].
- Sub-agents conduct tool-calling loops (using default Tavily search or MCP tools like flight/hotel search APIs) [1][2].
- Sub-agents use iterative web searches, strategic reflection (via `think_tool`), budget-aware execution, and intelligent termination [4].
- Each sub-agent runs in its own isolated context window, which prevents "context clash" and token bloat that plague single-agent systems handling multiple topics [1][4].
- Research findings are **compressed/cleaned** via an additional LLM call — this is framed as a "cleaning step" not a "summary" to preserve all relevant information and sources while removing token bloat [1][2].
- The supervisor reviews findings and decides whether to spawn more sub-agents or conclude research [1][2].
- The supervisor really has a simple job. It delegates tasks to the right number of sub agents to research topics in depth and in parallel. This is really just a context engineering technique [2].
- A multi-agent supervisor allows the system to tune research depth — spawning sub-agents for complex requests or using a single thread for simple ones [1][4].

### Phase 3: Report Writing
- When the supervisor deems findings sufficient, a **single LLM call** produces the final report in one-shot using the research brief and all condensed research findings [1][2][4].
- Earlier attempts at parallel section-writing produced disjointed reports; writing is now done in one-shot after research [1][2].
- One-shot generation produces more cohesive reports with inline citations [2][4].

### Key Design Patterns

**Reflection Pattern:** Agents evaluate their own output and use feedback to refine responses iteratively. The LLM generates a response, acts as its own critic, and produces improved versions until quality standards are met [9].

**Manual Tool Use Pattern (vs. Standard ReACT):** Instead of automatic tool execution, Open Deep Research uses manual tool orchestration. Tool schemas are defined without implementations, bound to the LLM, and tool calls are handled manually — spawning entire sub-agents as "tools." Key benefits include subgraph invocation, context efficiency (returns compact "Research completed" instead of 10,000-token reports), flexible routing, and parallel coordination [9].

### Key Lessons Learned (from LangChain blog)
- **Multi-agent should only be used for easily parallelized tasks** (e.g., research, not writing). Earlier attempts at parallel section-writing produced disjointed reports; writing is now done in one-shot after research [1][4].
- **Context isolation of sub-topics during research** can avoid various long context failure modes [1][4].
- **A multi-agent supervisor allows for flexibility of search strategy** [1].
- **Context engineering has many practical benefits.** It saves tokens, helps avoid context window limits, and helps stay under model rate limits. The chat history is compressed into a research brief, which prevents token-bloat from prior messages. Sub-agents prune their research findings to remove irrelevant tokens and information before returning to the supervisor [1][4].

### Step-by-Step Execution Flow (13 Steps, per Bolshchikov deep-dive)
1. **User Question** — LLM decides if clarification is needed
2. **User Responds to Clarifying Question** — LLM returns structured output with `need_verification` flag; proceeds to brief writer or asks more questions
3. **Generate Brief** — LLM generates research brief; initializes supervisor subgraph state
4. **Supervisor Reflects** — Supervisor uses `think_tool` (reflection) and checks research iteration count
5. **Supervisor Initiates Research** — LLM returns call to `conduct_research` tool with topic(s); can spawn multiple sub-agents in parallel
6. **Research Sub-Agent Spawned** — Subgraph with three nodes: `researcher`, `research_tools`, `compress_research`
7. **Research Agent Initiates Search** — LLM call returns `web_search` tool call with queries
8. **Multiple Parallel Searches** — Uses Tavily search; results are summarized to manage context size
9. **Reflect on Results** — Research node invokes `think_tool` to decide if results are sufficient
10. **Research Completed** — Calls `research_complete` tool; results compressed and returned to supervisor
11. **Supervisor Re-evaluates** — Calls `think_tool` to decide next actions based on received research
12. **Research Complete** — Supervisor calls `research_complete` when sufficient information gathered
13. **Generate Final Report** — Final LLM call generates report from message history, supervisor_messages, brief, and research results

[9]

### Architectural Approaches Compared (from video)
- **Tool-calling agents** (e.g., Hugging Face's open deep researcher, OpenAI/Gemini deep research): LLM with bound tools that can be called in any order; more flexible but potentially less reliable [5][10].
- **Workflows** (e.g., LangChain's Open Deep Research, other popular open-source implementations): Pre-defined control flow with constrained steps; more scaffolding for reliability and lower token usage, but less flexible [5][10].
- "There's always a trade-off between using an open-ended tool calling agent versus what I consider workflow here; often the benefit of workflow is that you provide more scaffolding for reliability and often lower token usage but it can lack some flexibility" [5][10].

### State Management
Built on LangGraph's StateGraph with TypedDict and Pydantic model states [4].

---

## 3. Supported Model and Search Configuration

### Model Support
- Uses `init_chat_model()` API to support various LLM providers [3][6].
- Uses separate models for different pipeline steps [3][6]:
  - **Summarization** (default: `gpt-4.1-mini`) — for summarizing individual search results [3][6]
  - **Research** (default: `gpt-4.1`) — for research sub-agents [3][6]
  - **Compression** (default: `gpt-4.1`) — for cleaning/compressing findings [3][6]
  - **Final Report** (default: `gpt-4.1`) — for one-shot report generation [3][6]
- Added GPT-5 support on August 7, 2025 [3][6].
- Supports OpenAI (GPT-4.1 default), Anthropic Claude, and others [4].
- All models must support structured outputs and tool calling [4].
- The planner model can be configured (supports DeepSeek, O3 mini, etc.) [5][10].

### Search API / Tool Configuration
- **Default:** Tavily search API [3][6].
- **Full MCP compatibility** — supports Model Context Protocol (MCP) servers as research tools [1][2][3].
- **Native web search** support for Anthropic/OpenAI models [3][6].
- Supports multiple search APIs: Tavily, Perplexity, Exa, ArXiv, PubMed, LinkUp, DuckDuckGo, GoogleSearch [4].
- Also supports SerpAPI and Firecrawl [5][10].

### Key Configuration Parameters
- `max_concurrent_research_units` (default 5) [4]
- `max_researcher_iterations` (default 3) [4]
- `max_react_tool_calls` (default 5) [4]
- Search depth, number of queries per iteration, and total iterations [5][10]

### Local vs. Cloud Deployment
- Can be run locally via LangGraph server using `uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking` [3][4].
- Deployable to LangGraph Platform (hosted deployment) [3][6].
- **Open Agent Platform (OAP)** at `oap.langchain.com` offers a UI for non-technical users to configure and test agents without local setup [2][3][6].
- LangGraph Studio for local testing (both Mac and Windows) [3][7].

### Cost Comparison
- Most reports generated with Open Deep Research cost **less than $0.50** [5][10].
- Proprietary services: OpenAI Pro and Gemini Pro cost ~$200/month subscriptions [5][10].
- Users can easily configure to make it cheaper using different models [5][10].

---

## 4. Recent Project Status (as of June 2026)

### GitHub Statistics
- **Repository:** `langchain-ai/open_deep_research` (Public, MIT License) [3][6]
- **Stars:** 11.8k [3][6]
- **Forks:** 1.7k [3][6]
- **Contributors:** 26 [3][6]
- **Language:** Python (69.6%), Jupyter Notebook (30.4%) [3][6]

### Timeline of Key Updates
- **August 14, 2025:** Free course on building open deep research released [3][6]
- **August 7, 2025:** Added GPT-5 support; updated Deep Research Bench evaluation with GPT-5 results [3][6]
- **August 2, 2025:** Achieved #6 ranking on Deep Research Bench Leaderboard with overall score of 0.4344 [3][6]
- **July 30, 2025:** Blog post on evolution from original implementations [3][6]
- **July 16, 2025:** Blog and video overview published [3][6]
- **February 20, 2025:** Earlier video overview published demonstrating the tool in LangGraph Studio [5][10]

### Evaluation Results (Deep Research Bench)
Benchmark with **100 PhD-level research tasks** (50 English, 50 Chinese) across **22 fields**. Uses **RACE score** (LLM-as-a-judge with Gemini) [3][6].

| Model | RACE Score | Total Tokens | Cost |
|-------|-----------|-------------|------|
| GPT-5 | 0.4943 | 204,640,896 | — |
| Claude Sonnet 4 | 0.4401 | 138,917,050 | $187.09 |
| Defaults (GPT-4.1) | 0.4309 | 58,015,332 | $45.98 |
| Deep Research Bench Submission | 0.4344 | 207,005,549 | $87.83 |

[3][6]

As of May 11, 2026, the official evaluator for Deep Research Bench switched to **GPT-5.5** (after Google's Gemini-2.5-Pro deprecation announcement) [2].

### Legacy Implementations
The `src/legacy/` folder contains two earlier implementations that provide alternative approaches [3][6]:
1. **Workflow Implementation** (`legacy/graph.py`): Plan-and-execute with human-in-the-loop planning, sequential processing, interactive control [3][6].
2. **Multi-Agent Implementation** (`legacy/multi_agent.py`): Supervisor-researcher architecture, parallel processing, speed-optimized, MCP support [3][6].

### Related Tutorial Repository
The **`langchain-ai/deep_research_from_scratch`** repository provides 5 tutorial notebooks that progressively construct a production-ready deep research system [6][9]:
1. User Clarification and Brief Generation (`1_scoping.ipynb`)
2. Research Agent with Custom Tools (`2_research_agent.ipynb`)
3. Research Agent with MCP (`3_research_agent_mcp.ipynb`)
4. Research Supervisor (`4_research_supervisor.ipynb`)
5. Full Multi-Agent Research System (`5_full_agent.ipynb`)

### Related Local-Only Variant
The **`langchain-ai/local-deep-researcher`** repository is a fully local web research assistant that uses LLMs via Ollama or LMStudio. It uses DuckDuckGo as the default web search (no API key required). It is inspired by IterDRAG [7]. **Warning (8/6/25):** The `gpt-oss` models do not support JSON mode in Ollama; use `use_tool_calling` in configuration instead [7].

---

## 5. Known Issues and Limitations

### Identified GitHub Issues
- **Bug:** `legacy/multi_agent.py` can treat partial section completion as full research completion (Issue #284) [7]
- **Bug:** `supervisor_tools` treats any child `ConductResearch` exception as successful research completion (Issue #283) [7]
- **Missing feature:** No `max_revisions` limit in the feedback-to-report-plan revision loop (Issue #269) [7]
- **Bug:** Broken links in README.md (Issue #268) [7]
- **Bug:** Configuration errors (Issue #267) [7]
- **Bug:** `compress_research` removes recent messages instead of older ones on token limit (Issue #252) [7]
- **Unclear customization:** Search provider customization guidance unclear (Issue #250) [7]
- **Missing features:** Customizable report templates (Issue #233), citation inconsistency in `compress_research_system_prompt` (Issue #232) [7]

### Enterprise Deployment Gaps
Per the Medium analysis (Dec 11, 2025) by Tuhin Sharma (Technical Advisor, Data & AI @ Red Hat) [4]:
- The framework is **not production-ready out of the box** [4].
- Missing infrastructure includes: Dockerfile/Kubernetes manifests, CI/CD pipelines, rate limiting, structured logging, Prometheus metrics, and input sanitization for prompt injection [4].
- Enterprise teams should expect **4-8 weeks of hardening work** to add rate limiting, caching, monitoring, and security controls appropriate for their environments [4].
- Recommended implementation roadmap [4]:
  - **Phase 1 (Pilot, 2-4 weeks):** Deploy with LangSmith tracing, evaluate performance
  - **Phase 2 (Integration, 4-8 weeks):** Connect enterprise search via MCP, implement rate limiting
  - **Phase 3 (Production, 4-8 weeks):** Deploy via LangGraph Platform or Kubernetes, add caching, monitoring
  - **Phase 4 (Scale, ongoing):** Optimize model selection, cost dashboards, domain-specific integrations

### Integration Challenges
- A backend developer reported difficulty integrating the open-deep-research package into existing backends, noting it differs from standard LangChain guides which provide clear APIs like `.invoke()`. The source code structure does not offer familiar API methods [8].

### Architecture-Specific Limitations
- **Multi-agent complexity:** Multi-agents are hard to coordinate, and can perform poorly if writing sections of the report in parallel [1][4].
- **Model requirements:** All models must support structured outputs and tool calling [4].
- **Local model limitations:** The `gpt-oss` models do not support JSON mode in Ollama for the local-deep-researcher variant [7].
- The research sub-agent is a subgraph that is invoked dynamically based on the LLM response from the conduct_research tool; therefore, it's not visible in LangGraph Studio [9].

### Limitations of the Evidence
- The most recent source specifically about Open Deep Research is from November 2025 (the Bolshchikov internals deep-dive) and December 2025 (the Medium enterprise analysis). No sources from June 2026 specifically mention new Open Deep Research updates, though the GitHub repository remains actively maintained with 11.8k stars [3][6].
- The deep research benchmark evaluator was updated to GPT-5.5 as of May 11, 2026, but Open Deep Research's ranking was last reported at #6 (August 2025) — current ranking is unknown [2][3].
- Several GitHub issues remain open, but the overall project status (whether these have been addressed) is unclear without more recent commit-level data [7].
- The integration difficulty reported in the LangChain forum has no solution posted [8].
- No formal security audit or production-readiness assessment from LangChain itself could be found — the enterprise gap analysis comes from a third-party Medium article [4].

---

**List of All Relevant Sources (with citations in the report)**

[1] Open Deep Research — LangChain Blog: https://www.langchain.com/blog/open-deep-research

[2] Open Deep Research Agent — YouTube (LangChain, July 16, 2025): https://www.youtube.com/watch?v=agGiWUpxkhg

[3] langchain-ai/open_deep_res