from agents import (
    build_search_agent,
    build_reader_agent,
    build_refine_agent,
    build_verifier_agent,
    writer_chain,
    critic_chain,
    claim_extractor_chain,
    query_refiner_chain,
)
from tools import parse_critic_score
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import re

console = Console()

# ── Config ────────────────────────────────────────────────────────────────────

MIN_SCORE       = 7.0   # Critic score threshold to exit the self-healing loop
MAX_ITERATIONS  = 3     # Hard cap — prevents infinite loops
MAX_CLAIMS      = 5     # How many claims the verifier checks per report


# ── Helpers ───────────────────────────────────────────────────────────────────

def _header(step: int, title: str):
    console.print(Panel(f"[bold cyan]Step {step}[/bold cyan] — {title}", expand=False))


def _run_search_and_scrape(topic: str, query: str) -> dict:
    """
    Shared helper used both in the initial run and in the self-healing loop.
    Returns a dict with keys: search_results, scraped_content.
    """
    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages": [("user", f"Find recent, reliable and detailed information about: {query}")]
    })
    search_results = search_result["messages"][-1].content

    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages": [(
            "user",
            f"Based on the following search results about '{topic}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{search_results[:800]}"
        )]
    })
    scraped_content = reader_result["messages"][-1].content

    return {"search_results": search_results, "scraped_content": scraped_content}


def _write_and_critique(topic: str, search_results: str, scraped_content: str) -> dict:
    """
    Runs the writer → critic chain pair.
    Returns a dict with keys: report, feedback, score.
    """
    research_combined = (
        f"SEARCH RESULTS:\n{search_results}\n\n"
        f"DETAILED SCRAPED CONTENT:\n{scraped_content}"
    )
    report = writer_chain.invoke({"topic": topic, "research": research_combined})
    feedback = critic_chain.invoke({"report": report})
    score = parse_critic_score(feedback)
    return {"report": report, "feedback": feedback, "score": score}


def _parse_claims(raw: str) -> list[str]:
    """
    Parses the numbered-list output from the claim extractor chain.
    Returns a clean list of claim strings.
    """
    lines = raw.strip().splitlines()
    claims = []
    for line in lines:
        line = line.strip()
        # Match lines like "1. claim text"
        match = re.match(r"^\d+\.\s+(.+)$", line)
        if match:
            claims.append(match.group(1).strip())
    return claims[:MAX_CLAIMS]


def _verify_claims(report: str) -> list[dict]:
    """
    Feature #3 — Claim Verification.

    1. Uses the claim_extractor_chain to pull out MAX_CLAIMS factual claims.
    2. For each claim, calls the verifier agent which uses the verify_claim tool.
    3. Parses the verdict (VERIFIED / UNVERIFIED / CONTRADICTED) from the agent output.
    4. Returns a list of dicts: {claim, verdict, evidence_summary}.
    """
    _header(4, "Claim Extractor is identifying key factual claims ...")

    raw_claims = claim_extractor_chain.invoke({"report": report})
    claims = _parse_claims(raw_claims)

    console.print(f"\n[bold]Extracted {len(claims)} claims to verify:[/bold]")
    for i, c in enumerate(claims, 1):
        console.print(f"  [dim]{i}.[/dim] {c}")

    _header(5, "Verifier Agent is fact-checking each claim ...")

    verifier_agent = build_verifier_agent()
    verified_claims = []

    for i, claim in enumerate(claims, 1):
        console.print(f"\n[yellow]Verifying claim {i}/{len(claims)}:[/yellow] {claim}")

        result = verifier_agent.invoke({
            "messages": [(
                "user",
                f"Use the verify_claim tool to check this claim, then give a final verdict.\n\n"
                f"Claim: {claim}\n\n"
                f"After seeing the evidence, respond in this exact format:\n"
                f"VERDICT: <VERIFIED|UNVERIFIED|CONTRADICTED>\n"
                f"REASON: <one sentence explaining why>"
            )]
        })

        agent_output = result["messages"][-1].content

        # Parse verdict from agent response
        verdict_match = re.search(
            r"VERDICT:\s*(VERIFIED|UNVERIFIED|CONTRADICTED)", agent_output, re.IGNORECASE
        )
        reason_match = re.search(r"REASON:\s*(.+)", agent_output)

        verdict = verdict_match.group(1).upper() if verdict_match else "UNVERIFIED"
        reason  = reason_match.group(1).strip()  if reason_match  else "Could not determine reason."

        verified_claims.append({
            "claim":   claim,
            "verdict": verdict,
            "reason":  reason,
        })

        # Color-coded live feedback
        color = {"VERIFIED": "green", "UNVERIFIED": "yellow", "CONTRADICTED": "red"}.get(verdict, "white")
        console.print(f"  [{color}]{verdict}[/{color}] — {reason}")

    return verified_claims


def _print_verification_table(verified_claims: list[dict]):
    table = Table(title="Claim Verification Report", box=box.ROUNDED, show_lines=True)
    table.add_column("#",        style="dim",   width=3)
    table.add_column("Claim",    style="white", max_width=50)
    table.add_column("Verdict",  style="bold",  width=14)
    table.add_column("Reason",   style="dim",   max_width=40)

    color_map = {"VERIFIED": "green", "UNVERIFIED": "yellow", "CONTRADICTED": "red"}

    for i, item in enumerate(verified_claims, 1):
        color = color_map.get(item["verdict"], "white")
        table.add_row(
            str(i),
            item["claim"],
            f"[{color}]{item['verdict']}[/{color}]",
            item["reason"],
        )

    console.print("\n")
    console.print(table)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_research_pipeline(topic: str) -> dict:
    state = {}

    # ── Initial pass ──────────────────────────────────────────────────────────

    _header(1, "Search + Reader agents gathering initial research ...")
    data = _run_search_and_scrape(topic, topic)
    state.update(data)

    _header(2, "Writer drafting report | Critic evaluating ...")
    result = _write_and_critique(topic, state["search_results"], state["scraped_content"])
    state.update(result)

    console.print(f"\n[bold]Initial critic score:[/bold] {state['score']:.1f}/10")
    console.print(state["feedback"])

    # ── Self-Healing Loop (Feature #1) ────────────────────────────────────────
    # If the critic score is below the threshold, we refine the search query
    # based on the feedback and run the full pipeline again (up to MAX_ITERATIONS).

    iteration = 1
    while state["score"] < MIN_SCORE and iteration < MAX_ITERATIONS:
        iteration += 1
        console.print(Panel(
            f"[bold red]Score {state['score']:.1f}/10 < {MIN_SCORE} — "
            f"entering self-healing iteration {iteration}/{MAX_ITERATIONS}[/bold red]",
            expand=False
        ))

        _header(f"2.{iteration}a", "Refine Agent generating a better search query ...")
        refined_query = query_refiner_chain.invoke({
            "topic":    topic,
            "feedback": state["feedback"],
        }).strip()
        console.print(f"[bold]Refined query:[/bold] {refined_query}")

        _header(f"2.{iteration}b", "Re-running Search + Reader with refined query ...")
        new_data = _run_search_and_scrape(topic, refined_query)

        # Merge new research with existing — gives the writer more to work with
        state["search_results"]  += "\n\n--- REFINED SEARCH ---\n" + new_data["search_results"]
        state["scraped_content"] += "\n\n--- REFINED SCRAPE ---\n"  + new_data["scraped_content"]

        _header(f"2.{iteration}c", "Re-running Writer + Critic ...")
        result = _write_and_critique(topic, state["search_results"], state["scraped_content"])
        state.update(result)

        console.print(f"\n[bold]Iteration {iteration} critic score:[/bold] {state['score']:.1f}/10")
        console.print(state["feedback"])

    if state["score"] >= MIN_SCORE:
        console.print(f"\n[bold green]✓ Report passed quality threshold "
                      f"({state['score']:.1f}/10) after {iteration} iteration(s).[/bold green]")
    else:
        console.print(f"\n[bold yellow]⚠ Max iterations reached. Best score: "
                      f"{state['score']:.1f}/10.[/bold yellow]")

    # ── Claim Verification (Feature #3) ───────────────────────────────────────
    _header(3, "Starting Claim Verification stage ...")
    state["verified_claims"] = _verify_claims(state["report"])
    _print_verification_table(state["verified_claims"])

    # ── Final summary ─────────────────────────────────────────────────────────
    verified_count    = sum(1 for c in state["verified_claims"] if c["verdict"] == "VERIFIED")
    unverified_count  = sum(1 for c in state["verified_claims"] if c["verdict"] == "UNVERIFIED")
    contradicted_count = sum(1 for c in state["verified_claims"] if c["verdict"] == "CONTRADICTED")
    total = len(state["verified_claims"])

    console.print(Panel(
        f"[bold]Pipeline Complete[/bold]\n\n"
        f"Final Report Quality Score : [cyan]{state['score']:.1f}/10[/cyan]\n"
        f"Iterations taken           : [cyan]{iteration}[/cyan]\n"
        f"Claims verified            : [green]{verified_count}/{total}[/green]\n"
        f"Claims unverified          : [yellow]{unverified_count}/{total}[/yellow]\n"
        f"Claims contradicted        : [red]{contradicted_count}/{total}[/red]",
        title="Summary",
        expand=False
    ))

    console.print("\n[bold]── Final Report ──[/bold]\n")
    console.print(state["report"])

    return state


if __name__ == "__main__":
    topic = input("\nEnter a research topic: ")
    run_research_pipeline(topic)