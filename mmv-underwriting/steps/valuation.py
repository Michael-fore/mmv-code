"""Valuation steps — cap rate and comparable sales approaches."""


def apply_cap_rate(deal: dict) -> dict:
    """Value the property using the income capitalization approach.

    Needs: noi, cap_rate
    Adds: cap_rate_value, price_per_acre_cap
    """
    value = deal["noi"] / deal["cap_rate"]
    deal["cap_rate_value"] = round(value, 2)
    deal["price_per_acre_cap"] = round(value / deal["acres"], 2)
    return deal


def value_by_comps(deal: dict) -> dict:
    """Value the property using comparable sales.

    Needs: acres, comp_sales
    Adds: comp_value, comp_price_per_acre, comp_spread

    comp_sales should be a list of dicts with at least:
      {"price_per_acre": float, "acres": float, "csr2": float}
    """
    comps = deal["comp_sales"]
    if not comps:
        deal["comp_value"] = None
        deal["comp_price_per_acre"] = None
        deal["comp_spread"] = None
        return deal

    prices = [c["price_per_acre"] for c in comps]
    avg_price = sum(prices) / len(prices)
    value = avg_price * deal["acres"]

    deal["comp_value"] = round(value, 2)
    deal["comp_price_per_acre"] = round(avg_price, 2)
    deal["comp_spread"] = round(max(prices) - min(prices), 2)
    return deal
