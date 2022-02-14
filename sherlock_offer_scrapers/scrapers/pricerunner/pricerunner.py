from typing import Optional
import time
import random

import requests

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.helpers.offers import Offer
from .search import query_products


ENABLED_COUNTRIES = [
    "SE",
    "DK",
]


def scrape(gtin, cached_offer_urls: Optional[dict]) -> list[Offer]:
    ip_addr = requests.get("https://api.ipify.org/").text

    all_offers: list[Offer] = []
    for country in ENABLED_COUNTRIES:
        product = query_products(gtin, country)

        all_offers.extend(offers)

    return all_offers


def get_offers(product, id, session, country="SE", wait=True):
    # Logic: Fetch the offers page (html), then wait a bit and fetch the data API
    # using the same session to disguise as a real user.

    url = _get_offers_html_url(product["url"], country)
    _make_request(url, session)

    # wait a little bit
    if wait:
        _pause_execution_random(min_sec=2, max_sec=5)

    # # fetch the offer data
    # url = _get_offers_url(product["url"], country)
    # response = _make_request(url, session)
    # # when the link is incorrect, pricerunner api actually return 204, not 404
    # if response.status_code == 204 or response.status_code >= 400:
    #     print(f"status code: {response.status_code} when requesting to {url}")
    #     return None, True
    # else:
    #     return _parse_offers_results(response.json(), product, id, country), False


def _make_request(url, session, retries=0):
    # max_retries is not defined",
    max_retries = 1
    try:
        response = session.get(url)
    except requests.exceptions.Timeout:
        print("Got a timeout on url " + url)
        if retries >= max_retries:
            raise e
        retries += 1
        return _make_request(url, session, retries)
    except requests.exceptions.RequestException as e:
        print(
            "There was an error with getting product offers for "
            + url
            + " on Pricerunner: "
            + str(e)
        )
        raise e
    # Check if we wasn't able to acces the content because Pricerunner blocker our IP
    if response.status_code == 403:
        # click the "I am not the robot button"
        session.post("https://www.pricerunner.se/public/access/v1", data={})
        # in the button implementation, they wait for 0.25 second, so do we
        pause_execution(0.25)
        # fetch the data api again
        try:
            response = session.get(url)
        except requests.exceptions.Timeout:
            print("Got a timeout on url " + url)
            if retries >= max_retries:
                raise e
            retries += 1
            return _make_request(url, session, retries)
        except requests.exceptions.RequestException as e:
            print(
                "There was an error with getting product offers for "
                + url
                + " on Pricerunner: "
                + str(e)
            )
            raise e
        # check 403 again
        if response.status_code == 403:
            print("They still block us")
            raise Exception(
                "Status code was 403 Forbidden. Pricerunner has probably blocked our IP adress."
            )
        else:
            print("I am not a robot")
    # Check if we wasn't able to acces the content because Pricerunner blocker our IP
    if response.status_code == 410:
        print("<Response 410>: the target resource is no longer available")

    return response


def _get_offers_html_url(url, country):
    return f"https://www.pricerunner.{country.lower()}/{url}"


# HELPERS
