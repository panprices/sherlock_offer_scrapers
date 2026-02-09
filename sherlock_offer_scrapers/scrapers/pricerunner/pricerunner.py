from typing import Optional


from sherlock_offer_scrapers.helpers.offers import Offer
from . import gtin_searcher, offer_scraper


ENABLED_COUNTRIES = [
    "SE",
    "DK",
]


def scrape(gtin, cached_offer_urls: Optional[dict]) -> list[Offer]:
    # ip_addr = requests.get("https://api.ipify.org/").text

    all_offers: list[Offer] = []
    for country in ENABLED_COUNTRIES:
        if cached_offer_urls and f"pricerunner_{country}" in cached_offer_urls:
            url_path = cached_offer_urls[
                f"pricerunner_{country}"
            ]  # /pl/110-5286908/Datormoess/Logitech-MX-Anywhere-3-priser
            print(f"Reuse cached GTIN's pricerunner_{country} url: {url_path}")

            url_path = _get_offers_html_url(url_path, country)
        else:
            url_path = gtin_searcher.gtin_to_product_url(gtin, country)

        if not url_path:
            print("No product found for gtin", gtin, "in country", country)
            continue

        offers = offer_scraper.get_offers(url_path, country)
        all_offers.extend(offers)

    return all_offers


def _get_offers_html_url(partial_url_path: str, country: str) -> str:
    return f"https://www.pricerunner.{country.lower()}" + partial_url_path
