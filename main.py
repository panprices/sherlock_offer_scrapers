import json
import asyncio
import base64
from typing import Literal, Optional, TypedDict, Any

import structlog

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.scrapers import (
    pricerunner,
    kelkoo,
    idealo,
    google_shopping,
    kuantokusta,
)


helpers.structlog.config_structlog()
logger = structlog.get_logger()


class Payload(TypedDict):
    created_at: int
    product_id: Optional[int]
    gtin: str
    product_token: str
    offer_fetch_complete: bool
    offer_urls: dict[str, str]
    user_country: str
    triggered_by: dict[str, Any]


OfferSourceType = Literal[
    "prisjakt",
    "pricerunner",
    "kelkoo",
    "idealo",
    "geizhals",
    "guenstiger",
    "ebay",
    "ceneo",
    "google_shopping",
    "kuantokusta",
]


def sherlock_prisjakt(event, context):
    """Search for offers on Prisjakt for a product."""
    payload: Payload = json.loads(base64.b64decode(event["data"]))
    _sherlock_scrape("prisjakt", payload)


def sherlock_pricerunner(event, context):
    """Search for offers on Pricerunner for a product."""
    payload: Payload = json.loads(base64.b64decode(event["data"]))
    _sherlock_scrape("pricerunner", payload)


def sherlock_kelkoo(event, context):
    """Search for offers on Kelkoo for a product."""
    payload: Payload = json.loads(base64.b64decode(event["data"]))
    _sherlock_scrape("kelkoo", payload)


def sherlock_idealo(event, context):
    """Search for offers on Idealo for a product."""
    payload: Payload = json.loads(base64.b64decode(event["data"]))
    _sherlock_scrape("idealo", payload)


def sherlock_gs_offers(event, context):
    payload: Payload = json.loads(base64.b64decode(event["data"]))

    # Only trigger for our b2b-flow
    if payload["triggered_by"]["source"] != "b2b_job":
        logger.msg("Skipping search. Google shopping is only enabled for b2b")
        return

    _sherlock_scrape("google_shopping", payload)


def sherlock_kuantokusta(event, context):
    payload: Payload = json.loads(base64.b64decode(event["data"]))
    if (
        "source" not in payload["triggered_by"]
        or payload["triggered_by"]["source"] != "b2b_job"
    ):
        return  # ignore kuanto kusta for non b2b to avoid burning scrapfly credits

    _sherlock_scrape("kuantokusta", payload)


def _sherlock_scrape(offer_source: OfferSourceType, payload: Payload) -> None:
    gtin = payload["gtin"]

    if (
        "source" in payload["triggered_by"]
        and payload["triggered_by"]["source"] == "b2b_job"
        and "requested_sources" in payload["triggered_by"]
        and payload["triggered_by"]["requested_sources"]
        and offer_source not in payload["triggered_by"]["requested_sources"]
    ):
        logger.info(
            "Skipping execution, because the source is not listed in requested list: ",
            payload=payload,
            offer_source=offer_source,
        )
        return

    logger.info(
        "offer-scraping-started",
        offer_source=offer_source,
        payload=payload,
        gtin=gtin,
    )

    cached_offer_urls = payload.get("offer_urls")
    offers = []
    exceptions: list[tuple[Exception, str]] = []

    try:
        if offer_source == "prisjakt":
            pass
        elif offer_source == "pricerunner":
            offers = pricerunner.scrape(gtin, cached_offer_urls)
        elif offer_source == "kelkoo":
            offers = kelkoo.scrape(gtin)
        elif offer_source == "idealo":
            offers = idealo.scrape(gtin, cached_offer_urls)
        elif offer_source == "google_shopping":
            offers, exceptions = asyncio.run(
                google_shopping.scrape(
                    gtin,
                    cached_offer_urls,
                    countries=[
                        "NL",
                        "PL",
                        "BE",
                        "IE",
                        "PT",
                        "CZ",
                        "CH",
                        "GR",
                        "SK",
                        "RO",
                        "HU",
                    ],
                )
            )
        elif offer_source == "kuantokusta":
            offers = kuantokusta.scrape(gtin)
        else:
            raise Exception(f"Offer source {offer_source} not supported.")

        for (ex, country) in exceptions:
            logger.error(
                "error when fetching offers",
                error=ex,
                country=country,
                gtin=gtin,
                offer_source=offer_source,
            )

        if len(exceptions) > 0:
            raise exceptions[0][0]

    except Exception as ex:
        logger.exception("exception", exc_info=ex)
        raise ex
    finally:
        helpers.offers.publish_offers(payload, offers, offer_source)
