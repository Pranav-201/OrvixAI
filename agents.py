from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.prebuilt import create_react_agent
from tools import web_search, scrape_url, verify_claim
from dotenv import load_dotenv

try:
    load_dotenv()
except Exception:
    pass

# Model setup
llm = ChatMistralAI(
    model="mistral-small-2506",
    temperature=0
)


# ── Agents ────────────────────────────────────────────────────────────────────

def build_search_agent():
    """Agent 1 — searches the web for information on a topic."""
    return create_react_agent(
        model=llm,
        tools=[web_search]
    )


def build_reader_agent():
    """Agent 2 — scrapes the most relevant URL for deeper content."""
    return create_react_agent(
        model=llm,
        tools=[scrape_url]
    )


def build_refine_agent():
    """
    Agent 3 (NEW) — Self-Healing Loop.
    Given critic feedback and the original topic, it generates a better,
    more targeted search query to improve the next research iteration.
    """
    return create_react_agent(
        model=llm,
        tools=[web_search]
    )


def build_verifier_agent():
    """
    Agent 4 (NEW) — Claim Verification.
    Takes individual factual claims from the report and verifies each one
    against a second independent web search. Labels each: VERIFIED /
    UNVERIFIED / CONTRADICTED.
    """
    return create_react_agent(
        model=llm,
        tools=[verify_claim]
    )


# ── Chains ────────────────────────────────────────────────────────────────────

# Writer chain
writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert research writer. Write clear, structured and insightful reports."
    ),
    (
        "human",
        """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual and professional."""
    ),
])

writer_chain = writer_prompt | llm | StrOutputParser()


# Critic chain
critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a sharp and constructive research critic. Be honest and specific."
    ),
    (
        "human",
        """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""
    ),
])

critic_chain = critic_prompt | llm | StrOutputParser()


# Claim extractor chain (NEW)
# Pulls out individual verifiable factual claims from the report as a
# numbered list so the verifier agent can check them one by one.
claim_extractor_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are a fact-checking assistant. Extract only concrete, verifiable "
            "factual claims from research reports. Ignore opinions, vague statements, "
            "and qualitative observations."
        )
    ),
    (
        "human",
        """Extract the 5 most important, specific, and verifiable factual claims from the report below.

Report:
{report}

Return ONLY a numbered list in this exact format (no extra text, no preamble):
1. <claim>
2. <claim>
3. <claim>
4. <claim>
5. <claim>"""
    ),
])

claim_extractor_chain = claim_extractor_prompt | llm | StrOutputParser()


# Query refiner chain (NEW)
# Used inside the self-healing loop: given feedback + original topic,
# it returns a sharper search query for the next iteration.
query_refiner_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are a research strategist. Given a topic and critic feedback on a "
            "previous report, generate a better, more specific search query that "
            "addresses the gaps identified. Return ONLY the query string, nothing else."
        )
    ),
    (
        "human",
        """Original topic: {topic}

Critic feedback:
{feedback}

Generate a single improved search query that targets the weaknesses above:"""
    ),
])

query_refiner_chain = query_refiner_prompt | llm | StrOutputParser()