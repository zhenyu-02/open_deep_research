**List of Queries and Tool Calls Made**

1. Accessed the public GitHub repository for `langchain-ai/open_deep_research` at https://github.com/langchain-ai/open_deep_research (seeded web search)

---

**Fully Comprehensive Findings**

### Purpose

LangChain Open Deep Research is described as "a simple, configurable, fully open source deep research agent that works across many model providers, search tools, and MCP servers." It was built because "deep research has broken out as one of the most popular agent applications." Its performance is "on par with many popular deep research agents" as evidenced by its ranking on the Deep Research Bench leaderboard. As of August 2, 2025, it achieved **#6 ranking** on the Deep Research Bench Leaderboard with an overall RACE score of **0.4344**. As of August 7, 2025, GPT-5 was added and the Deep Research Bench evaluation was updated with GPT-5 results, achieving a RACE score of **0.4943**.

### Architecture

Open Deep Research is an agent built on LangGraph. The project structure is:

- **Clone the repository**: `git clone https://github.com/langchain-ai/open_deep_research.git`
- **Install dependencies**: `uv sync` or `uv pip install -r pyproject.toml`
- **Configure environment**: Copy `.env.example` to `.env`
- **Launch agent with LangGraph server locally**: `uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking`

This opens the **LangGraph Studio UI** in the browser with the following endpoints:
- 🚀 API: `http://127.0.0.1:2024`
- 🎨 Studio UI: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`
- 📚 API Docs: `http://127.0.0.1:2024/docs`

Users ask a question in the `messages` input field and click Submit. Different configurations can be selected in the "Manage Assistants" tab.

### Model Configuration (LLM)

Open Deep Research supports a wide range of LLM providers via the `init_chat_model()` API. It uses LLMs for four different tasks, configurable via the `configuration.py` file. The following are the default model fields:

| Task | Default Model | Description |
|------|---------------|-------------|
| **Summarization** | `openai:gpt-4.1-mini` | Summarizes search API results |
| **Research** | `openai:gpt-4.1` | Powers the search agent |
| **Compression** | `openai:gpt-4.1` | Compresses research findings |
| **Final Report Model** | `openai:gpt-4.1` | Writes the final report |

> **Note**: The selected model will need to support **structured outputs** and **tool calling**.
> **Note for OpenRouter**: Follow [this guide](https://github.com/langchain-ai/open_deep_research/issues/75#issuecomment-2811472408).
> **Note for local models via Ollama**: See [setup instructions](https://github.com/langchain-ai/open_deep_research/issues/65#issuecomment-2743586318).

### Search Configuration

Open Deep Research supports a wide range of search tools. By default it uses the **Tavily** search API. It has **full MCP compatibility** and works with **native web search for Anthropic and OpenAI**. The `search_api` and `mcp_config` fields in `configuration.py` control these settings. This can be accessed via the LangGraph Studio UI.

### Evaluation

Open Deep Research is configured for evaluation with **Deep Research Bench**. This benchmark has **100 PhD-level research tasks** (50 English, 50 Chinese), crafted by domain experts across **22 fields** (e.g., Science & Tech, Business & Finance) to mirror real-world deep-research needs. It has 2 evaluation metrics, but the leaderboard is based on the **RACE score**. This uses LLM-as-a-judge (Gemini) to evaluate research reports against a golden set of reports compiled by experts across a set of metrics.

> **Warning**: Running across the 100 examples can cost ~$20-$100 depending on the model selection.

The dataset is available on **LangSmith** [via this link](https://smith.langchain.com/public/c5e7a6ad-fdba-478c-88e6-3a388459ce8b/d). To kick off evaluation, run:
```
python tests/run_evaluate.py
```
Then extract results to JSONL:
```
python tests/extract_langsmith_data.py --project-name "YOUR_EXPERIMENT_NAME" --model-name "you-model-name" --dataset-name "deep_research_bench"
```

Results table from the README:

| Name | Summarization | Research | Compression | Total Tokens | RACE Score |
|------|---------------|----------|-------------|--------------|------------|
| GPT-5 | `openai:gpt-4.1-mini` | `openai:gpt-5` | `openai:gpt-4.1` | 204,640,896 | **0.4943** |
| Defaults | `openai:gpt-4.1-mini` | `openai:gpt-4.1` | `openai:gpt-4.1` | 58,015,332 | **0.4309** |
| Claude Sonnet 4 | `openai:gpt-4.1-mini` | `anthropic:claude-sonnet-4-20250514` | `openai:gpt-4.1` | 138,917,050 | **0.4401** |
| Deep Research Bench Submission | `openai:gpt-4.1-nano` | `openai:gpt-4.1` | `openai:gpt-4.1` | 207,005,549 | **0.4344** |

Total Cost:
- Defaults: $45.98
- Claude Sonnet 4: $187.09
- Deep Research Bench Submission: $87.83

### Recent Updates (as of README publication date)

- **August 14, 2025**: Free course available [here](https://academy.langchain.com/courses/deep-research-with-langgraph) (course repo [here](https://github.com/langchain-ai/deep_research_from_scratch))
- **August 7, 2025**: Added GPT-5 and updated the Deep Research Bench evaluation w/ GPT-5 results
- **August 2, 2025**: Achieved #6 ranking on the Deep Research Bench Leaderboard with an overall score of 0.4344
- **July 30, 2025**: Blog post on evolution from original implementations to current version [here](https://rlancemartin.github.io/2025/07/30/bitter_lesson/)
- **July 16, 2025**: Blog post [here](https://blog.langchain.com/open-deep-research/) and video [here](https://www.youtube.com/watch?v=agGiWUpxkhg) for a quick overview

---

**List of All Relevant Sources (with citations in the report)**

[1] GitHub Repository - langchain-ai/open_deep_research: https://github.com/langchain-ai/open_deep_research