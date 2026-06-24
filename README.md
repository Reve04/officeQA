# Treasury Bulletin QA Agent

An autonomous financial analyst agent system designed for the Sentient **Office-QA Arena**. The system is built to perform grounded, multi-step reasoning and precise calculations over the historical U.S. Treasury Bulletin corpus (1939–2025).

## 🚀 Key Features

* **Custom FastMCP Retrieval Server (`bm25-search`):**
  * **BM25 Search:** Custom search engine optimized with temporal heuristics and metadata-based scaling for historical data.
  * **Document Parsing:** Table extraction and raw text extraction from historical JSON/TXT pages.
* **Grounded Reasoning Prompting System:**
  * Uses structured system prompts (`prompts/system.j2`) to guide the model through temporal alignment, historical fiscal year definition swaps (pre/post 1976), and cabine-level department data aggregation.
* **Advanced Math & Statistical Analysis Tools:**
  * Out-of-the-box MCP tools for evaluating safe mathematical expressions, Sample/Population Standard Deviation, Pearson Correlation, OLS Linear Regression, Geometric Mean, Gini Coefficient, Coefficient of Variation (CV), Box-Cox transformations, and Hodrick-Prescott (HP) filtering.
* **Numerically Stable Fallbacks:**
  * Statistical tools include optimized Numpy implementations with pure Python fallbacks (e.g., Gaussian elimination with partial pivoting) to operate in strict, sandboxed offline environments.

## 🛠️ Tech Stack

* **Agent Harness:** Goose
* **Model Configuration:** `openrouter/minimax/minimax-2.7` (with high reasoning effort)
* **MCP Framework:** FastMCP (Python)
* **Environment:** Sandboxed CLI runner via `arena-cli`
