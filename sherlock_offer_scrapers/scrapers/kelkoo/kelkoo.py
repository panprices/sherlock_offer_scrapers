import json
import os
from unicodedata import category

import structlog

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.helpers.utils import gtin_to_ean
from sherlock_offer_scrapers.helpers.offers import Offer

COUNTRIES = [
    "DE",
    "FR",
    "NO",
    "SE",
    "DK",
    "FI",
    "UK",
    "NL",
    "PL",
    "BE",
    "IE",
    "PT",
    "CZ",
    "CH",
    # "EE", # Does not exist on Kelkoo's platform
    # "LT", # Does not exist on Kelkoo's platform
    # "LV", # Does not exist on Kelkoo's platform
    "GR",
    "SK",
]
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
    ean = gtin_to_ean(gtin)
    url = (
        f"https://api.kelkoogroup.net/publisher/shopping/v2/search/offers"
        + f"?country={country.lower()}"
        + f"&filterBy=codeEan:{ean}"
        + f"&additionalFields=merchantName,categoryName,description"
    )

    jwt = os.getenv("KELKOO_JWT_TOKEN")
    response = helpers.requests.get(
        url,
        headers={
            "Authorization": f"Bearer {jwt}",
        },
    )
    if response.status_code != 200:
        if response.status_code < 500:
            logger.error("request failed", response=response.text)
        raise Exception(
            f"Status code: {response.status_code} when requesting to url: {url}"
        )

    offers = _parse_result(response.json(), country)
    return offers


def _parse_result(result: dict, country: str) -> list[Offer]:
    offers: list[Offer] = []
    for kelkoo_offer in result["offers"]:
        category = kelkoo_offer.get("category", {}).get("name", "")
        category = [category] if len(category) > 0 else []

        images = [
            image.get("zoomUrl")
            for image in kelkoo_offer.get("images", [])
            if image.get("zoomUrl") is not None
        ]

        print(kelkoo_offer.get("images"))

        offer: Offer = {
            "offer_source": "kelkoo_" + country,
            "offer_url": kelkoo_offer["goUrl"],
            "retail_prod_name": kelkoo_offer["title"],
            "retailer_name": kelkoo_offer["merchant"]["name"],
            "country": country,
            "price": round(float(kelkoo_offer["price"]) * 100),
            "currency": kelkoo_offer["currency"],
            "stock_status": _parse_stock_status(kelkoo_offer["availabilityStatus"]),
            "metadata": json.dumps(
                {
                    "description": kelkoo_offer.get("description"),
                    "brand": kelkoo_offer.get("brand", {}).get("name", ""),
                    "category": category,
                    "images": images,
                }
            ),
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
