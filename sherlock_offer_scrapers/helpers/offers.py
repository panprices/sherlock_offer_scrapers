from typing import Any, Literal, Optional, List, TypedDict
import json

import structlog
from google.cloud import pubsub_v1

logger = structlog.get_logger()


class Offer(TypedDict):
    offer_source: str
    offer_url: str

    retail_prod_name: str
    retailer_name: str
    country: str

    price: int
    currency: str
    stock_status: Literal["in_stock", "out_of_stock", "unknown"]

    description: Optional[str]
    brand: Optional[str]
    category: Optional[str]
    images: List[Any]


class Publisher:
    def __init__(self, project_id, topic):
        self.client = pubsub_v1.PublisherClient()
        self.topic_path = self.client.topic_path(project_id, topic)

    def publish_message(self, message: dict):
        # Data must be a bytestring
        data = json.dumps(message).encode("utf-8")
        future = self.client.publish(self.topic_path, data=data)
        message_id = future.result()
        return message_id

    def publish_messages(self, messages: List[dict]) -> List[str]:
        message_ids = []
        for message in messages:
            # Data must be a bytestring
            data = json.dumps(message).encode("utf-8")
            future = self.client.publish(self.topic_path, data=data)
            message_id = future.result()
            message_ids.append(message_id)
        return message_ids


def publish_new_offer_urls(gtin: str, offer_urls: dict[str, Optional[str]]):
    """Publish new urls to store them in the database.

    Example of product_urls: {
        "idealo_DE": "https://www.idealo.de/preisvergleich/OffersOfProduct/200557215",
        "idealo_UK": "https://www.idealo.co.uk/compare/200557215",
        ...
    }
    """
    cache_link_publisher = Publisher("panprices", "new_gtin_link")
    cache_link_publisher.publish_messages([{"gtin": gtin, "links": offer_urls}])

    logger.info(
        "new-offer-urls-published",
        offer_urls=offer_urls,
    )


def publish_offers(payload, offers: list[Offer], offer_source: str):
    live_search_publisher = Publisher("panprices", "live_search_offers")

    live_search_message = payload
    live_search_message["offer_source"] = offer_source
    live_search_message["offers"] = offers

    live_search_publisher.publish_message(live_search_message)

    logger.info(
        "live-search-offers-published",
        nb_offers=len(offers),
    )
