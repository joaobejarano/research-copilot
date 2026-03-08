from mcp.server.fastmcp import FastMCP

mcp = FastMCP("research-tools")


@mcp.tool()
def normalize_ticker(ticker: str) -> str:
    """Normalize a market ticker string."""
    return ticker.strip().upper()


@mcp.tool()
def score_evidence_coverage(num_chunks: int, num_citations: int) -> str:
    """Return a coarse evidence coverage label."""
    if num_chunks <= 0 or num_citations <= 0:
        return "insufficient"
    if num_chunks < 3 or num_citations < 2:
        return "weak"
    return "good"


@mcp.tool()
def suggest_confidence_label(score: float) -> str:
    """Map a numeric confidence score to a UI-friendly label."""
    if score < 0.4:
        return "low"
    if score < 0.75:
        return "medium"
    return "high"


if __name__ == "__main__":
    mcp.run()