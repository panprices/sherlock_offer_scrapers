import functools
import asyncio
from typing import Optional

from bs4 import BeautifulSoup
import structlog

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.helpers.offers import Offer
from . import user_agents, parser

logger = structlog.get_logger()

"""
Using UULE parameter to access the offer page in different countries.
Read about UULE here: https://valentin.app/uule.html
"""
uule_of_country = {
    "SE": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU5MzI0ODk0NSwKbG9uZ2l0dWRlX2U3OjE4MDcwNjQ0MAp9CnJhZGl1czo5MzAwMAogICAgICAgICAg",
    "NL": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OiA1MjM0MjQ5NDAKbG9uZ2l0dWRlX2U3OiA0ODUzMjk5Mgp9CnJhZGl1czo5MzAwMAogICAgICAgICAg",
    "AT": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ4MjA5NDI2NSwKbG9uZ2l0dWRlX2U3OjE2MzU5NTQ4NAp9CnJhZGl1czo5MzAwMAogICAgICAgICAg",
    "PL": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjUyMjAwNDYzMwpsb25naXR1ZGVfZTc6MjA5MzM4OTgxCn0KcmFkaXVzOjkzMDAwCiAgICAgICAgICA%3D",
}


async def scrape(
    gtin: str,
    cached_offers_urls: Optional[dict],
    countries=["SE"],
) -> list[helpers.offers.Offer]:
    if not cached_offers_urls or "google_shopping" not in cached_offers_urls:
        print("No google shopping url provided")
        return []

    google_product_id = cached_offers_urls["google_shopping"]
    all_searches = []
    for country in countries:
        coro = fetch_offers_from_google_product_id(google_product_id, country)
        all_searches.append(coro)

    all_offers = await asyncio.gather(*all_searches)
    return all_offers


async def fetch_offers_from_google_product_id(
    google_pid: str,
    country: str,
) -> list[Offer]:
    proxy_country = "DE"  # always use DE proxy
    url = (
        f"https://www.google.com/shopping/product/{google_pid}/offers"
        + f"?hl=en&gl={country}&uule={uule_of_country[country]}"
    )

    loop = asyncio.get_event_loop()

    logger.msg("fetching url", url=url)

    response = await loop.run_in_executor(
        None,
        functools.partial(
            helpers.requests.get,
            url,
            headers={"User-Agent": user_agents.choose_random()},
            proxy_country=proxy_country,
        ),
    )

    soup = BeautifulSoup(response.text, "html.parser")
    offers = parser.parser_offer_page(soup, country)
    return offers
