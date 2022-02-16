import random
import time
from typing import Optional

from . import common


def query_products(gtin: str, country: str) -> Optional[str]:
    """Find the product's url_path on pricerunner.

    Example return: /pl/110-5286908/Datormoess/Logitech-MX-Anywhere-3-priser
    """
    # Mimic the behavior of a real human by
    # 1st fetch the home page, then wait a few seconds,
    # then fetch the search API. All within a session.
    session = common.create_session(country)

    url = common.BASE_URL[country]
    common._make_request(url, session)

    # wait a little bit, normal human don't type that fast
    common.pause_execution_random(min_sec=2, max_sec=5)

    # fetch the search API
    url = _get_query_url(gtin, country)
    res = common._make_request(url, session)
    # Check if the target resource is no longer available
    if res.status_code == 410:
        return None
    query_result = common._make_request(url, session).json()
    return _parse_query_results(query_result)


def _get_query_url(gtin: str, country: str):
    common.BASE_URL[country]
    return f"{common.BASE_URL[country]}/public/search/v3/{country.lower()}?q={gtin}"


def _parse_query_results(result) -> Optional[str]:
    products = result["products"]
    # Issue to know with Pricerunner, when you search for something that they don't
    # index they will just return very low matching search results
    if len(products) == 0:
        return None
    product = products[0]
    return product["url"]
