"""
Composable analysis engine for MMV underwriting.

Design principles (optimized for LLM + non-coder execution):
- Every step is a plain function: dict -> dict
- Steps declare what they Need and what they Add via docstring
- A chain is a list of steps executed in order
- No classes, no decorators, no implicit state
- Flat dicts, not nested objects
"""


def run_chain(deal: dict, steps: list) -> dict:
    """Run a list of analysis steps sequentially on a deal dict.

    Each step receives the full deal dict, enriches it, and returns it.
    Steps are plain functions with signature: dict -> dict.

    Needs: a deal dict with at least the keys required by the first step
    Adds: all keys added by all steps in the chain
    """
    for step in steps:
        deal = step(deal)
    return deal


def describe_step(step) -> dict:
    """Extract the Needs/Adds contract from a step's docstring.

    Returns {"name": str, "doc": str, "needs": list[str], "adds": list[str]}
    Useful for LLM agents deciding which steps to chain.
    """
    doc = (step.__doc__ or "").strip()
    needs = []
    adds = []
    for line in doc.splitlines():
        line = line.strip()
        if line.lower().startswith("needs:"):
            needs = [k.strip() for k in line.split(":", 1)[1].split(",")]
        elif line.lower().startswith("adds:"):
            adds = [k.strip() for k in line.split(":", 1)[1].split(",")]
    return {
        "name": step.__name__,
        "doc": doc,
        "needs": needs,
        "adds": adds,
    }


def describe_chain(steps: list) -> list[dict]:
    """Describe all steps in a chain. Useful for LLM introspection."""
    return [describe_step(s) for s in steps]


def validate_chain(deal: dict, steps: list) -> list[str]:
    """Check that each step's Needs are satisfied by prior Adds or initial deal keys.

    Returns a list of error strings. Empty list means the chain is valid.
    """
    available = set(deal.keys())
    errors = []
    for step in steps:
        info = describe_step(step)
        missing = [k for k in info["needs"] if k not in available]
        if missing:
            errors.append(f"{info['name']}: missing {missing}")
        available.update(info["adds"])
    return errors
