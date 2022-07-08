from itertools import count

from sherlock_offer_scrapers.helpers.offers import Offer
from . import common
from .common import BASE_URL, _make_request, pause_execution_random, create_session


DELAY_BETWEEN_REQUESTS_RANGE_SECONDS = [2, 5]


def get_offers(product_page_url: str, country: str) -> list[Offer]:
    # Logic: Fetch the offers page (html), then wait a bit and fetch the data API
    # using the same session to disguise as a real user.
    session = create_session(country)
    _make_request(product_page_url, session)

    # wait a little bit between requests
    pause_execution_random(*DELAY_BETWEEN_REQUESTS_RANGE_SECONDS)

    # # fetch the offer data
    offer_url = _get_offer_api_url(product_page_url, country)
    response = _make_request(offer_url, session)
    # when the link is incorrect, pricerunner api actually return 204, not 404
    if response.status_code == 204 or response.status_code >= 400:
        print(f"status code: {response.status_code} when requesting to {offer_url}")
        return []
    else:
        return _parse_offers(response.json(), country)


def _get_offer_api_url(product_url: str, country: str) -> str:
    dir, id = product_url.split("/")[3:5]
    return f"{common.BASE_URL[country]}/public/productlistings/v3/{dir}/{id}/{country.lower()}/filter?offer_sort=price"


def _parse_offers(json_result: dict, country: str) -> list[Offer]:
    offers: list[Offer] = []

    merchants = json_result["filteredOfferList"]["merchants"]

    for merchant_offer in json_result["filteredOfferList"]["merchantOffers"]:
        offer_info = merchant_offer["offers"][0]
        retail_prod_name = offer_info["name"]
        offer_url = _extract_full_offer_url(offer_info["url"], country)
        price = _extract_price(merchant_offer["price"]["amount"])
        stock_status = _extract_stock_status(offer_info["stockStatus"])
        offer: Offer = {
            "offer_source": f"pricerunner_{country}",
            "offer_url": offer_url,
            "retail_prod_name": retail_prod_name,
            "retailer_name": merchants[merchant_offer["merchantId"]]["name"],
            "country": country,
            "price": price,
            "currency": merchant_offer["price"]["currency"],
            "stock_status": stock_status,
            "metadata": None,
        }
        offers.append(offer)

    return offers


def _extract_full_offer_url(url: str, country: str) -> str:
    """Example:
    url = "/gotostore/v1/SE/2091_106753?productId=3345033"
    country = "SE"

    return https://wwww.pricerunner.se/gotostore/v1/SE/2091_106753?productId=3345033
    """
    return common.BASE_URL[country] + url


def _extract_price(amount: str) -> int:
    return int(float(amount) * 100)


def _extract_stock_status(pricerunner_stock_status: str):
    if pricerunner_stock_status == "IN_STOCK":
        stock_status = "in_stock"
    elif pricerunner_stock_status == "OUT_OF_STOCK":
        stock_status = "out_of_stock"
    else:
        stock_status = "unknown"

    return stock_status
