import argparse
import base64
import json

from main import sherlock_idealo

messages = [
    {
        "created_at": 1622804976212,
        "product_id": 11039509,
        "gtin": "00194715600645",
        "offer_fetch_complete": False,
        "offer_urls": {
            "geizhals_DE": "https://geizhals.de/salomon-speedcross-5-magnet-black-phantom-herren-410429-a2377369.html",
            "geizhals_EU": "https://geizhals.eu/salomon-speedcross-5-magnet-black-phantom-herren-410429-a2377369.html",
            "google_shopping_SE": "https://www.google.com/shopping/product/2803031962674793185",
            "prisjakt_FI": "5043459",
            "prisjakt_SE": "5043459",
            "idealo_DE": "https://www.idealo.de/preisvergleich/OffersOfProduct/200654750_-ipad-air-64gb-wifi-4g-blau-2020-apple.html",
            "idealo_UK": "https://www.idealo.co.uk/compare/201386993",
            "idealo_ES": "https://www.idealo.es/precios/201386993",
            "idealo_IT": "https://www.idealo.it/confronta-prezzi/201386993",
            "idealo_FR": "https://www.idealo.fr/prix/201386993",
        },
        "product_token": "gAAAAAAAAAAA8HDc9UvYXDxW-lFum7e-77tDmVhJNlZV31Lf79tU-w6OiF85_L2s7cFP3nHS7WHdhOn6Sll-1nCu1UrM4IWKtQ==",
        "triggered_from_client": True,
        "user_country": "SE",
        "triggered_by": {"source": "client"},
    },
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
]

# Define a mocked context
context = {"event_id": "-1", "timestamp": "11111111"}


def demo_sherlock_idealo():
    for message in messages:
        # Simulate how a message gets received from Pubsub
        data = {"data": base64.b64encode(json.dumps(message).encode())}

        sherlock_idealo(data, context)


if __name__ == "__main__":

    # Instantiate the parser
    parser = argparse.ArgumentParser(
        epilog="A demo script to try out the scrapers.",
    )
    # Define the arguments
    parser.add_argument(
        "scraper",
        choices=["prisjakt", "pricerunner", "idealo"],
        help="run a scraper",
    )

    # Decide on execution
    args = parser.parse_args()
    if args.scraper == "prisjakt":
        pass
    elif args.scraper == "pricerunner":
        pass
    elif args.scraper == "idealo":
        demo_sherlock_idealo()
