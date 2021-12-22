import os

import structlog

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.helpers.offers import Offer

COUNTRIES = ["DE", "FR", "NO", "SE", "DK", "FI", "UK", "NL", "PL"]
# COUNTRIES = ["SE"]

logger = structlog.get_logger()


def scrape(gtin: str):
    all_offers = []
    for country in COUNTRIES:
        offers = fetch_offers(country, gtin)
        if offers:
            all_offers.extend(offers)

    return all_offers


def fetch_offers(country: str, gtin: str) -> list[Offer]:
    # Make request:
    ean = _gtin_to_ean(gtin)
    url = (
        f"https://api.kelkoogroup.net/publisher/shopping/v2/search/offers"
        + f"?country={country.lower()}"
        + f"&filterBy=codeEan:{ean}"
        + f"&additionalFields=merchantName"
    )

    jwt = os.getenv("KELKOO_JWT_TOKEN")
    response = helpers.requests.get(
        url,
        headers={
            "Authorization": f"Bearer {jwt}",
        },
    )
    if response.status_code != 200:
        raise Exception(
            f"Status code: {response.status_code} when requesting to url: {url}"
        )

    offers = _parse_result(response.json(), country)
    return offers


# Checks if gtin is a GTIN14 and if so, converts to GTIN13
def _gtin_to_ean(gtin: str) -> str:
    if len(gtin) == 14:
        return gtin[1:14]
    if len(gtin) == 13:
        return gtin
    if len(gtin) < 13:
        return gtin.zfill(13)

    raise ValueError(f"cannot convert gtin to ean: {gtin} is not a valid gtin.")


def _parse_result(result: dict, country: str) -> list[Offer]:
    offers: list[Offer] = []
    for kelkoo_offer in result["offers"]:
        offer: Offer = {
            "offer_source": "kelkoo_" + country,
            "offer_url": kelkoo_offer["goUrl"],
            "retail_prod_name": kelkoo_offer["title"],
            "retailer_name": kelkoo_offer["merchant"]["name"],
            "country": country,
            "price": round(float(kelkoo_offer["price"]) * 100),
            "currency": kelkoo_offer["currency"],
            "stock_status": _parse_stock_status(kelkoo_offer["availabilityStatus"]),
            # "deliveryCost": kelkoo_offer["deliveryCost"],
            # "totalPrice": kelkoo_offer["totalPrice"],
        }
        offers.append(offer)

    return offers


def _parse_stock_status(kelkoo_availability_status: str):
    """Map Kelkoo's availabilityStatus to Panprices stock_status."""
    mapping = {
        "in_stock": "in_stock",
        "available_on_order": "in_stock",
        "pre_order": "out_of_stock",
        "not_in_stock": "out_of_stock",
        "check_site": "unknown",
    }
    if kelkoo_availability_status not in mapping:
        logger.warning(
            f"unknown availability status",
            kelkoo_availability_status=kelkoo_availability_status,
        )
        return "unknown"

    return mapping[kelkoo_availability_status]
