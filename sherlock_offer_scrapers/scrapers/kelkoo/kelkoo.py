import logging
import time
import hashlib
import base64
import os
import datetime

from .user_agents import get_user_agent
from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.helpers.offers import Offer


COUNTRIES = ["DE", "FR", "NO", "SE", "DK", "FI", "UK", "NL", "PL"]
# COUNTRIES = ["SE"]


def scrape(gtin: str):
    all_offers = []
    for country in COUNTRIES:
        offers = fetch_offers(country, gtin)
        if offers:
            all_offers.extend(offers)

    return all_offers


# Checks if gtin is a GTIN14 and if so, converts to GTIN13
def _gtin_to_ean(gtin: str) -> str:
    if len(gtin) == 14:
        return gtin[1:14]
    if len(gtin) == 13:
        return gtin
    if len(gtin) < 13:
        return gtin.zfill(13)

    raise ValueError(f"cannot convert gtin to ean: {gtin} is not a valid gtin.")


def _parse_stock_status(kelkoo_availability_status: str):
    """Map Kelkoo's availabilityStatus to Panprices stock_status."""
    mapping = {
        "in_stock": "in_stock",
        "available_on_order": "in_stock",
        "check_site": "unknown",
    }
    if kelkoo_availability_status in mapping:
        return mapping[kelkoo_availability_status]

    print("Unknown availability status:", kelkoo_availability_status)
    return "unknown"


def _get_headers():
    jwt = os.getenv("KELKOO_JWT_TOKEN")
    return {
        # Random generated user agent
        "User-Agent": get_user_agent(),
        "Authorization": f"Bearer {jwt}",
    }


def _parse_result(result: dict, country: str) -> list[Offer]:
    # kelkoo_offers = result["offers"]
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
            # deliveryCost: kelkoo_offer["deliveryCost"],
            # totalPrice: kelkoo_offer["totalPrice"],
            # "product_id": id,
            # "requested_at": str(datetime.datetime.now()),
        }
        offers.append(offer)

    return offers


def fetch_offers(country: str, gtin: str) -> list[Offer]:
    # Make request:
    ean = _gtin_to_ean(gtin)
    url = (
        f"https://api.kelkoogroup.net/publisher/shopping/v2/search/offers"
        + f"?country={country.lower()}&filterBy=codeEan:{ean}&additionalFields=merchantName"
    )

    response = helpers.requests.get(url, headers=_get_headers())
    # TODO: <Response [404]>,
    # Don't know why we cannot open XML at the first time,
    # but refresh can solve this problem
    if response.status_code == 404:
        # Try again
        response = helpers.requests.get(url, headers=_get_headers())
        if response.status_code == 404:
            logging.warning(f"404 when request for gtin {gtin} from {country}")
            return []

    offers = _parse_result(response.json(), country)
    return offers
