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


OfferSourceType = Literal["idealo", "prisjakt", "pricerunner", "kelkoo", ""]


class Offer(TypedDict):
    # TODO: Complete this
    price: int


# class PublishMessage(Payload):
#     offer_source: OfferSourceType
#     offers: list[Offer]


def sherlock_prisjakt(event, context):
    """Search for offers on Prisjakt for a product."""
    payload: Payload = json.loads(base64.b64decode(event["data"]))
    _sherlock_scrape("prisjakt", payload)


def sherlock_idealo(event, context):
    """Search for offers on Idealo for a product."""
    payload: Payload = json.loads(base64.b64decode(event["data"]))
    _sherlock_scrape("idealo", payload)


def _sherlock_scrape(offer_source: OfferSourceType, payload: Payload) -> None:
    logger.info("offer scraping started", offer_source=offer_source, payload=payload)

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
        helpers.offers.publish_offers(payload, offers, offer_source)


# def _sherlock_idealo(payload: Payload, logger: Logger) -> List[Offer]:
#     gtin = payload.get("gtin")
#     offer_urls = payload.get("offer_urls")

#     if idealo._has_cached_url(offer_urls):
#         idealo_product_urls = idealo._retrive_cached_idealo_urls(offer_urls)
#     else:
#         if gtin is None:
#             logger.product_not_found(gtin)
#             return []

#         idealo_product_urls = idealo._find_product_urls(gtin)
#         if not idealo_product_urls:
#             logger.product_not_found(gtin)
#             return []

#         idealo_product_urls = idealo._find_product_urls(gtin)
#         _publish_new_urls(gtin, idealo_product_urls, logger)

#     if idealo_product_urls:
#         logger.products_found(idealo_product_urls)
#     else:
#         logger.product_not_found(gtin)
#         return []

#     # Scrape offers
#     futures = []
#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         for product_url in idealo_product_urls.values():
#             future = executor.submit(
#                 idealo.get_offers_from_url, product_url, product_id
#             )
#             futures.append(future)

#     all_offers = []
#     for future in futures:
#         try:
#             offers = future.result()
#             all_offers.extend(offers)
#         except Exception as ex:
#             logging.exception(ex)

#     return all_offers

#     # Scrape offers
#     for offer_source, product_url in idealo_product_urls.items():
#         logging.info(f"Scraping offers on {product_url} for {gtin}...")

#         try:
#             offers = idealo.get_offers_from_url(product_url, product_id)
#             logger.offers_found(offers, product_url)


#                 logging.info(
#                     "Published a live_search_message: "
#                     + json.dumps(live_search_message)
#                 )
#         # Only log exception if scraping from one Idealo site doesn't work
#         # so that we would still try to scrape other sites.
#         except Exception as ex:
#             logging.error(ex)
