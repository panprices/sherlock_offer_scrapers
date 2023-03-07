import functools
import asyncio
import pydash.arrays
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
import structlog

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.helpers.offers import Offer
from . import user_agents, parser

logger = structlog.get_logger()

"""
!DEPRECATED: Only need to use gl={country} now, no need for UULE.

Using UULE parameter to access the offer page in different countries.
Read about UULE here: https://valentin.app/uule.html

https://www.google.ch/search?q=restaurant&hl=en&gl=SE&ie=utf-8&oe=utf-8&pws=0&uule=a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjUwMDE3MjQ0OTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ2OTQ3OTczOQpsb25naXR1ZGVfZTc6NzQ0NzQ0NjgKfQpyYWRpdXM6OTMwMDA%3D

"""
uule_of_country = {
    "SE": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU5MzI0ODk0NSwKbG9uZ2l0dWRlX2U3OjE4MDcwNjQ0MAp9CnJhZGl1czo5MzAwMAogICAgICAgICAg",  # Sweden
    "NO": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU5OTEwMDY4NiwKbG9uZ2l0dWRlX2U3OjEwNzQyMDk2Mgp9CnJhZGl1czo5MzAwMAo%3D",  # Norway
    "NL": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OiA1MjM0MjQ5NDAKbG9uZ2l0dWRlX2U3OiA0ODUzMjk5Mgp9CnJhZGl1czo5MzAwMAogICAgICAgICAg",  # Netherlands
    "AT": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ4MjA5NDI2NSwKbG9uZ2l0dWRlX2U3OjE2MzU5NTQ4NAp9CnJhZGl1czo5MzAwMAogICAgICAgICAg",  # Austria
    "PL": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjUyMjAwNDYzMwpsb25naXR1ZGVfZTc6MjA5MzM4OTgxCn0KcmFkaXVzOjkzMDAwCiAgICAgICAgICA%3D",  # Poland
    "BE": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTQxNjA0MzAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjUwODUwMzM5Ngpsb25naXR1ZGVfZTc6NDM1MTcxMDMKfQpyYWRpdXM6OTMwMDA%3D",  # Belgium
    "IE": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTY1NDY4MzAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjUzMzQ5ODA1Mwpsb25naXR1ZGVfZTc6LTYyNjAzMDk3Cn0KcmFkaXVzOjkzMDAw",  # Ireland
    "PT": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTg1NTMwNTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjM4NzIyMjUyNApsb25naXR1ZGVfZTc6LTkxMzkzMzY2Cn0KcmFkaXVzOjkzMDAw",  # Portugal
    "EE": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTkyMjk1NTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU5NDM2OTYwNwpsb25naXR1ZGVfZTc6MjQ3NTM1NzQ3Cn0KcmFkaXVzOjkzMDAw",  # Estonia
    "LT": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTk3MjIzOTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU0Njg3MTU1NQpsb25naXR1ZGVfZTc6MjUyNzk2NTE0Cn0KcmFkaXVzOjkzMDAw",  # Lithuania
    "LV": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjUwMDAxNDE3OTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU2OTQ5NjQ4Nwpsb25naXR1ZGVfZTc6MjQxMDUxODY1Cn0KcmFkaXVzOjkzMDAw",  # Latvia
    "CZ": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjUwMDExNDk5NzAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjUwMDc1NTM4MQpsb25naXR1ZGVfZTc6MTQ0Mzc4MDA1Cn0KcmFkaXVzOjkzMDAw",  # Czech Republic
    "CH": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjUwMDE3MjQ0OTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ2OTQ3OTczOQpsb25naXR1ZGVfZTc6NzQ0NzQ0NjgKfQpyYWRpdXM6OTMwMDA%3D",  # Switzerland
    "GR": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MzAzNjAzNDQ3NTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjM3OTgzODA5Ngpsb25naXR1ZGVfZTc6MjM3Mjc1Mzg4Cn0KcmFkaXVzOjkzMDAw",  # Greece
    "SK": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MzAzNjA4NTI5NzAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ4MTQ4NTk2NApsb25naXR1ZGVfZTc6MTcxMDc3NDc3Cn0KcmFkaXVzOjkzMDAw",  # Slovakia
    "RO": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0NDQxOTQ4MDcxMTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ0NDI2NzY3NApsb25naXR1ZGVfZTc6MjYxMDI1Mzg0Cn0KcmFkaXVzOjkzMDAw",  # Romania
    "HU": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0NDQxOTUzODkxMDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ3NDk3OTEyMApsb25naXR1ZGVfZTc6MTkwNDAyMzUwCn0KcmFkaXVzOjkzMDAw",  # Hungary
    "TR": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0NDQxOTU3OTEyMDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjM5OTMzMzYzNQpsb25naXR1ZGVfZTc6MzI4NTk3NDE5Cn0KcmFkaXVzOjkzMDAw",  # Turkey
    "RU": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0NDQxOTYwNjUzMTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU1NzU1ODI2MApsb25naXR1ZGVfZTc6Mzc2MTcyOTk5Cn0KcmFkaXVzOjkzMDAw",  # Russia
}


async def scrape(
    gtin: str,
    cached_offers_urls: Optional[dict],
    countries=["SE"],
) -> Tuple[List[helpers.offers.Offer], List[Tuple[Exception, str]]]:
    if not cached_offers_urls or "google_shopping" not in cached_offers_urls:
        print("No google shopping url provided")
        google_product_id = find_product_id(gtin)
        helpers.offers.publish_new_offer_urls(
            gtin, {"google_shopping": google_product_id}
        )

        if google_product_id is None:
            print(f"No product found for gtin {gtin}")
            return [], []
    else:
        google_product_id = cached_offers_urls["google_shopping"]

    all_searches = []
    for country in countries:
        coro = fetch_offers_from_google_product_id(google_product_id, gtin, country)  # type: ignore
        all_searches.append(coro)

    offer_results = await asyncio.gather(*all_searches)

    all_offers = []
    exceptions = []
    for (offers, country, exception) in offer_results:
        all_offers.extend(offers)
        if exception is not None:
            exceptions.append((exception, country))

    return all_offers, exceptions


def find_product_id(gtin: str) -> Optional[str]:
    """Find product_id of a google shopping product based on GTIN."""
    # TODO: Parameterize this
    COUNTRY_TO_SEARCH_ON = "se"
    url = f"https://www.google.com/search?q={gtin}&gl={COUNTRY_TO_SEARCH_ON}&hl=en&tbm=shop"
    html = helpers.requests.get(
        url,
        headers={"User-Agent": user_agents.choose_random()},
        cookies={"CONSENT": "YES+cb.20210329-17-p2.en+FX+900"},
        proxy_country="SE",
    ).text
    soup = BeautifulSoup(html, features="html.parser")

    all_a_tags = soup.select("a.Lq5OHe")
    # Only consider links to google shopping products. Ignore links directly to seller websites.
    product_a_tags = [a for a in all_a_tags if "/shopping/product" in a["href"]]
    possible_product_ids = set(
        a["href"].split("?")[0].split("/")[3]
        for a in product_a_tags
        # /shopping/product/2336121681419728525?q=05400653007411&hl=en&... -> 2336121681419728525
    )
    if len(possible_product_ids) == 0:
        return None
    if len(possible_product_ids) > 1:
        logger.warning(
            "Multiple google shopping product ids found",
            gtin=gtin,
            product_ids=list(possible_product_ids),
        )
        return None

    product_id = possible_product_ids.pop()
    return product_id


async def fetch_offers_from_google_product_id(
    google_pid: str,
    gtin: str,
    country: str,
) -> Tuple[list[Offer], str, Optional[Exception]]:
    try:
        proxy_country = "DE"  # always use DE proxy
        url = (
            f"https://www.google.com/shopping/product/{google_pid}/offers"
            + f"?hl=en&gl={country}"
        )

        loop = asyncio.get_event_loop()

        response = await loop.run_in_executor(
            None,
            functools.partial(
                helpers.requests.get,
                url,
                headers={"User-Agent": user_agents.choose_random()},
                proxy_country=proxy_country,
                offer_source_country=country,
            ),
        )

        soup = BeautifulSoup(response.text, "html.parser")
        try:
            offers = parser.parser_offer_page(soup, country)
            return offers, country, None
        except Exception as ex:
            logger.msg("error parsing html", country=country, exception=str(ex))
            helpers.dump_html.dump_html(
                response.text,
                "google_shopping",
                gtin,
                country,
            )
            raise ex
    except Exception as ex:
        logger.error(
            "error when fetching offers",
            google_pid=google_pid,
            country=country,
            error=str(ex),
        )
        return [], country, ex
