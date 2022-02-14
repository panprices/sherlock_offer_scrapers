import random
import time

from . import common


def query_products(gtin: str, country: str):
    # Mimic the behavior of a real human by
    # 1st fetch the home page, then wait a few seconds,
    # then fetch the search API.

    url = common.BASE_URL[country]
    common._make_request(url, session)

    # wait a little bit, normal human don't type that fast
    _pause_execution_random(min_sec=2, max_sec=5)

    # fetch the search API
    url = _get_query_url(gtin, country)
    res = common._make_request(url, session)
    # Check if the target resource is no longer available
    if res.status_code == 410:
        return None
    query_result = common._make_request(url, session).json()
    return _parse_query_results(query_result)


def _get_query_url(name_or_gtin, country):
    tld = _tlds[country]
    origin = _get_origin(tld)
    query = urllib.parse.quote(name_or_gtin)
    # Add the last shit to look like the client
    return f"{origin}/public/search/v2/{country.lower()}?q={query}"


def _parse_query_results(result):
    products = result["products"]
    score = 1
    # Issue to know with Pricerunner, when you search for something that they don't
    # index they will just return very low matching search results
    if len(products) == 0:
        return {"name": None, "score": None, "url": None}
    product = products[0]
    return {"name": product["name"], "score": score, "url": product["url"]}


def _pause_execution_random(min_sec=1, max_sec=300):
    rand_duration = random.randint(min_sec, max_sec)
    print("Pause for " + str(rand_duration) + "s")
    time.sleep(rand_duration)
