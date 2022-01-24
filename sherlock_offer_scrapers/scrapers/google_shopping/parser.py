from typing import Tuple

import price_parser
import structlog

from sherlock_offer_scrapers.helpers.offers import Offer

logger = structlog.get_logger()


def parser_offer_page(soup, country) -> list[Offer]:
    """Extract offers from offer page."""
    if _is_cookies_prompt_page(soup):
        raise Exception(f"Cookies consent page encountered.")

    if len(soup.select(".product-not-found")) > 0:
        print("This product does not exist on google_shopping_SE")
        return []

    rows = soup.select("table.dOwBOc tr.sh-osd__offer-row")
    product_name = soup.select(".f0t7kf a")[0].get_text()

    offers: list[Offer] = []
    for row in rows:
        price_divs = row.select(".drzWO")
        if len(price_divs) == 0:  # skip rows without prices
            continue
        price_text = price_divs[0].get_text()
        price, currency = _extract_price_and_currency(price_text, country)

        link_div = row.select("a.b5ycib")[0]
        offer_url = link_div.attrs["href"]
        retailer_name = link_div.contents[0].get_text()

        offer: Offer = {
            "offer_source": f"google_shopping_{country}",
            "offer_url": f"https://www.google.com{offer_url}",
            "retail_prod_name": product_name,
            "retailer_name": retailer_name,
            "country": country,
            "price": price,
            "currency": currency,
            "stock_status": "in_stock",
        }
        offers.append(offer)

    return offers


def _is_cookies_prompt_page(soup) -> bool:
    if (
        soup.select_one(
            'form[action="https://consent.google.com/s"] button.VfPpkd-LgbsSe'
        )
        is None
    ):
        return False
    return True


# def _extract_price_and_currency(price_text: str) -> Tuple[int, str]:
#     print(price_text)
#     if "kr" in price_text:
#         currency = "SEK"
#         # Remove spaces, including non-breaking spaces (&nbsp; or \xa0)
#         price_text = "".join(price_text.split("\xa0")[:-1])
#         price_text = price_text.replace(",", ".")
#     elif "€" in price_text:
#         currency = "€"
#     else:
#         raise Exception(f"Cannot parse currency from price_text: {price_text}")

#     # Convert to zero-decimal-price by multipling with 100 and truncate the decimal part:
#     price = int(float(price_text) * 100)
#     return price, currency


def _extract_price_and_currency(price_text: str, country: str) -> Tuple[int, str]:
    price_text_normalized = price_text.replace("'", "").replace("’", "")

    price_obj = price_parser.parse_price(price_text_normalized)
    if not price_obj.amount or not price_obj.currency:
        raise Exception(f"Error when parsing price: {price_text_normalized}")

    amount, currency = round(price_obj.amount * 100), price_obj.currency
    # Convert currency symbols to ISO 4217 currency code:
    if price_obj.currency == "kr":
        if country == "SE":
            currency = "SEK"
        if country == "NO":
            currency = "NOK"
        if country == "DK":
            currency = "DKK"
    elif price_obj.currency == "€":
        currency = "EUR"
    elif price_obj.currency == "£":
        currency = "GBP"
    elif len(currency) == 3:
        currency = price_obj.currency  # already in ISO format, do nothing
    else:
        raise Exception(f"Cannot convert currency: {currency}")

    logger.msg(
        "parsing price and currency",
        input_price_text=price_text,
        input_price_text_normalized=price_text_normalized,
        input_country=country,
        output_amount=amount,
        output_currency=currency,
    )

    return amount, currency
