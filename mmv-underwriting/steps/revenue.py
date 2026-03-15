"""Revenue projection step."""


def project_revenue(deal: dict) -> dict:
    """Project gross revenue and effective gross income over the hold period.

    Needs: acres, tillable_acres, cash_rent_per_acre, vacancy_rate, hold_years, revenue_growth_rate
    Adds: gross_revenue, effective_gross_income, revenue_schedule
    """
    tillable = deal["tillable_acres"]
    rent = deal["cash_rent_per_acre"]
    vacancy = deal["vacancy_rate"]
    growth = deal["revenue_growth_rate"]
    hold = deal["hold_years"]

    schedule = []
    for year in range(1, hold + 1):
        year_rent = rent * ((1 + growth) ** (year - 1))
        gross = tillable * year_rent
        egi = gross * (1 - vacancy)
        schedule.append({
            "year": year,
            "rent_per_acre": round(year_rent, 2),
            "gross_revenue": round(gross, 2),
            "effective_gross_income": round(egi, 2),
        })

    deal["gross_revenue"] = schedule[0]["gross_revenue"]
    deal["effective_gross_income"] = schedule[0]["effective_gross_income"]
    deal["revenue_schedule"] = schedule
    return deal
