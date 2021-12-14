import json
import base64
from typing import Literal, Optional, TypedDict

import structlog

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.scrapers import idealo
from sherlock_offer_scrapers.scrapers.prisjakt import prisjakt


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


def _sherlock_scrape(offer_source: OfferSourceType, payload: Payload) -> None:
    logger.info("offer-scraping-started", offer_source=offer_source, payload=payload)

    gtin = payload["gtin"]
    cached_offer_urls = payload.get("offer_urls")
    offers = []
    try:
        if offer_source == "prisjakt":
            # offer_urls = prisjakt.retrieve_urls(offer_urls)
            # _publish_new_offer_urls(gtin, offer_urls)
            # offers = prisjakt.scrape(gtin, cached_offer_urls)
            pass
        elif offer_source == "idealo":
            # offer_urls = idealo.retrieve_urls(payload, gtin)
            # _publish_new_offer_urls(gtin, offer_urls)
            offers = idealo.scrape(gtin, cached_offer_urls)
    except Exception as ex:
        raise ex
    finally:
        helpers.offers.publish_offers(payload, offers, offer_source)  # type: ignore
