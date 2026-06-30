I'll start by searching for information about LangChain Open Deep Research from multiple angles.
Search results: 



--- SOURCE 1: Open Deep Research - LangChain ---
URL: https://www.langchain.com/blog/open-deep-research

SUMMARY:
<summary>
This webpage from the LangChain blog introduces **Open Deep Research**, an open-source, configurable deep research agent built with LangGraph. It addresses the challenge that research is an open-ended task requiring flexible strategies. The system uses a three-phase architecture:

1. **Phase 1: Scope** — Gathers user context through user clarification and generates a focused research brief.
2. **Phase 2: Research** — A supervisor agent delegates research tasks to sub-agents with isolated context windows. Sub-agents use search/MCP tools and return cleaned findings. The supervisor can iterate, spawning further sub-agents if more depth is needed.
3. **Phase 3: Report Writing** — When the supervisor deems findings sufficient, a final LLM call produces the report in one shot.

**Key lessons learned:**
- Multi-agent should only be used for easily parallelized tasks (e.g., research, not writing). Earlier attempts at parallel section-writing produced disjointed reports; writing is now done in one-shot after research.
- Multi-agent is useful for isolating context across sub-topics, preventing context clash and token bloat that plague single-agent systems handling multiple topics.
- A multi-agent supervisor allows the system to tune research depth — spawning sub-agents for complex requests or using a single thread for simple ones.
- Context engineering (compressing chat history into a brief, pruning sub-agent findings) is critical to mitigate token bloat, save costs, and avoid context window limits.

The project is available on GitHub and can be run locally with LangSmith Studio. A course is also offered via LangChain Academy.
</summary>

<key_excerpts>
"Multi-agents are hard to coordinate, and can perform poorly if writing sections of the report in parallel. We restrict multi-agent to research, and write the report in one-shot.", "Context isolation of sub-topics during research can avoid various long context failure modes.", "A multi-agent supervisor allows for flexibility of search strategy.", "Context engineering has many practical benefits. It saves tokens, helps avoid context window limits, and helps stay under model rate limits.", "We compress the chat history into a research brief, which prevents token-bloat from prior messages. Sub-agents prune their research findings to remove irrelevant tokens and information before returning to the supervisor."
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 2: Open Deep Research - YouTube ---
URL: https://www.youtube.com/watch?v=agGiWUpxkhg

SUMMARY:
<summary>
# Open Deep Research Agent - Summary

This video (July 16, 2025) from LangChain presents their open-source Deep Research agent built on LangGraph. The agent is highly configurable, supports custom LLMs, data sources, and MCP servers, and can be run locally or tested via Open Agent Platform.

## Three-Phase Architecture

**1. Scoping Phase:**
- Agent asks clarifying questions to gather missing context from users
- Compresses chat history into a single research brief using structured LLM output
- This brief serves as the focused target for all subsequent research and writing

**2. Research Phase:**
- A supervisor analyzes the research brief and delegates subtopics to parallel sub-agents (or a single thread if splitting isn't appropriate)
- Each sub-agent runs a tool-calling loop (using default Tavily search or MCP tools like flight/hotel search APIs)
- Sub-agents use a "research complete" tool to signal completion
- A compression/cleaning step condenses messy tool outputs into clean mini-reports, preserving all relevant information and sources
- The supervisor reviews findings and decides whether to spawn more sub-agents or conclude research

**3. Report Writing Phase:**
- Final report is generated in a single shot using all condensed research findings
- Parallel report writing was found to produce disjointed results; one-shot generation produces more cohesive reports
- The compression step prevents context window overload from messy tool outputs

## Running Locally
1. Clone the Open Deep Research repository
2. Install dependencies in a virtual environment
3. Set API keys for models (OpenAI by default), Tavily search, and LangSmith
4. Customize prompts and architecture in deep_researcher.py
5. Run `langgraph dev` to start LangGraph Studio

## Configuration Options
- Choose search tools (Tavily, model-native search, or MCP servers)
- Choose different models for different pipeline steps (summarization, research, report writing)
- Open Agent Platform offers a UI for testing without local setup

## Key Design Philosophy
- Context engineering: splitting research into parallel subtopics with separate context windows keeps each sub-agent focused
- Cleaning step (not summarizing) preserves all relevant data while removing token bloat
- Supervisor mimics human research behavior: surface-level or deep dives as needed
</summary>

<key_excerpts>
"Open Deep Research is an open source agent that is built on LangGraph and can be hooked up to your own data sources, LLMs, and MCP servers.", "Instead of reasoning about the research brief itself as one whole, the agent can split it into individual pieces whenever it's applicable. The benefit here is that each sub agent conducts research on a single subtopic siloed in its own separate context window.", "When I wrote the system prompt, I really emphasized that I wanted to preserve all relevant information and sources. I framed this to the agent as a cleaning step rather than a summary or a synthesis to really try and deter it from accidentally leaving out valuable information.", "We found that parallel report writing was pretty finicky. Trying to write sections of a report in parallel led to disjointed and not very cohesive reports. We found that the best approach was to oneshot the report generation with all of our condensed research findings.", "The supervisor really has a simple job. It delegates tasks to the right number of sub agents to research topics in depth and in parallel. This is really just a context engineering technique."
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 3: langchain-ai/open_deep_research - GitHub ---
URL: https://github.com/langchain-ai/open_deep_research

SUMMARY:
<summary>
# 🔬 Open Deep Research - GitHub Repository Summary

**langchain-ai/open_deep_research** is an open-source, configurable deep research agent that works across multiple model providers, search tools, and MCP servers. The repository has 11.8k stars, 1.7k forks, and 26 contributors. It is licensed under MIT.

## Key Features
- Simple, fully open source deep research agent compatible with many LLM providers, search APIs, and MCP servers
- Performance on par with popular deep research agents (Deep Research Bench leaderboard)

## Recent Updates (as of June 2026)
- **August 14, 2025**: Free course on building open deep research available
- **August 7, 2025**: Added GPT-5 support; updated Deep Research Bench evaluation with GPT-5 results
- **August 2, 2025**: Achieved #6 ranking on Deep Research Bench Leaderboard with overall score of 0.4344
- **July 30, 2025**: Blog post on evolution from original implementations
- **July 16, 2025**: Blog and video overview published

## Quickstart
1. Clone repo, activate virtual environment with `uv venv`
2. Install dependencies via `uv sync`
3. Set up `.env` file from `.env.example`
4. Launch LangGraph server locally with `uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking`

## Configurations
- **LLM**: Supports various providers via `init_chat_model()` API. Uses separate models for summarization (default: `gpt-4.1-mini`), research (default: `gpt-4.1`), compression (default: `gpt-4.1`), and final report writing (default: `gpt-4.1`)
- **Search API**: Default is Tavily search API; supports MCP compatibility and native web search for Anthropic/OpenAI

## Evaluation (Deep Research Bench)
Benchmark with 100 PhD-level research tasks (50 English, 50 Chinese) across 22 fields. Uses RACE score (LLM-as-a-judge with Gemini).

### Top Results
| Model | RACE Score | Total Tokens |
|-------|-----------|-------------|
| GPT-5 | 0.4943 | 204,640,896 |
| Claude Sonnet 4 | 0.4401 | 138,917,050 |
| Defaults (GPT-4.1) | 0.4309 | 58,015,332 |
| Deep Research Bench Submission | 0.4344 | 207,005,549 |

## Deployments
- LangGraph Studio (local testing)
- LangGraph Platform (hosted deployment)
- Open Agent Platform (OAP) - UI for non-technical users to configure agents

## Legacy Implementations
Two earlier approaches in `src/legacy/`:
1. **Workflow Implementation** (`legacy/graph.py`): Plan-and-execute with human-in-the-loop planning, sequential processing, interactive control
2. **Multi-Agent Implementation** (`legacy/multi_agent.py`): Supervisor-researcher architecture, parallel processing, speed-optimized, MCP support
</summary>

<key_excerpts>
Deep research has broken out as one of the most popular agent applications. This is a simple, configurable, fully open source deep research agent that works across many model providers, search tools, and MCP servers., Achieved #6 ranking on the Deep Research Bench Leaderboard with an overall score of 0.4344., Open Agent Platform (OAP) is a UI from which non-technical users can build and configure their own agents., The src/legacy/ folder contains two earlier implementations that provide alternative approaches to automated research.
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 4: Building Enterprise Deep Research Agents with LangChain's Open ... ---
URL: https://medium.com/@tuhinsharma121/building-enterprise-deep-research-agents-with-langchains-open-deep-research-63e7cdb80a58

SUMMARY:
<summary>
# Building Enterprise Deep Research Agents with LangChain's Open Deep Research

**Author:** Tuhin Sharma (Technical Advisor, Data & AI @ Red Hat)  
**Date:** Dec 11, 2025

This article provides a comprehensive technical analysis of LangChain's **open_deep_research** framework, which ranked **#6 on the Deep Research Bench Leaderboard** (RACE score of 0.4344). The framework is MIT-licensed and offers production-grade multi-agent research capabilities at a fraction of the cost of commercial alternatives.

## Architecture (3 Phases)

**Phase 1: Scoping** — User clarification + research brief generation. The `clarify_with_user` node optionally asks clarifying questions, then `write_research_brief` transforms the conversation into a structured research brief.

**Phase 2: Research** — A supervisor-subagent pattern where a lead supervisor spawns parallel researcher agents with isolated context windows. Each researcher uses iterative web searches, strategic reflection (via `think_tool`), budget-aware execution, and intelligent termination. Research findings are compressed into clean summaries with citations preserved.

**Phase 3: Report Writing** — One-shot report generation from compressed findings using a single agent, ensuring coherent output with inline citations and multilingual support.

## Core Technical Details

- **Configuration:** Supports multiple search APIs (Tavily, Perplexity, Exa, ArXiv, PubMed, LinkUp, DuckDuckGo, GoogleSearch) and LLM providers (OpenAI GPT-4.1 default, Anthropic Claude).
- **Key Configurables:** `max_concurrent_research_units` (default 5), `max_researcher_iterations` (default 3), `max_react_tool_calls` (default 5).
- **State Management:** Built on LangGraph's StateGraph with TypedDict and Pydantic model states.
- **All models must support structured outputs and tool calling.**

## Critical Gaps for Enterprise Deployment

The framework is **not production-ready out of the box**. Missing infrastructure includes: Dockerfile/Kubernetes manifests, CI/CD pipelines, rate limiting, structured logging, Prometheus metrics, and input sanitization for prompt injection. Enterprise teams should expect **4-8 weeks of hardening work**.

## Quick Start

```bash
git clone https://github.com/langchain-ai/open_deep_research.git
cd open_deep_research
uv venv && source .venv/bin/activate
uv sync
cp .env.example .env # Set TAVILY_API_KEY, OPENAI_API_KEY
uvx --from "langgraph-cli[inmem]" --python 3.11 langgraph dev --allow-blocking
```

## Implementation Roadmap for Enterprises

- **Phase 1 (Pilot, 2-4 weeks):** Deploy with LangSmith tracing, evaluate performance.
- **Phase 2 (Integration, 4-8 weeks):** Connect enterprise search via MCP, implement rate limiting.
- **Phase 3 (Production, 4-8 weeks):** Deploy via LangGraph Platform or Kubernetes, add caching, monitoring.
- **Phase 4 (Scale, ongoing):** Optimize model selection, cost dashboards, domain-specific integrations.

**Conclusion:** The combination of MIT licensing, competitive benchmark scores, and multi-provider support makes it the leading open-source choice for research automation, but requires significant hardening for production.
</summary>

<key_excerpts>
LangChain's open_deep_research framework offers production-grade multi-agent research capabilities under MIT license — delivering competitive performance at a fraction of commercial alternatives' cost., The framework's supervisor-researcher architecture separates parallel information gathering from coherent report synthesis, achieving a RACE score of 0.4344 while allowing full customization of LLM providers, search APIs, and integration points., The combination of MIT licensing, competitive benchmark scores (#6 on Deep Research Bench), and multi-provider support makes it the leading open-source choice for organizations building research automation., However, the framework is not production-ready out of the box. Enterprise teams should expect 4-8 weeks of hardening work to add rate limiting, caching, monitoring, and security controls appropriate for their environments.
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 5: Open Deep Research ---
URL: https://www.youtube.com/watch?v=2mSNIX-l_Zc

SUMMARY:
<summary>
This video from LangChain (published February 20, 2025) introduces "Open Deep Research," an open-source AI assistant for autonomous web research and report generation. Lance from LangChain demonstrates the tool in LangGraph Studio and discusses the broader landscape of deep research systems.

**Key Architecture:**
The system has two main phases:
1. **Planning Phase**: The assistant generates a report plan with sections based on initial web research. A human-in-the-loop feedback mechanism allows users to review and modify the plan before proceeding.
2. **Deep Research Phase**: For each section, the system generates search queries, runs web searches, writes content, reflects on its completeness, and iterates as needed—all in parallel across sections.

**Architectural Approaches Compared:**
- **Tool-calling agents** (e.g., Hugging Face's open deep researcher, likely OpenAI/Gemini deep research): LLM with bound tools that can be called in any order; more flexible but potentially less reliable.
- **Workflows** (e.g., LangChain's Open Deep Research, other popular open-source implementations): Pre-defined control flow with constrained steps; more scaffolding for reliability and lower token usage, but less flexible.

**Configurability Advantages:**
Users can customize: report structure/outline, planning model (supports DeepSeek, O3 mini), writer model, search API (Tavily, Perplexity, SerpAPI, Firecrawl), search depth, number of queries per iteration, and total iterations.

**Cost Comparison:**
- Open-source implementation: Most reports cost less than $0.50
- Proprietary services: $200/month subscriptions

**Evaluations:**
- Open AI deep research scores well on GAIA benchmark
- Hugging Face's approach scored 55% on GAIA
- OpenAI deep research outperforms O3 alone on Humanities Last Exam (3,000 questions across STEM and Humanities) by a large margin

**Key Takeaways:**
- Open source offers configurability, ability to integrate new models and search tools quickly, and significantly lower cost
- Proprietary offerings (Gemini, OpenAI) provide strong citation functions and crawl many pages by default but are less configurable
- Trade-off between flexibility (agents) vs. reliability and cost-efficiency (workflows)
</summary>

<key_excerpts>
"There's always a trade-off between using an open-ended tool calling agent versus what I consider workflow here; often the benefit of workflow is that you provide more scaffolding for reliability and often lower token usage but it can lack some flexibility.", "The configurability and the customization in the report flow can be drawbacks depending on your need...it's about configurability and ability to use new for example models or new search tools as they come out versus the proprietary offerings here providing very well-sited but less configurable reports.", "Cost is a consideration in this case Pro is $200 a month versus most of the ports I've generated are less than 50 cents and you can easily configure that make it cheaper if you'd like using different models."
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 6: langchain-ai/deep_research_from_scratch - GitHub ---
URL: https://github.com/langchain-ai/deep_research_from_scratch

SUMMARY:
<summary>
This is a GitHub repository page for "langchain-ai/deep_research_from_scratch" — an open-source project by LangChain that builds a deep research agent from scratch. The repository provides 5 tutorial notebooks that progressively construct a production-ready deep research system. Key components include:

1. **User Clarification and Brief Generation** — Scoping research and transforming user input into structured briefs.
2. **Research Agent with Custom Tools** — Building an iterative research agent using external search tools.
3. **Research Agent with MCP** — Integrating Model Context Protocol (MCP) servers as research tools.
4. **Research Supervisor** — Multi-agent coordination for complex research tasks using parallel processing and async orchestration.
5. **Full Multi-Agent Research System** — Complete end-to-end system integrating all components via subgraph composition.

The project draws inspiration from deep research products by OpenAI, Anthropic, Perplexity, and Google, as well as other open-source implementations. It is configurable, allowing users to bring their own models, search tools, and MCP servers. The repository uses an agent-based three-step research process and includes files such as README.md, LICENSE, pyproject.toml, uv.lock, and langgraph.json.
</summary>

<key_excerpts>
Deep research has broken out as one of the most popular agent applications., We built an open deep researcher that is simple and configurable, allowing users to bring their own models, search tools, and MCP servers., Agents are well suited to research because they can flexibly apply different strategies, using intermediate results to guide their exploration., Each notebook builds on the previous concepts, culminating in a production-ready deep research system that can handle complex, multi-faceted research queries with intelligent scoping and coordinated execution.
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 7: langchain-ai/local-deep-researcher - GitHub ---
URL: https://github.com/langchain-ai/local-deep-researcher

SUMMARY:
<summary>
**Local Deep Researcher** is a fully local web research assistant hosted on GitHub by langchain-ai. It uses LLMs via Ollama or LMStudio to automate iterative web research: given a topic, it generates search queries, gathers and summarizes results, reflects on knowledge gaps, generates new queries, and repeats for a configurable number of cycles. The final output is a markdown summary with citations.

**Key Features & Setup:**
- Clone the repo and configure a `.env` file for model selection (Ollama or LMStudio) and search tools.
- Default web search uses DuckDuckGo (no API key). Alternative search tools: SearXNG, Tavily, or Perplexity.
- Supports running via LangGraph Studio UI (both Mac and Windows) or as a Docker container.
- Configuration priority: Environment variables > LangGraph UI config > Default values in the Configuration class.

**How It Works:**
- Inspired by IterDRAG. Decomposes queries into sub-queries, retrieves documents, answers sub-queries, and builds iteratively.
- Uses structured JSON output; models like DeepSeek R1 (1.5B/7B) may have issues and fall back to alternative mechanisms.

**⚠️ Warning (8/6/25):** The `gpt-oss` models do not support JSON mode in Ollama. Use `use_tool_calling` in configuration instead.

**Outputs:** Research summary in markdown with citations. All sources are saved to graph state and visible in LangGraph Studio.

**Deployment:** Docker container available (Ollama must run separately). A TypeScript port (without Perplexity search) is also available.
</summary>

<key_excerpts>
Local Deep Researcher is a fully local web research assistant that uses any LLM hosted by Ollama or LMStudio., Give it a topic and it will generate a web search query, gather web search results, summarize the results of web search, reflect on the summary to examine knowledge gaps, generate a new search query to address the gaps, and repeat for a user-defined number of cycles., It will provide the user a final markdown summary with all sources used to generate the summary., WARNING (8/6/25): The gpt-oss models do not support JSON mode in Ollama. Select use_tool_calling in the configuration to use tool calling instead of JSON mode., Local Deep Researcher is inspired by IterDRAG.
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 8: How can I properly integrate open-deep-research package to my existing backend? - Deployment - LangChain Forum ---
URL: https://forum.langchain.com/t/how-can-i-properly-integrate-open-deep-research-package-to-my-existing-backend/1325

SUMMARY:
<summary>
A backend developer is seeking help integrating the open-deep-research package (a LangGraph-based deep research agent from langchain-ai) into their existing backend system. They previously used the OpenAI SDK via LangChain AI and are migrating to Deep Research Agent due to complex workflows requiring LangGraph. They have read documentation and run the local version but are struggling with integration, noting that the package differs from typical LangChain guides which provide clear APIs like `.invoke()`. The post is from the LangChain community forum and includes related topics about running open-deep-research locally (authorization errors), deploying deep agents in the cloud, deploying createDeepAgent on LangGraph Cloud, comparing source code vs. LangGraph, and deep agent filesystem vs. store backend.
</summary>

<key_excerpts>
"I am trying to migrate a project initially using OpenAI SDK (from langchain ai), for generation to Deep Research Agent due to our now involved process requiring complex the need of LangGraph", "I wanted to be able to integrate this package in my backend. Reading through the source code, I can't seem to wrap my head on how to integrate this, it differs from langchain guides and resources, which provide certain APIs i can call such as the .invoke() and many more."
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 9: Langchain Open Deep Research Internals: A Step-by-Step Architecture Guide ---
URL: https://www.bolshchikov.com/p/open-deep-research-internals-a-step

SUMMARY:
<summary>
# Langchain Open Deep Research Internals: A Step-by-Step Architecture Guide

**Author:** Sergey Bolshchikov  
**Published:** November 2, 2025

This article provides a detailed technical deep-dive into the internal architecture of LangChain's Open Deep Research agent, explaining how state evolves, agents coordinate, and design patterns combine at each execution step. It fills gaps left by official LangChain resources (GitHub, blog, LangSmith, LangGraph Studio) by capturing state at each step and dynamic graph invocation.

## High-Level Architecture

The agent consists of three main parts:
1. **Scoping** — User clarification loop (LLM determines if clarification is needed) and brief generation
2. **Research** — Heavy work with supervisor and research sub-agents
3. **Final Report** — Reporter generates the final result

## Key Design Patterns

### 1. Reflection Pattern
Agents evaluate their own output and use feedback to refine responses iteratively. The LLM generates a response, acts as its own critic, and produces improved versions until quality standards are met.

### 2. Manual Tool Use Pattern (vs. Standard ReACT)
Instead of automatic tool execution, Open Deep Research uses **manual tool orchestration**:
- **Why needed:** Complex operations (spawning subgraphs), memory management (large research reports bloat context), custom routing logic, parallel execution
- **How it works:** Tool schemas are defined without implementations, bound to the LLM, and tool calls are handled manually — spawning entire sub-agents as "tools"
- **Key benefits:** Subgraph invocation, context efficiency (returns compact "Research completed" instead of 10,000-token reports), flexible routing, parallel coordination

## Step-by-Step Execution Flow (13 Steps)

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
</summary>

<key_excerpts>
The reflection pattern enables agents to evaluate their own output and use that feedback to refine their responses iteratively., Instead of adding a 10,000-token research report to the message history, you return a simple 'Research completed' message, The research sub-agent is a subgraph that is invoked dynamically based on the LLM response from the conduct_research tool; therefore, it's not visible in LangGraph Studio., The supervisor, given the brief and using reflection, spawns multiple research sub-agents on demand, each with a dedicated sub-task., A solid grasp of reflection agents, tool-use design patterns, and basic recursion is required to fully understand the process.
</key_excerpts>



--------------------------------------------------------------------------------

Excellent! I now have comprehensive results. Let me do one more search to check the very latest status on the project.
Search results: 



--- SOURCE 1: Introducing deep research - OpenAI ---
URL: https://openai.com/index/introducing-deep-research

SUMMARY:
February 10, 2026 update: You can now connect deep research to any MCP or app and restrict web searches to trusted sites, so you can focus



--------------------------------------------------------------------------------


--- SOURCE 2: GitHub - Ayanami0730/deep_research_bench: DeepResearch Bench: A Comprehensive Benchmark for Deep Research Agents · GitHub ---
URL: https://github.com/Ayanami0730/deep_research_bench

SUMMARY:
<summary>
# DeepResearch Bench: A Comprehensive Benchmark for Deep Research Agents

DeepResearch Bench is a GitHub repository hosted under user Ayanami0730 that provides a benchmark for evaluating Deep Research Agents (DRAs). It consists of **100 PhD-level research tasks** (50 Chinese, 50 English) crafted by domain experts across **22 distinct fields**, with topics derived from analyzing 96,147 anonymized user queries from web search-enabled LLM interactions.

## Key Features

- **Two complementary evaluation frameworks**: RACE (Reference-based Adaptive Criteria-driven Evaluation) for report generation quality, and FACT (Framework for Factual Abundance and Citation Trustworthiness) for information retrieval and grounding.
- **Latest evaluator (as of May 11, 2026)**: GPT-5.5 adopted as the RACE evaluator (scoring 71.82% overall alignment with human judgments, exceeding the 68.78% human baseline), with GPT-5.4-mini for the FACT pipeline.
- **Leaderboard**: Available on Hugging Face for comparing DRA performance; submissions require a temporary GPT-5.5 key and raw generated articles.

## Recent Developments
- **[11 May 2026]**: Official evaluator switched to GPT-5.5 (after Google's Gemini-2.5-Pro deprecation announcement). GPT-5.5 scored highest on Overall (71.82), PAR (73.00), and FAS (59.23) compared to Gemini-3.1-Pro and Claude-Opus-4-7.
- **[6 Feb 2026]**: DeepResearch Bench II released as a follow-up; DRB continues to be maintained.
- **[18 July 2025]**: Partnership established with AGI-Eval platform.
- **[15 July 2025]**: Major update adding Kimi-Researcher, Doubao-DeepResearch, and Claude-Researcher evaluations.

## Usage
The project provides a quick start flow: use the 100 benchmark queries from `data/prompt_data/query.jsonl`, run DRAs to produce outputs in `data/test_data/raw_data/<model_name>.jsonl`, configure `run_benchmark.sh`, and execute evaluation. Results save to `results/race/<model_name>/race_result.txt` and `results/fact/<model_name>/fact_result.txt`.

## Contact for Leaderboard Submission
dumingxuan@mail.ustc.edu.cn and imlrz@mail.ustc.edu.cn
</summary>

<key_excerpts>
DeepResearch Bench addresses the absence of a comprehensive benchmark for systematically evaluating Deep Research Agents (DRAs). Our benchmark consists of 100 PhD-level research tasks, each meticulously crafted by domain experts across 22 distinct fields, "GPT-5.5 wins on Overall, PAR, and FAS. We are adopting it as the new RACE evaluator (with GPT-5.4-mini for the FACT pipeline).", "If you like our project, please give us a star ⭐ on GitHub for the latest update.", "A temporary key with access to GPT-5.5, The raw generated articles, Reproducibility link, Model metadata", "Our benchmark consists of 100 PhD-level research tasks, each meticulously crafted by domain experts across 22 distinct fields"
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 3: Open-Source AI June 2026: New Models, Agents & Papers | devFlokers ---
URL: https://www.devflokers.com/blog/open-source-ai-roundup-june-2026

SUMMARY:
<summary>
# Open-Source AI June 2026 Roundup

The June 2026 open-source AI landscape is characterized by architectural diversification, localized execution, and a shift away from API dependencies toward open-weight configurations with complete deployment control.

## New Model Releases

**MiniMax M3** is the first open-weight model combining frontier software engineering with a 1-million-token context window and native multi-modal computer use. Built on MiniMax Sparse Attention (MSA) architecture, it scored 59.0% on SWE-Bench Pro (exceeding GPT-5.5 and Gemini 3.1 Pro), 66.0% on Terminal-Bench 2.1, 74.2% on MCP Atlas, and 70.06% on OSWorld-Verified.

**NVIDIA Cosmos 3** uses a mixture-of-transformers (MoT) architecture pairing a reasoning transformer with a generation transformer for physical AI. It ranks #1 among open-weight models on Physics-IQ, PAI-Bench, RoboLab, and RoboArena.

**DeepSeek V4-Pro** (1.6T MoE, 49B active, MIT License) scored 93.5 on LiveCodeBench with a 1M-token context window. **DeepSeek V4-Flash** (284B MoE, 13B active) achieved 79% SWE-Bench Verified. Other notable releases include Kimi K2.6, GLM-5.1, Qwen3-Coder-Next, Qwen3.6-27B, and Zyphra's ZAYA1-8B (trained from scratch on AMD Instinct hardware).

Proprietary labs responded: OpenAI launched GPT-5.5 Instant with 52.5% hallucination reduction, and Google presented Gemini 3.5 Flash at I/O.

## Key GitHub Projects

- **OpenClaw** (377,000+ stars): Open-source local AI assistant gateway connecting LLMs to messaging apps (Signal, Telegram, WhatsApp, Discord, iMessage) with Docker sandboxing.
- **Hermes Agent** (Nous Research): Self-improving skill compilation with persistent memory.
- **smolagents** (Hugging Face): Code-first ReAct loops via ~1,000 lines of Python.
- **OpenHands** (70,000+ stars): Full-scale autonomous coding workspace.
- **SWE-agent** (Princeton): Minimalist Agent-Computer Interface for repo-level debugging.

## Research Papers

- **SkillOpt** (Microsoft Research): Text-space optimizer updating agent skills as external state with zero inference overhead.
- **ARIS** (Shanghai Jiao Tong University): Multi-agent adversarial collaboration for autonomous research.
- **VLM3** (Meta): Native 3D learning for VLMs via text training.
- **Crashing Waves vs. Rising Tides** (MIT FutureTech): Analysis of 17,000+ worker evaluations showing AI automation as a continuous "rising tide" rather than sudden job replacement.

## Framework Updates

LangChain released v1.2.16 and LangGraph v1.1.10, with LangSmith rebranded to LangSmith Fleet. AutoGen's v0.4 breaking changes prompted a community fork (AG2). Anthropic released the Claude Agent SDK with native MCP support.

## Developer Tools

- **NVIDIA RTX Spark Superchip**: 1 petaflop AI compute, 128 GB unified memory, runs local models up to 120B parameters.
- **Microsoft Coreutils for Windows**: Rust-based reimplementation of GNU Coreutils.
- **Aion 1.0 Plan**: 14B parameter local reasoning model built into Windows.
- **Work IQ APIs & Web IQ**: Contextual organizational access and MCP-native web search.
- **ASSERT**: Open-source safety evaluation framework for agent trajectories.

## Three Key Trends

1. **Non-Transformer Architecture Proliferation**: Subquadratic attention models like SubQ 1M-Preview aim to bypass O(N²) complexity.
2. **Standardization of MCP**: Model Context Protocol becoming a foundational layer across major frameworks.
3. **Local-First Physical Simulators**: Models like Cosmos 3 enabling physically accurate world simulation for robotics and autonomous vehicles.
</summary>

<key_excerpts>
MiniMax M3 registers a 59.0% score on SWE-Bench Pro, exceeding the performance of several closed-source APIs including GPT-5.5 and Gemini 3.1 Pro., ZAYA1-8B was trained from scratch on AMD Instinct hardware, demonstrating that developers are no longer restricted to traditional Nvidia-dependent pipelines for high-efficiency model training., OpenClaw has surpassed 377,000 GitHub stars, functioning as a local, always-on control plane that connects large language models directly to messaging applications., arXiv enacted a temporary ban on all computer science review papers and instituted a one-year penalty for authors submitting papers containing hallucinated citations or clearly unverified AI-generated content., AI automation does not behave as a series of sudden, isolated 'crashing waves' that immediately replace human workers... instead operates as a continuous 'rising tide' gradually elevating capabilities across a wide array of interrelated tasks.
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 4: Open Deep Research ---
URL: https://www.langchain.com/blog/open-deep-research

SUMMARY:
<summary>
This webpage from LangChain's blog introduces their open source "Open Deep Research" system — a configurable, multi-agent deep research tool that allows users to bring their own models, search tools, and MCP servers. It addresses the challenge that research is an open-ended task requiring different strategies depending on the request type (comparisons, listings/rankings, or validation questions).

The system follows a three-phase architecture:

1. **Scope Phase**: Gathers user context via clarification questions and generates a focused research brief that serves as the "north star."
2. **Research Phase**: Uses a supervisor agent that delegates research tasks to sub-agents with isolated context windows. Sub-agents conduct tool-calling loops, then clean their findings via an additional LLM call before returning results. The supervisor iterates — if findings are insufficient, it spawns more sub-agents.
3. **Report Writing Phase**: When the supervisor deems research sufficient, a single LLM call produces the final report in one-shot using the brief and all research findings.

**Key lessons learned:**
- Multi-agent should only be used for easily parallelized tasks (e.g., research, not report section writing). Parallel section writing led to disjointed reports.
- Multi-agent with isolated context windows avoids "context clash" and token bloat when handling multiple sub-topics (e.g., comparing OpenAI vs Anthropic vs Google DeepMind). Single agents juggle unrelated context wastefully.
- A multi-agent supervisor can flexibly tune research depth — spawning sub-agents for complex queries or keeping it simple for straightforward ones.
- Context engineering (compressing chat into briefs, pruning sub-agent findings) is critical to avoid token bloat, context window limits, and model rate limits.

The project is hosted on GitHub and can be run locally via LangSmith Studio. LangChain Academy offers a course on building custom deep research agents.
</summary>

<key_excerpts>
"Research is an open‑ended task; the best strategy to answer a user request can't be easily known in advance.", "We translate the researcher-user chat interaction into a focused brief for the research supervisor to measure against.", "Multi-agents are hard to coordinate, and can perform poorly if writing sections of the report in parallel. We restrict multi-agent to research, and write the report in one-shot.", "Context isolation of sub-topics during research can avoid various long context failure modes.", "Context engineering has many practical benefits. It saves tokens, helps avoid context window limits, and helps stay under model rate limits."
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 5: Building Frontier Deep Research Systems in 2026 | Tomoro.ai ---
URL: https://tomoro.ai/insights/building-frontier-deep-research-systems-in-2026

SUMMARY:
<summary>
This article by Tomoro (dated June 26, 2026) discusses the evolution and implementation of enterprise-grade "deep research" AI systems, building on the paradigm popularized by OpenAI. It argues that while deep research has been useful individually, enterprise adoption has lagged due to concerns about reliability, disparate data sources, and model context limitations.

**Key Inflection Points in Model Capability:**
- Early 2025: Models like o1, GPT-4o, Claude-3.5-Sonnet struggled with low hundreds of sources.
- Mid-2025 (o3): Used for a pharmaceutical drug target discovery system; 3-4% of responses contained hallucinated sources (mitigated via post-hoc citation checks).
- August 2025 (GPT-5): Source hallucination rate dropped to 0%, enabling 10x more sources (3,000-5,000) per run. The limiting factor shifted to long-context performance.
- December 2025 (GPT-5.2): Further improved effective long-context performance.

**Three Pillars for Building Enterprise Deep Research Systems:**

1. **Getting Your Data Right:** Don't aim for full data unification upfront, which is slow and political. Instead, "make your data reachable, before you make it beautiful" — use sparse connections with high-signal "anchor" data points (specifications, policies, SKUs). Frontier models can soft-join heterogeneous data sources at inference time without formal mappings.

2. **Helping LLMs Navigate Your Data:** Use a lightweight ontology/semantic layer/graph to help models orient themselves across enterprise data, analogous to giving a new employee a map of who to talk to. These can be auto-generated by LLMs during ingestion or pass-throughs to existing systems (CRM, wikis, HR systems).

3. **Evals, Evals, Evals:** Three-tier evaluation framework:
   - *Mechanical (Guardrails):* Automated checks (citation validation, response length constraints, source diversity) run on every query.
   - *Analytic (How):* Q-A pairs scored by LLM-as-judge to assess tool usage, research direction, and stopping behavior. Second-order benefit: can surface new high-quality data connections to formalize.
   - *User (So What?):* Measures actual usefulness via user surveys, task completion tracking, and "would you hire this analyst?" assessments.

**Converting to Business Value:**
- **Wedge Selection:** Target large, expensive problems where improvement is demonstrable (drug discovery, competitive intelligence, regulatory compliance, contract analysis, supply chain risk) rather than low-stakes summarization.
- **UX Shift:** Move from "chatting" (short Q&A) to "delegating" (setting scope/template/goals and letting the system run independently). Key shifts: template-driven outputs, asynchronous (email/slack results rather than real-time chat), and user curation/feedback loops.
</summary>

<key_excerpts>
"the ability to synthesise knowledge is a prerequisite for creating new knowledge", "make your data reachable, before you make it beautiful", "Upon swapping from o3 to gpt-5 our evaluations showed that source hallucination rate dropped immediately to 0%", "you're no longer evaluating a model, you're evaluating a system", "MIT's claim that 95% of enterprise AI projects fail to achieve ROI"
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 6: langchain-ai/open_deep_research - GitHub ---
URL: https://github.com/langchain-ai/open_deep_research

SUMMARY:
<summary>
# 🔬 Open Deep Research

This is the GitHub repository for **Open Deep Research**, an open-source deep research agent developed by LangChain. It is a simple, configurable agent that works across many model providers, search tools, and MCP servers, with performance on par with popular deep research agents.

**Key Details:**
- **Repository**: langchain-ai/open_deep_research (Public)
- **Stars**: 11.8k | **Forks**: 1.7k | **Contributors**: 26
- **Language**: Python (69.6%), Jupyter Notebook (30.4%)
- **License**: MIT

**Recent Updates:**
- **Aug 14, 2025**: Free course released on building open deep research
- **Aug 7, 2025**: Added GPT-5, updated Deep Research Bench evaluation with GPT-5 results
- **Aug 2, 2025**: Achieved #6 ranking on Deep Research Bench Leaderboard with score 0.4344
- **Jul 30, 2025**: Blog post on evolution from original implementations
- **Jul 16, 2025**: Blog post and video overview released

**Architecture & Configuration:**
- Uses multiple LLMs for different tasks: Summarization (default: gpt-4.1-mini), Research (default: gpt-4.1), Compression (default: gpt-4.1), Final Report (default: gpt-4.1)
- Supports wide range of search tools (default: Tavily) with full MCP compatibility
- Configurable via LangGraph Studio UI

**Evaluation Results (Deep Research Bench):**
- **GPT-5**: RACE Score 0.4943 (204.6M total tokens)
- **Claude Sonnet 4**: RACE Score 0.4401 ($187.09 cost, 138.9M tokens)
- **Defaults (gpt-4.1)**: RACE Score 0.4309 ($45.98 cost, 58M tokens)
- **Bench Submission**: RACE Score 0.4344 ($87.83 cost, 207M tokens)

**Legacy Implementations**: Includes two older approaches - a Workflow Implementation (plan-and-execute with human-in-the-loop) and a Multi-Agent Implementation (supervisor-researcher architecture with parallel processing).

**Deployment**: Can be run locally via LangGraph server, deployed to LangGraph Platform, or used via Open Agent Platform (OAP) at oap.langchain.com.
</summary>

<key_excerpts>
Deep research has broken out as one of the most popular agent applications. This is a simple, configurable, fully open source deep research agent that works across many model providers, search tools, and MCP servers., Achieved #6 ranking on the Deep Research Bench Leaderboard with an overall score of 0.4344., Open Agent Platform (OAP) is a UI from which non-technical users can build and configure their own agents.
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 7: Issues · langchain-ai/open_deep_research · GitHub ---
URL: https://github.com/langchain-ai/open_deep_research/issues

SUMMARY:
<summary>
This appears to be the GitHub Issues page for the `langchain-ai/open_deep_research` repository. The page lists several open bug reports and feature requests related to the open_deep_research project. Key issues include bugs in `legacy/multi_agent.py` treating partial section completion as full research completion (Issue #284), `supervisor_tools` treating child `ConductResearch` exceptions as successful research completion (Issue #283), a missing max_revisions limit in the feedback-to-report-plan revision loop (Issue #269), broken links in README.md (Issue #268), configuration errors (Issue #267), and a bug where `compress_research` removes recent messages instead of older ones on token limit (Issue #252). Other issues cover unclear search provider customization (Issue #250), evaluation tool questions (Issue #234), customizable report templates (Issue #233), citation inconsistency in `compress_research_system_prompt` (Issue #232), and code update questions (Issue #231).
</summary>

<key_excerpts>
[[BUG] `legacy/multi_agent.py` can treat partial section completion as full research completion, [[BUG] `supervisor_tools` treats any child `ConductResearch` exception as successful research completion, [Bug: compress_research removes recent messages instead of older ones on token limit]
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 8: How can I properly integrate open-deep-research package to my ... ---
URL: https://forum.langchain.com/t/how-can-i-properly-integrate-open-deep-research-package-to-my-existing-backend/1325

SUMMARY:
<summary>
This is a forum post from the LangChain community where a backend developer is seeking help integrating the open-deep-research package (a LangGraph-based project from GitHub) into their existing backend. The developer was previously using OpenAI SDK from LangChain AI with `.invoke()` APIs but is struggling to adapt to the open-deep-research package, as its source code structure differs from standard LangChain guides and doesn't offer familiar API methods. They have successfully run the local version per documentation but cannot figure out how to programmatically integrate it into their backend. The post includes links to related discussion topics about running open-deep-research locally, deploying deep agents on LangGraph Cloud, and other LangGraph-related questions. No solution or answer is provided in the post itself.
</summary>

<key_excerpts>
I am trying to migrate a project initially using OpenAI SDK (from langchain ai), for generation to Deep Research Agent due to our now involved process requiring complex the need of LangGraph, Reading through the source code, I can't seem to wrap my head on how to integrate this, it differs from langchain guides and resources, which provide certain APIs i can call such as the .invoke()
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 9: langchain-ai/deep_research_from_scratch - GitHub ---
URL: https://github.com/langchain-ai/deep_research_from_scratch

SUMMARY:
<summary>
This GitHub repository (`langchain-ai/deep_research_from_scratch`) is a tutorial series by LangChain that builds a deep research agent system from scratch. Deep research (producing comprehensive reports from various sources) is a popular agent application, with competing products from OpenAI, Anthropic, Perplexity, and Google. The repo builds on LangChain's earlier "open deep researcher" project, offering a simple and configurable implementation allowing users to bring their own models, search tools, and MCP servers.

The system uses an agent-based approach to conduct research as part of a three-step process, since research is an open-ended task requiring flexible strategies. The repo contains 5 tutorial notebooks:

1. **User Clarification and Brief Generation** (`1_scoping.ipynb`) - Clarifies research scope and transforms user input into structured research briefs. Covers state management, structured output patterns, and conditional routing.
2. **Research Agent with Custom Tools** (`2_research_agent.ipynb`) - Builds an iterative research agent using external search tools. Covers agent patterns, tool integration, search optimization, and research workflow design.
3. **Research Agent with MCP** (`3_research_agent_mcp.ipynb`) - Integrates Model Context Protocol (MCP) servers as research tools. Covers MCP integration and client-server architecture.
4. **Research Supervisor** (`4_research_supervisor.ipynb`) - Multi-agent coordination for complex research tasks using parallel processing and async orchestration.
5. **Full Multi-Agent Research System** (`5_full_agent.ipynb`) - Complete end-to-end research system integrating all components. Covers system architecture, subgraph composition, and end-to-end workflows.

The repo includes a `.env` file for API keys, a `CLAUDE.md` file, and uses `pyproject.toml` and `uv.lock` for dependencies. It is licensed under standard terms and has 50 commits on the main branch.
</summary>

<key_excerpts>
Deep research has broken out as one of the most popular agent applications., We built an open deep researcher that is simple and configurable, allowing users to bring their own models, search tools, and MCP servers., Agents are well suited to research because they can flexibly apply different strategies, using intermediate results to guide their exploration., Each notebook builds on the previous concepts, culminating in a production-ready deep research system that can handle complex, multi-faceted research queries with intelligent scoping and coordinated execution.
</key_excerpts>



--------------------------------------------------------------------------------


--- SOURCE 10: Open Deep Research - YouTube ---
URL: https://www.youtube.com/watch?v=2mSNIX-l_Zc

SUMMARY:
<summary>
# Open Deep Research - LangChain Video Summary

## Overview
This video (posted February 20, 2025) by Lance from LangChain presents **Open Deep Research**, an open-source AI assistant capable of autonomous deep research on user-supplied topics. The video demonstrates the tool in LangGraph Studio, discusses common architectures across closed/open deep research tools, and compares implementations from OpenAI, Gemini, and various open-source projects.

## Key Architecture Components

1. **Report Planning Phase**: The system generates a report plan using search queries to seed generation, presents sections to the user for feedback (human-in-the-loop), and allows iterative refinement before proceeding.

2. **Deep Research Phase**: For each section, the system generates search queries, runs web searches, writes the section, reflects on content quality, and iterates searches to fill gaps. This runs in parallel across all sections.

## Architectural Comparisons

- **Planning with Human-in-Loop**: Gemini produces a reviewable/editable plan; OpenAI Deep Research asks clarifying questions; LangChain's approach follows Gemini's pattern with explicit section plans.
- **Architecture Types**: 
  - **Tool-Calling Agents** (flexible, LLM with bound tools called in any order) - used by Hugging Face's open deep researcher
  - **Workflows** (constrained control flow specified by user, more reliable, lower token usage) - used by LangChain's implementation

## Evaluation Results
- GAIA benchmark: OpenAI Deep Research scores well; Hugging Face approach at 55%
- Humanities Last Exam (3,000 questions across STEM/Humanities): OpenAI Deep Research significantly outperforms O3 alone

## Configuration Options
Users can customize: report structure (outline), planner model (e.g., DeepSeek, O3-mini), human-in-loop settings, search depth, number of iterations, search API (Tavily by default, also supports Perplexity, SerpAPI, Firecrawl), and writer model.

## Cost Comparison
- OpenAI/Gemini Pro: ~$200/month subscriptions
- Open Deep Research: Most reports cost less than $0.50 to generate, with options to reduce cost further using different models

## Key Tradeoffs
- **Proprietary services** (Gemini/OpenAI): Strong default web crawling, excellent inline citations, less configurable
- **Open-source**: High configurability, ability to integrate new models and search services quickly, significantly lower cost, full trace visibility (via LangSmith)
</summary>

<key_excerpts>
"The argument I would make is it's about configurability and the nice thing about open source research assistants is that they are very very configurable", "There is always a trade-off between using an open-ended tool calling agent versus what I consider workflow... the benefit of workflow is that you provide more scaffolding for reliability and often lower token usage but it can lack some flexibility", "Most of the reports I've generated are less than 50 cents and you can easily configure that make it cheaper if you'd like using different models", "The ability to just pull in new new tools is a really fun part of the open source deep researchers", "I'll mention briefly that some of these deep research approaches have been evaluated so Gaia is one particular evaluation from meta and hugging phase and you can see that open ey deep research scores quite well and Huggy B's approach is 55"
</key_excerpts>



--------------------------------------------------------------------------------


Reflection recorded: I now have comprehensive information about LangChain Open Deep Research. Let me organize the findings into a clear synthesis covering:
1. Purpose
2. Architecture (three phases + design patterns)
3. Supported model/search configuration
4. Recent project status
5. Limitations of the evidence
6. Source URLs

Let me compile this now.