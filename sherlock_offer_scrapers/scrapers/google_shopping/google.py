from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

from sherlock_offer_scrapers import helpers
from . import user_agents


def scrape(gtin: str, cached_offers_urls: Optional[dict]) -> list[helpers.offers.Offer]:
    if not cached_offers_urls or "google_shopping_SE" not in cached_offers_urls:
        print("No google shopping url provided")
        return []

    url = cached_offers_urls["google_shopping_SE"]
    offers = fetch_offers_from_url(url)

    return offers


def fetch_offers_from_url(url: str, country="SE") -> list:
    url = url + "/offers?hl=en"

    response = helpers.requests.get(
        url,
        headers={"User-Agent": user_agents.choose_random()},
        proxy_country=country,
    )
    # with open("test.html", "wb") as f:
    #     f.write(response.content)

    soup = BeautifulSoup(response.text, "html.parser")
    offers = _parse_offer(soup)
    return offers


def _parse_offer(soup, country="SE"):
    if _is_cookies_prompt_page(soup):
        raise Exception(f"Cookies consent page encountered.")

    if len(soup.select(".product-not-found")) > 0:
        print("This product does not exist on google_shopping_SE")
        return []

    rows = soup.select("table.dOwBOc tr.sh-osd__offer-row")
    product_name = soup.select(".f0t7kf a")[0].get_text()

    offers = []
    for row in rows:
        price_divs = row.select(".drzWO")
        if len(price_divs) == 0:  # skip rows without prices
            continue
        price_text = price_divs[0].get_text()
        price, currency = _extract_price_and_currency(price_text)

        link_div = row.select("a.b5ycib")[0]
        offer_url = link_div.attrs["href"]
        retailer_name = link_div.contents[0].get_text()

        offers.append(
            {
                "offer_source": f"google_shopping_{country}",
                "offer_url": f"https://www.google.com{offer_url}",
                "retail_prod_name": product_name,
                "retailer_name": retailer_name,
                "country": country,
                "price": price,
                "currency": currency,
            }
        )

    return offers


def _extract_price_and_currency(price_text: str) -> Tuple[int, str]:
    if "kr" in price_text:
        currency = "SEK"
    else:
        raise Exception(f"Cannot parse currency from price_text: {price_text}")

    # Remove spaces, including non-breaking spaces (&nbsp; or \xa0)
    price_text = "".join(price_text.split("\xa0")[:-1])
    price_text = price_text.replace(",", ".")
    # Convert to zero-decimal-price by multipling with 100 and truncate the decimal part:
    price = int(float(price_text) * 100)
    return price, currency


def _is_cookies_prompt_page(soup) -> bool:
    if (
        soup.select_one(
            'form[action="https://consent.google.com/s"] button.VfPpkd-LgbsSe'
        )
        is None
    ):
        return False
    return True
