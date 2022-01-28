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
        logger.warn("This product does not exist on google_shopping_SE")
        return []

    try:
        product_name, page_variant = _extract_product_name(soup)
    except Exception as ex:
        div_MPhl6c_exist = len(soup.select(".MPhl6c")) > 0
        logger.error(
            "cannot extract product name, new google html page encountered",
            country=country,
            div_MPhl6c_exist=div_MPhl6c_exist,
        )
        raise ex

    if page_variant == 0:
        rows = soup.select("table.dOwBOc tr.sh-osd__offer-row")
    elif page_variant == 1:
        rows = soup.select("div.Nq7DI div.MVQv4e")

    offers: list[Offer] = []
    for row in rows:
        if page_variant == 0:
            price_divs = row.select(".drzWO")
        elif page_variant == 1:
            price_divs = row.select("div.DX0ugf div.xwW5Ce div.DX0ugf span.Lhpu7d")

        if len(price_divs) == 0:  # skip rows without prices
            continue
        price_text = price_divs[0].get_text()
        price, currency = _extract_price_and_currency(price_text, country)

        if page_variant == 0:
            link_anchor = row.select("a.b5ycib")[0]
            offer_url = link_anchor.attrs["href"]
            offer_url = f"https://www.google.com{offer_url}"
        elif page_variant == 1:
            link_anchor = row.select("a.ueI0Ed")[0]
            offer_url = link_anchor.attrs["href"]
        retailer_name = link_anchor.contents[0].get_text()

        offer: Offer = {
            "offer_source": f"google_shopping_{country}",
            "offer_url": offer_url,
            "retail_prod_name": product_name,
            "retailer_name": retailer_name,
            "country": country,
            "price": price,
            "currency": currency,
            "stock_status": "in_stock",
            "metadata": None,
        }
        offers.append(offer)

    return offers


def _extract_product_name(soup) -> Tuple[str, int]:
    page_variant = 0

    product_title = soup.find("div", class_="f0t7kf")
    if product_title is None:
        product_title = soup.find("div", class_="MPhl6c")
        page_variant = 1
    if product_title is None:
        raise Exception("Cannot find product title")

    product_name = product_title.get_text()

    return product_name, page_variant


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
    elif price_obj.currency == "$":
        currency = "USD"
    elif price_obj.currency == "NZ$":
        currency = "NZD"
    elif price_obj.currency == "A$" or price_obj.currency == "AU$":
        currency = "AUD"
    elif price_obj.currency == "MX$" or price_obj.currency == "Mex$":
        currency = "MXN"
    elif price_obj.currency == "₪":
        currency = "ILS"
    elif len(currency) == 3:
        currency = price_obj.currency  # already in ISO format, do nothing
    else:
        logger.error(
            "error when parsing price and currency",
            input_price_text=price_text,
            input_price_text_normalized=price_text_normalized,
            country=country,
            output_amount=amount,
            output_currency=currency,
        )
        raise Exception(f"Cannot convert currency: {currency}")

    logger.msg(
        "parsing price and currency",
        input_price_text=price_text,
        input_price_text_normalized=price_text_normalized,
        country=country,
        output_amount=amount,
        output_currency=currency,
    )

    return amount, currency
