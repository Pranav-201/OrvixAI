<p align="center"> <img src="https://img.shields.io/badge/AI-Multi--Agent-blue?style=for-the-badge" /> <img src="https://img.shields.io/badge/LangChain-Powered-green?style=for-the-badge" /> <img src="https://img.shields.io/badge/Streamlit-UI-red?style=for-the-badge" /> </p>

Self-healing multi-agent research system that searches, reads, writes, critiques, and fact-checks reports automatically.

⚡ What it does
🌐 Web search via AI agents (Tavily)
📄 Extracts clean content from pages
✍️ Generates structured research reports
🧠 Self-critiques and improves output
🔁 Auto-retries until quality threshold
🔍 Verifies key factual claims
🏗️ Architecture
⚙️ Tech Stack
LangChain + LangGraph
Mistral LLM
Tavily Search API
Streamlit UI
Python
🚀 Run Locally
git clone https://github.com/your-username/researchmind.git
cd researchmind
pip install -r requirements.txt
streamlit run app.py
🔐 Setup
MISTRAL_API_KEY=your_key
TAVILY_API_KEY=your_key
🧠 Key Idea

Instead of one-shot answers, the system iteratively improves itself until it becomes reliable and fact-checked.

📜 License

MIT © 2026
