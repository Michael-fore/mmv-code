"""Net Operating Income projection step."""


def project_noi(deal: dict) -> dict:
    """Calculate Net Operating Income for each year of the hold period.

    Needs: revenue_schedule, expense_schedule
    Adds: noi, noi_schedule
    """
    rev = deal["revenue_schedule"]
    exp = deal["expense_schedule"]

    schedule = []
    for r, e in zip(rev, exp):
        noi = r["effective_gross_income"] - e["total_expenses"]
        schedule.append({
            "year": r["year"],
            "effective_gross_income": r["effective_gross_income"],
            "total_expenses": e["total_expenses"],
            "noi": round(noi, 2),
        })

    deal["noi"] = schedule[0]["noi"]
    deal["noi_schedule"] = schedule
    return deal
