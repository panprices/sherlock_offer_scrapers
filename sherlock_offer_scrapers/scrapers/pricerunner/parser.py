from itertools import count

from sherlock_offer_scrapers.helpers.offers import Offer
from . import common


def parse_offers(json_result: dict, country: str) -> list[Offer]:
    offers: list[Offer] = []

    merchants = json_result["filteredOfferList"]["merchants"]

    for merchant_offer in json_result["filteredOfferList"]["merchantOffers"]:
        offer_info = merchant_offer["offers"][0]
        retail_prod_name = offer_info["name"]
        offer_url = get_offer_url(offer_info["url"], country)
        stock_status = _extract_stock_status(offer_info["stockStatus"])
        offer: Offer = {
            "offer_source": f"pricerunner_{country}",
            "offer_url": offer_url,
            "retail_prod_name": retail_prod_name,
            "retailer_name": merchants[merchant_offer["merchantId"]]["name"],
            "country": country,
            "price": price_amount_to_cents(merchant_offer["price"]["amount"]),
            "currency": merchant_offer["price"]["currency"],
            "stock_status": stock_status,
            "metadata": None,
        }
        offers.append(offer)

    return offers


def price_amount_to_cents(amount: str) -> int:
    return int(float(amount) * 100)


def get_offer_url(url: str, country: str) -> str:
    """Example:
    url = "/gotostore/v1/SE/2091_106753?productId=3345033"
    country = "SE"

    return https://wwww.pricerunner.se/gotostore/v1/SE/2091_106753?productId=3345033
    """
    return common.BASE_URL[country] + url


def _extract_stock_status(pricerunner_stock_status: str):
    if pricerunner_stock_status == "IN_STOCK":
        stock_status = "in_stock"
    elif pricerunner_stock_status == "OUT_OF_STOCK":
        stock_status = "out_of_stock"
    else:
        stock_status = "unknown"

    return stock_status
