import asyncio
import functools
from typing import List, Optional, Tuple

import structlog
from bs4 import BeautifulSoup

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.helpers.offers import Offer
from . import user_agents, parser

logger = structlog.get_logger()


# Using UULE parameter to access the offer page in different countries.
# Read about UULE here: https://valentin.app/uule.html
# You can create new UULE using that website as well.

# Example: https://www.google.com/search?q=restaurant&hl=en&gl=SE&ie=utf-8&oe=utf-8&pws=0&uule=w+CAIQICIYRnJpZWRyaWNoc3dlcmRlciwgQmVybGlu
uule_of_country = {
    "DE": "w+CAIQICIYRnJpZWRyaWNoc3dlcmRlciwgQmVybGlu",
    "NL": "w+CAIQICIYQm9zIGVuIExvbW1lciwgQW1zdGVyZGFt",
    "DK": "w+CAIQICIaVmVzdGVyYnJvIMO4c3QsIENvcGVuaGFnZW4%3D",
    "IT": "w+CAIQICIQUm9tZSxMYXppbyxJdGFseQ%3D%3D",
    "US": "w+CAIQICImV2VzdCBOZXcgWW9yayxOZXcgSmVyc2V5LFVuaXRlZCBTdGF0ZXM%3D",
    "CH": "w+CAIQICIcRGlldGxpa29uLFp1cmljaCxTd2l0emVybGFuZA%3D%3D",
    "SE": "w+CAIQICIXU3RvY2tob2xtIENvdW50eSxTd2VkZW4%3D",
    "NO": "w+CAIQICIdT3NsbyBNdW5pY2lwYWxpdHksT3NsbyxOb3J3YXk%3D",
    "FR": "w+CAIQICIgTHlvbixBdXZlcmduZS1SaG9uZS1BbHBlcyxGcmFuY2U%3D",
    "ES": "w+CAIQICIWUmVnaW9uIG9mIE11cmNpYSxTcGFpbg%3D%3D",
}


# DEPRECATED: This is UULE version 2 accordding to https://valentin.app/uule.html,
# and it used to work but not anymore. Now only the version 1 above works.
# Keeping it commented here so that we remember this exists and in case it works again
# in the future.
# uule_of_country = {
#     "SE": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU5MzI0ODk0NSwKbG9uZ2l0dWRlX2U3OjE4MDcwNjQ0MAp9CnJhZGl1czo5MzAwMAogICAgICAgICAg",  # Sweden
#     "NO": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU5OTEwMDY4NiwKbG9uZ2l0dWRlX2U3OjEwNzQyMDk2Mgp9CnJhZGl1czo5MzAwMAo%3D",  # Norway
#     "NL": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OiA1MjM0MjQ5NDAKbG9uZ2l0dWRlX2U3OiA0ODUzMjk5Mgp9CnJhZGl1czo5MzAwMAogICAgICAgICAg",  # Netherlands
#     "AT": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ4MjA5NDI2NSwKbG9uZ2l0dWRlX2U3OjE2MzU5NTQ4NAp9CnJhZGl1czo5MzAwMAogICAgICAgICAg",  # Austria
#     "PL": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTU5MTUyMTI0OTAzNDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjUyMjAwNDYzMwpsb25naXR1ZGVfZTc6MjA5MzM4OTgxCn0KcmFkaXVzOjkzMDAwCiAgICAgICAgICA%3D",  # Poland
#     "BE": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTQxNjA0MzAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjUwODUwMzM5Ngpsb25naXR1ZGVfZTc6NDM1MTcxMDMKfQpyYWRpdXM6OTMwMDA%3D",  # Belgium
#     "IE": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTY1NDY4MzAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjUzMzQ5ODA1Mwpsb25naXR1ZGVfZTc6LTYyNjAzMDk3Cn0KcmFkaXVzOjkzMDAw",  # Ireland
#     "PT": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTg1NTMwNTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjM4NzIyMjUyNApsb25naXR1ZGVfZTc6LTkxMzkzMzY2Cn0KcmFkaXVzOjkzMDAw",  # Portugal
#     "EE": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTkyMjk1NTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU5NDM2OTYwNwpsb25naXR1ZGVfZTc6MjQ3NTM1NzQ3Cn0KcmFkaXVzOjkzMDAw",  # Estonia
#     "LT": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjQ5OTk3MjIzOTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU0Njg3MTU1NQpsb25naXR1ZGVfZTc6MjUyNzk2NTE0Cn0KcmFkaXVzOjkzMDAw",  # Lithuania
#     "LV": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjUwMDAxNDE3OTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU2OTQ5NjQ4Nwpsb25naXR1ZGVfZTc6MjQxMDUxODY1Cn0KcmFkaXVzOjkzMDAw",  # Latvia
#     "CZ": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjUwMDExNDk5NzAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjUwMDc1NTM4MQpsb25naXR1ZGVfZTc6MTQ0Mzc4MDA1Cn0KcmFkaXVzOjkzMDAw",  # Czech Republic
#     "CH": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MjUwMDE3MjQ0OTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ2OTQ3OTczOQpsb25naXR1ZGVfZTc6NzQ0NzQ0NjgKfQpyYWRpdXM6OTMwMDA%3D",  # Switzerland
#     "GR": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MzAzNjAzNDQ3NTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjM3OTgzODA5Ngpsb25naXR1ZGVfZTc6MjM3Mjc1Mzg4Cn0KcmFkaXVzOjkzMDAw",  # Greece
#     "SK": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0MzAzNjA4NTI5NzAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ4MTQ4NTk2NApsb25naXR1ZGVfZTc6MTcxMDc3NDc3Cn0KcmFkaXVzOjkzMDAw",  # Slovakia
#     "RO": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0NDQxOTQ4MDcxMTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ0NDI2NzY3NApsb25naXR1ZGVfZTc6MjYxMDI1Mzg0Cn0KcmFkaXVzOjkzMDAw",  # Romania
#     "HU": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0NDQxOTUzODkxMDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjQ3NDk3OTEyMApsb25naXR1ZGVfZTc6MTkwNDAyMzUwCn0KcmFkaXVzOjkzMDAw",  # Hungary
#     "TR": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0NDQxOTU3OTEyMDAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjM5OTMzMzYzNQpsb25naXR1ZGVfZTc6MzI4NTk3NDE5Cn0KcmFkaXVzOjkzMDAw",  # Turkey
#     "RU": "a+cm9sZToxCnByb2R1Y2VyOjEyCnByb3ZlbmFuY2U6Ngp0aW1lc3RhbXA6MTY0NDQxOTYwNjUzMTAwMApsYXRsbmd7CmxhdGl0dWRlX2U3OjU1NzU1ODI2MApsb25naXR1ZGVfZTc6Mzc2MTcyOTk5Cn0KcmFkaXVzOjkzMDAw",  # Russia
# }


async def scrape_one_country(
    gtin: Optional[str],
    sku: Optional[str],
    cached_offers_urls: Optional[dict],
    country: str,
) -> Tuple[List[helpers.offers.Offer], List[Tuple[Exception, str]]]:
    offer_sources = ["google_shopping"]
    if country.upper() != "SE":
        """
        Sweden is a special case because this code used to search only in Sweden and we already have entries in the
        database with "google_shopping" as `offer_source`.

        That's why you will find "google_shopping_DK", but not "google_shopping_SE" in the database.

        June 2024 update: Now we use "google_shopping" as the default source, so an URL can be assigned to a country
        with the "google_shopping_DE" source, or it can be used in all the countries by using "google_shopping"
        """
        offer_sources += [f"google_shopping_{country.upper()}"]

    if not cached_offers_urls:
        logger.warning(
            "Search by GTIN has been disabled for google_shopping. "
            + "No cached url provided, cannot fetch offers.",
            offer_source=offer_sources,
            gtin=gtin,
        )
        return [], []

    product_urls = [u for s in offer_sources for u in cached_offers_urls.get(s, [])]
    if not product_urls:
        logger.warning(
            "Missing URLs for given sources, skip...",
            offer_source=offer_sources,
            gtin=gtin,
        )
        return [], []

    all_searches = []
    for product_url in product_urls:
        coro = fetch_offers_from_google_product_id(product_url, gtin, sku, country)  # type: ignore
        all_searches.append(coro)

    offer_results = await asyncio.gather(*all_searches)

    all_offers = []
    exceptions = []
    for offers, country, exception in offer_results:
        all_offers.extend(offers)
        if exception is not None:
            exceptions.append((exception, country))

    return all_offers, exceptions


async def scrape(
    gtin: Optional[str],
    sku: Optional[str],
    cached_offers_urls: Optional[dict],
    countries=["SE"],
) -> Tuple[List[helpers.offers.Offer], List[Tuple[Exception, str]]]:
    results_per_country = await asyncio.gather(
        *[
            scrape_one_country(gtin, sku, cached_offers_urls, country)
            for country in countries
        ]
    )

    return [o for r in results_per_country for o in r[0]], [
        e for r in results_per_country for e in r[1]
    ]


def find_product_id(gtin: str, country: str = "se") -> Optional[str]:
    """Find product_id of a google shopping product based on GTIN."""

    url = f"https://www.google.com/search?q={gtin}&gl={country}&hl=en&tbm=shop"
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
    logger.info(
        "found google shopping product",
        gtin=gtin,
        product_id=product_id,
        url=f"https://www.google.com/shopping/product/{product_id}",
    )

    return product_id


def __build_product_url(cached_product_url: str, country: str):
    """
    We have 2 types of storing the Google Shopping products in the cache.

    1. One relies on the google product id, and then we store just the id and recompose the URL.
    Ex: 13206784448519231477

    2. Sometimes offer are displayed in one-offer product pages, that do not have an id assigned. Then we need to cache
    the full URL.
    Ex: epd:6307150723913084381,eto:6307150723913084381_0,pid:6307150723913084381

    """
    return (
        f"https://www.google.com/shopping/product/{cached_product_url}/offers?hl=en&gl={country}"
        if cached_product_url.isdigit()
        else f"https://www.google.com/shopping/product/1?hl=en&gl={country}&prds={cached_product_url}"
    )


async def fetch_offers_from_google_product_id(
    cached_product_url: str,
    gtin: Optional[str],
    sku: Optional[str],
    country: str,
) -> Tuple[list[Offer], str, Optional[Exception]]:
    try:
        proxy_country = "DE"  # always use DE proxy
        url = __build_product_url(cached_product_url, country)

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
                gtin if gtin else sku,
                country,
            )
            raise ex
    except Exception as ex:
        logger.error(
            "error when fetching offers",
            google_pid=cached_product_url,
            country=country,
            error=str(ex),
        )
        return [], country, ex
