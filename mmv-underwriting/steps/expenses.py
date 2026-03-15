"""Operating expense projection step."""


def project_expenses(deal: dict) -> dict:
    """Project operating expenses over the hold period.

    Needs: acres, tax_per_acre, insurance_per_acre, management_rate, maintenance_per_acre, hold_years, expense_growth_rate, revenue_schedule
    Adds: operating_expenses, expense_schedule
    """
    acres = deal["acres"]
    tax = deal["tax_per_acre"]
    insurance = deal["insurance_per_acre"]
    mgmt_rate = deal["management_rate"]
    maint = deal["maintenance_per_acre"]
    growth = deal["expense_growth_rate"]
    revenue_schedule = deal["revenue_schedule"]

    schedule = []
    for entry in revenue_schedule:
        year = entry["year"]
        egi = entry["effective_gross_income"]
        g = (1 + growth) ** (year - 1)
        taxes = acres * tax * g
        ins = acres * insurance * g
        mgmt = egi * mgmt_rate
        maintenance = acres * maint * g
        total = taxes + ins + mgmt + maintenance
        schedule.append({
            "year": year,
            "taxes": round(taxes, 2),
            "insurance": round(ins, 2),
            "management": round(mgmt, 2),
            "maintenance": round(maintenance, 2),
            "total_expenses": round(total, 2),
        })

    deal["operating_expenses"] = schedule[0]["total_expenses"]
    deal["expense_schedule"] = schedule
    return deal
