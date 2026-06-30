<p align="center"> <img src="https://img.shields.io/badge/AI-Multi--Agent-blue?style=for-the-badge" /> <img src="https://img.shields.io/badge/LangChain-Powered-green?style=for-the-badge" /> <img src="https://img.shields.io/badge/LangGraph-Orchestration-purple?style=for-the-badge" /> <img src="https://img.shields.io/badge/Streamlit-UI-red?style=for-the-badge" /> </p> <p align="center"> <b>Self-Healing Multi-Agent Research Intelligence System</b><br> <i>Search → Read → Write → Critique → Self-Heal → Verify</i> </p>
⚡ Live System Flow
<p align="center">
</p>
🚀 What is ResearchMind?

ResearchMind is an autonomous AI research engine that:

🌐 Searches the web using AI agents
📄 Extracts and cleans real content
✍️ Generates structured research reports
🧠 Critiques its own output
🔁 Improves itself via self-healing loops
🔍 Fact-checks every major claim
🧠 Core Architecture
<p align="center">
Stage	Component	Role
🔎 1	Search Agent	Finds top web results
📄 2	Reader Agent	Scrapes clean content
✍️ 3	Writer Chain	Generates report
🎯 4	Critic Chain	Scores output
🔁 5	Self-Healing Loop	Improves query
🔬 6	Claim Verifier	Fact-checks claims
</p>
⚙️ Tech Stack
<p align="center">












</p>
🔁 Self-Healing Intelligence

The system doesn’t fail — it iterates until it improves.

If score < 7 → system refines query
Re-searches better sources
Merges new knowledge
Rewrites improved report
Repeats max 3 times
🔬 Claim Verification Engine

Each final report is validated:

✔ Extract top claims
✔ Run fresh web search
✔ Compare evidence
✔ Assign verdict:

Status	Meaning
✅ VERIFIED	Supported by evidence
⚠️ UNVERIFIED	Not enough proof
❌ CONTRADICTED	Conflicting sources
📁 Project Structure
ResearchMind/
│
├── app.py              # Streamlit UI
├── pipeline.py         # CLI runner
├── agents.py           # LLM agents
├── tools.py            # Search + scraping tools
├── requirements.txt
└── .env
⚡ Quick Start
git clone https://github.com/your-username/researchmind.git
cd researchmind
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
🔐 Environment Setup
MISTRAL_API_KEY=your_key
TAVILY_API_KEY=your_key
▶️ Run
🖥 Streamlit UI
streamlit run app.py
💻 CLI Mode
python pipeline.py
🧠 Why This Project is Powerful
Self-improving AI pipeline (rare in portfolios)
Real multi-agent orchestration (not single LLM calls)
Built-in reasoning + critique loop
Fact verification system
Production-level architecture thinking
🚀 Future Upgrades
🧠 Vector DB memory (RAG layer)
⚡ Parallel claim verification
📄 PDF export reports
🤖 Multi-model critic voting
📊 LangSmith observability
🧩 Caching layer for search results
📜 License
MIT License © 2026 ResearchMind
