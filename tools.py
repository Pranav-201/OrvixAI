from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
import re
from dotenv import load_dotenv
from rich import print

try:
    load_dotenv()
except Exception:
    pass

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic. Returns Titles, URLs and snippets."""
    results = tavily.search(query=query, max_results=5)

    out = []
    for r in results["results"]:
        out.append(
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['content'][:300]}\n"
        )

    return "\n----\n".join(out)


@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper reading."""
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:3000]
    except Exception as e:
        return f"Could not scrape URL: {str(e)}"


@tool
def verify_claim(claim: str) -> str:
    """
    Verify a single factual claim by searching the web for corroborating or contradicting evidence.
    Returns a verdict: VERIFIED, UNVERIFIED, or CONTRADICTED with supporting evidence.
    """
    try:
        results = tavily.search(query=claim, max_results=3)

        evidence_snippets = []
        for r in results["results"]:
            evidence_snippets.append(
                f"Source: {r['url']}\nEvidence: {r['content'][:200]}"
            )

        evidence_text = "\n---\n".join(evidence_snippets) if evidence_snippets else "No evidence found."

        return f"""CLAIM: {claim}

EVIDENCE FOUND:
{evidence_text}

(Use this evidence to determine if the claim is VERIFIED, UNVERIFIED, or CONTRADICTED)"""

    except Exception as e:
        return f"Could not verify claim: {str(e)}"


def parse_critic_score(feedback: str) -> float:
    """
    Utility (not a tool) — parses the numeric score from the critic chain's output.
    Looks for patterns like 'Score: 7/10' or 'Score: 7.5/10'.
    Returns float score, defaults to 0.0 if not found.
    """
    match = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", feedback, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 0.0