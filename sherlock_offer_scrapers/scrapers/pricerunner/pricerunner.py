from typing import Optional

import requests

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.helpers.offers import Offer
from .search import query_products
from .common import BASE_URL, _make_request, pause_execution_random, create_session
from . import common
from . import parser


ENABLED_COUNTRIES = [
    "SE",
    # "DK",
]


def scrape(gtin, cached_offer_urls: Optional[dict]) -> list[Offer]:
    # ip_addr = requests.get("https://api.ipify.org/").text

    all_offers: list[Offer] = []
    for country in ENABLED_COUNTRIES:
        if not cached_offer_urls or f"pricerunner_{country}" not in cached_offer_urls:
            url_path = query_products(
                gtin, country
            )  # /pl/110-5286908/Datormoess/Logitech-MX-Anywhere-3-priser
        else:
            url_path = cached_offer_urls[f"pricerunner_{country}"]
            print(f"Reuse cached GTIN's pricerunner_{country} url: {url_path}")

        if not url_path:
            print("No product found for gtin", gtin, "in country", country)

        print(url_path)
        offers = get_offers(url_path, wait=False)
        all_offers.extend(offers)

    return all_offers


def get_offers(url_path, country="SE", wait=True) -> list[Offer]:
    # Logic: Fetch the offers page (html), then wait a bit and fetch the data API
    # using the same session to disguise as a real user.
    session = create_session(country)
    product_page_url = _get_offers_html_url(url_path, country)
    print("product_page_url", product_page_url)
    _make_request(product_page_url, session)

    # wait a little bit
    if wait:
        pause_execution_random(min_sec=2, max_sec=5)

    # # fetch the offer data
    offer_url = get_offer_api_url(url_path, country)
    print("url:", url_path)
    response = _make_request(offer_url, session)
    # when the link is incorrect, pricerunner api actually return 204, not 404
    if response.status_code == 204 or response.status_code >= 400:
        print(f"status code: {response.status_code} when requesting to {offer_url}")
        return []
    else:
        return parser.parse_offers(response.json(), country)


def _get_offers_html_url(url_path, country):
    return f"https://www.pricerunner.{country.lower()}" + url_path


def get_offer_api_url(url_path: str, country: str) -> str:
    [_, dir, id, category, product] = url_path.split("/")
    return f"{common.BASE_URL[country]}/public/productlistings/v3/{dir}/{id}/{country.lower()}/filter?offer_sort=price"
