"""Return analysis steps — IRR, cash-on-cash, equity multiple, DSCR."""


def compute_irr(deal: dict) -> dict:
    """Calculate the Internal Rate of Return over the hold period.

    Needs: purchase_price, noi_schedule, exit_value
    Adds: irr

    Uses Newton's method to solve for the discount rate where NPV = 0.
    Cash flows: -purchase_price at year 0, NOI each year, NOI + exit_value in final year.
    """
    price = deal["purchase_price"]
    noi_sched = deal["noi_schedule"]
    exit_val = deal["exit_value"]

    # Build cash flow series
    cashflows = [-price]
    for i, entry in enumerate(noi_sched):
        cf = entry["noi"]
        if i == len(noi_sched) - 1:
            cf += exit_val
        cashflows.append(cf)

    # Newton's method for IRR
    rate = 0.08  # initial guess
    for _ in range(200):
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))
        dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cashflows))
        if abs(dnpv) < 1e-12:
            break
        rate = rate - npv / dnpv
        if abs(npv) < 0.01:
            break

    deal["irr"] = round(rate, 6)
    return deal


def compute_cash_on_cash(deal: dict) -> dict:
    """Calculate the first-year cash-on-cash return.

    Needs: noi, annual_debt_service, equity_invested
    Adds: cash_on_cash

    If no debt (annual_debt_service is 0 or missing), uses NOI directly.
    """
    noi = deal["noi"]
    debt_service = deal.get("annual_debt_service", 0)
    equity = deal["equity_invested"]

    cfbt = noi - debt_service
    deal["cash_on_cash"] = round(cfbt / equity, 6) if equity else 0
    return deal


def compute_equity_multiple(deal: dict) -> dict:
    """Calculate the equity multiple over the full hold period.

    Needs: equity_invested, noi_schedule, exit_value, annual_debt_service
    Adds: equity_multiple

    Equity multiple = total distributions / equity invested.
    """
    equity = deal["equity_invested"]
    debt_service = deal.get("annual_debt_service", 0)
    noi_sched = deal["noi_schedule"]
    exit_val = deal["exit_value"]

    total_cf = sum(entry["noi"] - debt_service for entry in noi_sched) + exit_val
    deal["equity_multiple"] = round(total_cf / equity, 4) if equity else 0
    return deal


def compute_dscr(deal: dict) -> dict:
    """Calculate the Debt Service Coverage Ratio.

    Needs: noi, annual_debt_service
    Adds: dscr

    DSCR = NOI / annual debt service. Returns None if no debt.
    """
    debt_service = deal.get("annual_debt_service", 0)
    if debt_service <= 0:
        deal["dscr"] = None
        return deal

    deal["dscr"] = round(deal["noi"] / debt_service, 4)
    return deal
