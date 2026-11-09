# 🕵️ AgentProbe

AgentProbe is an open-source, lightweight red-teaming framework designed to evaluate the security, safety, and robustness of Tool-Calling AI Agents. It automates prompt injection attacks, evaluates defense mechanisms, and generates reproducible regression tests.

## 🚀 Key Features

* **Provider-Agnostic LLM Interface:** Works with OpenAI, Anthropic, Ollama, or custom mock models for cost-free testing.
* **Sandboxed Target Agents:** Includes mock environments for Email, Web Research, and Banking to safely simulate severe attacks (e.g., data exfiltration, unauthorized transfers).
* **Attack Engine:** Loads YAML-based attack seeds and uses an LLM-driven mutator to generate variants for fuzzy testing.
* **Pluggable Defenses:** Implements a Wrapper pattern allowing you to easily stack defenses (Sanitization, Guard Models, Permission Gates) without rewriting agent code.
* **SQLite Tracing & Resumability:** Every step, tool call, and token cost is logged. If a massive campaign crashes due to API limits, AgentProbe resumes exactly where it left off.
* **Automated Regression Generation:** Converts successful LLM traces into pure Python `pytest` files for CI/CD integration.

## 🛠️ Quick Start

**1. Install Dependencies**
```bash
pip install -e .