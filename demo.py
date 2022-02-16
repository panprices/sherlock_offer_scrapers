import argparse
import base64
import json
import structlog

from main import (
    sherlock_pricerunner,
    sherlock_idealo,
    sherlock_gs_offers,
    sherlock_kelkoo,
)


# Define a mocked context
context = {"event_id": "-1", "timestamp": "11111111"}

logger = structlog.get_logger()


def demo_sherlock_pricerunner():
    message = {
        "created_at": 1622804976212,
        "product_id": 11031881,
        "gtin": "05099206092938",
        "offer_fetch_complete": False,
        "offer_urls": {
            "pricerunner_SE": "/pl/110-5286908/Datormoess/Logitech-MX-Anywhere-3-priser",
        },
        "product_token": "test_gAAAAAAAAAAAsMFK1hehjtyl8OSy9z19N9wvdLUdZdZlh0BWDUgGGc08fkgYGqeXaQn1JegqyzvYRJKhMGix6cIKlNUjHqI2sQ==",
        "triggered_from_client": True,
        "user_country": "SE",
        "triggered_by": {"source": "client"},
    }

    event = {"data": base64.b64encode(json.dumps(message).encode())}
    sherlock_pricerunner(event, {})


def demo_sherlock_idealo():
    messages = [
        # {
        #     "created_at": 1622804976212,
        #     "product_id": 11039509,
        #     "gtin": "00194715600645",
        #     "offer_fetch_complete": False,
        #     "offer_urls": {
        #         "idealo_DE": "https://www.idealo.de/preisvergleich/OffersOfProduct/201386993",
        #         "idealo_UK": "https://www.idealo.co.uk/compare/201386993",
        #         "idealo_ES": "https://www.idealo.es/precios/201386993",
        #         "idealo_IT": "https://www.idealo.it/confronta-prezzi/201386993",
        #         "idealo_FR": "https://www.idealo.fr/prix/201386993",
        #         "idealo_AT": "https://www.idealo.at/preisvergleich/OffersOfProduct/201386993",
        #     },
        #     "product_token": "gAAAAAAAAAAA8HDc9UvYXDxW-lFum7e-77tDmVhJNlZV31Lf79tU-w6OiF85_L2s7cFP3nHS7WHdhOn6Sll-1nCu1UrM4IWKtQ==",
        #     "triggered_from_client": True,
        #     "user_country": "SE",
        #     "triggered_by": {"source": "client"},
        # },
        # {
        #     "created_at": 1622804931119,
        #     "product_id": 10114356,
        #     "gtin": "00629162136053",
        #     "offer_fetch_complete": False,
        #     "offer_urls": {
        #         "google_shopping_SE": "https://www.google.com/shopping/product/18160921550937040099",
        #         "prisjakt_FI": "5773034",
        #         "prisjakt_SE": "5773034",
        #     },
        #     "product_token": "gAAAAABghatiT4kT7NiArKTb2s6Ba-81y1NraqMQKDKlxUQvOghsMB5baWdFjVTGSdsmM3BvSrbKCpI-RTaz2Lvpi7cvx2vLvw==",
        #     "triggered_from_client": True,
        #     "user_country": "SE",
        #     "triggered_by": {"source": "client"},
        # },
        {  # Product with description
            "created_at": 1622804976212,
            "product_id": 9978653,
            "gtin": "00889842651393",
            "offer_fetch_complete": False,
            "offer_urls": {
                "idealo_DE": "https://www.idealo.de/preisvergleich/OffersOfProduct/200637075",
                "idealo_UK": "https://www.idealo.co.uk/compare/200637075",
                "idealo_ES": "https://www.idealo.es/precios/200637075",
                "idealo_IT": "https://www.idealo.it/confronta-prezzi/200637075",
                "idealo_FR": "https://www.idealo.fr/prix/200637075",
                "idealo_AT": "https://www.idealo.at/preisvergleich/OffersOfProduct/200637075",
            },
            "product_token": "gAAAAABfc-DzBi5GrOEIprSqxyNjV-Ayx_MZeTg8wXnVNqTVog2J6FIOQk9_kY3kYAh4uGqEMTJVWx7o_hgDGShoH-gQ7EZ1Qg==",
            "triggered_from_client": True,
            "user_country": "SE",
            "triggered_by": {"source": "client"},
        },
    ]
    for message in messages:
        # Simulate how a message gets received from Pubsub
        data = {"data": base64.b64encode(json.dumps(message).encode())}

        sherlock_idealo(data, context)


def demo_sherlock_kelkoo():
    message = {
        "created_at": 1622804976212,
        "product_id": 11031881,
        "gtin": "04242002542768",
        "offer_fetch_complete": False,
        "offer_urls": {
            "google_shopping": "16065837288008218653",
        },
        "product_token": "test_gAAAAAAAAAAAsMFK1hehjtyl8OSy9z19N9wvdLUdZdZlh0BWDUgGGc08fkgYGqeXaQn1JegqyzvYRJKhMGix6cIKlNUjHqI2sQ==",
        "triggered_from_client": True,
        "user_country": "SE",
        "triggered_by": {"source": "client"},
    }

    event = {"data": base64.b64encode(json.dumps(message).encode())}

    sherlock_kelkoo(event, {})


def demo_sherlock_gs_offers():
    message = {
        "created_at": 1622804976212,
        "product_id": 11031881,
        "gtin": "00711719827399",
        "offer_fetch_complete": False,
        "offer_urls": {
            "google_shopping": "5346533728443139525",
        },
        "product_token": "test_gAAAAAAAAAAAsMFK1hehjtyl8OSy9z19N9wvdLUdZdZlh0BWDUgGGc08fkgYGqeXaQn1JegqyzvYRJKhMGix6cIKlNUjHqI2sQ==",
        "triggered_from_client": True,
        "user_country": "SE",
        "triggered_by": {
            "source": "b2b_job",
            "job_id": "UupuDUjLXoHbAKjHsrtH",
            "task_id": "hyAnhCIoQQyt0qWl5W3S",
            "offer_search_id": "JGUl2cEn2pU77PevQBYx",
        },
    }

    event = {"data": base64.b64encode(json.dumps(message).encode())}

    sherlock_gs_offers(event, {})


if __name__ == "__main__":
    # Instantiate the parser
    parser = argparse.ArgumentParser(
        epilog="A demo script to try out the scrapers.",
    )
    # Define the arguments
    parser.add_argument(
        "scraper",
        choices=["prisjakt", "pricerunner", "kelkoo", "idealo", "google_shopping"],
        help="run a scraper",
    )

    # Decide on execution
    args = parser.parse_args()
    if args.scraper == "prisjakt":
        pass
    elif args.scraper == "pricerunner":
        demo_sherlock_pricerunner()
    elif args.scraper == "kelkoo":
        demo_sherlock_kelkoo()
    elif args.scraper == "idealo":
        demo_sherlock_idealo()
    elif args.scraper == "google_shopping":
        demo_sherlock_gs_offers()
