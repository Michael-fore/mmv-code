"""Exit analysis step — terminal value and appreciation scenarios."""


def compute_exit(deal: dict) -> dict:
    """Calculate terminal/exit value using the final year NOI and an exit cap rate.

    Needs: noi_schedule, exit_cap_rate, selling_cost_rate, purchase_price
    Adds: terminal_noi, gross_exit_value, selling_costs, exit_value, total_appreciation, appreciation_annualized
    """
    final_noi = deal["noi_schedule"][-1]["noi"]
    exit_cap = deal["exit_cap_rate"]
    sell_rate = deal["selling_cost_rate"]
    purchase = deal["purchase_price"]

    gross_exit = final_noi / exit_cap
    selling_costs = gross_exit * sell_rate
    net_exit = gross_exit - selling_costs

    total_appr = (net_exit - purchase) / purchase
    hold = len(deal["noi_schedule"])
    annual_appr = (1 + total_appr) ** (1 / hold) - 1 if hold > 0 else 0

    deal["terminal_noi"] = round(final_noi, 2)
    deal["gross_exit_value"] = round(gross_exit, 2)
    deal["selling_costs"] = round(selling_costs, 2)
    deal["exit_value"] = round(net_exit, 2)
    deal["total_appreciation"] = round(total_appr, 6)
    deal["appreciation_annualized"] = round(annual_appr, 6)
    return deal
