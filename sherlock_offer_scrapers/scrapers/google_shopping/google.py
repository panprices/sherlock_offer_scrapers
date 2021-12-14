from datetime import datetime, timezone
from os import EX_CANTCREAT
from typing import Optional

import requests
from bs4 import BeautifulSoup

from sherlock_offer_scrapers import helpers
from . import user_agents


def scrape(gtin: str, cached_offers_urls: Optional[dict]) -> list:
    if "google_shopping_SE" not in cached_offers_urls:
        print("No google shopping url provided")
        return []

    url = cached_offers_urls["google_shopping_SE"]
    offers = fetch_offers_from_url(url)
    print(f"Found {len(offers)} offers.")

    return offers


def fetch_offers_from_url(url: str) -> list:
    url = url + "/offers?hl=en"

    response = helpers.requests.get(
        url,
        headers={"User-Agent": user_agents.choose_random()},
        proxy_country="SE",
    )
    # with open("test.html", "wb") as f:
    #     f.write(response.content)

    soup = BeautifulSoup(response.text, "html.parser")
    offers = _parse_offer(soup)
    return offers


def _parse_offer(soup):
    if len(soup.select(".product-not-found")) > 0:
        print("This product is not existed on google_shopping_SE")
        return []

    rows = soup.select("table.dOwBOc tr.sh-osd__offer-row")
    product_name = soup.select(".f0t7kf a")[0].getText()

    offers = []
    for row in rows:
        # get the url, make the request so google redirect to the retailer url
        link_node = row.select("a.b5ycib")[0]
        offer_url = link_node.attrs["href"]
        retailer_name = link_node.get_text()

        price = row.select(".drzWO")[0].get_text()
        # Remove spaces, including non-breaking spaces (&nbsp; or \xa0)
        price = "".join(price.split("\xa0")[:-1])
        price = price.replace(",", ".")
        price = str(
            int(float(price) * 100)
        )  # multiply by 100 and truncate the decimal part, basically keep 2 digits after the decimal

        offers.append(
            {
                "offer_source": "google_shopping_SE",
                "retailer_name": retailer_name,
                "offer_url": f"https://www.google.com{offer_url}",
                "country": "SE",
                "retail_prod_name": product_name,
                "price": price,
                "currency": "SEK",
                "requested_at": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "match_score": None,
            }
        )

    return offers
