import os
import json
import base64
from typing import Literal, Optional, TypedDict

import structlog

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.scrapers import idealo, google_shopping


helpers.logging.config_structlog()
logger = structlog.get_logger()


class Payload(TypedDict):
    created_at: int
    product_id: Optional[int]
    gtin: str
    product_token: str
    offer_fetch_complete: bool
    offer_urls: dict[str, str]
    user_country: str


OfferSourceType = Literal[
    "prisjakt",
    "pricerunner",
    "kelkoo",
    "idealo",
    "geizhals",
    "guenstiger",
    "ebay",
    "ceneo",
]


def sherlock_prisjakt(event, context):
    """Search for offers on Prisjakt for a product."""
    payload: Payload = json.loads(base64.b64decode(event["data"]))
    _sherlock_scrape("prisjakt", payload)


def sherlock_idealo(event, context):
    """Search for offers on Idealo for a product."""
    payload: Payload = json.loads(base64.b64decode(event["data"]))
    _sherlock_scrape("idealo", payload)


def sherlock_gs_offers(event, context):
    payload: Payload = json.loads(base64.b64decode(event["data"]))

    # if (
    #     os.getenv("PANPRICES_ENVIRONMENT") != "local"
    #     and payload["triggered_by"]["source"] != "b2b_job"
    # ):
    #     print("Not b2b offer search, do not scrape on googleshopping.")
    #     return

    if os.getenv("PANPRICES_ENVIRONMENT") != "local":
        print("Google shopping not enabled yet.")
        return

    _sherlock_scrape("google_shopping", payload)


def _sherlock_scrape(offer_source: OfferSourceType, payload: Payload) -> None:
    logger.info("offer-scraping-started", offer_source=offer_source, payload=payload)

    gtin = payload["gtin"]
    cached_offer_urls = payload.get("offer_urls")
    offers = []

    try:
        if offer_source == "prisjakt":
            pass
        elif offer_source == "idealo":
            offers = idealo.scrape(gtin, cached_offer_urls)
        elif offer_source == "google_shopping":
            offers = google_shopping.scrape(
                gtin, cached_offer_urls, countries=["NL", "PL"]
            )
        else:
            raise Exception(f"Offer source {offer_source} not supported.")

    except Exception as ex:
        raise ex
    finally:
        helpers.offers.publish_offers(payload, offers, offer_source)
