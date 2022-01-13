import json
from typing import List, Optional, Tuple, Dict
import concurrent.futures
import structlog
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode
import codecs


from sherlock_offer_scrapers import helpers
from . import errors, user_agents, products


logger = structlog.get_logger()


COUNTRIES = ["DE", "UK", "ES", "IT", "FR", "AT"]

base_urls = {
    "DE": "https://www.idealo.de",
    "UK": "https://www.idealo.co.uk",
    "ES": "https://www.idealo.es",
    "IT": "https://www.idealo.it",
    "FR": "https://www.idealo.fr",
    "AT": "https://idealo.at",
}

base_product_urls = {
    "DE": "https://www.idealo.de/preisvergleich/OffersOfProduct",
    "UK": "https://www.idealo.co.uk/compare",
    "ES": "https://www.idealo.es/precios",
    "IT": "https://www.idealo.it/confronta-prezzi",
    "FR": "https://www.idealo.fr/prix",
    "AT": "https://www.idealo.at/preisvergleich/OffersOfProduct",
}


def scrape(gtin, cached_offer_urls: Optional[dict]) -> list:
    # Check cached urls and search for them if not exist:
    if cached_offer_urls and _has_cached_url(cached_offer_urls):
        idealo_product_urls = _retrive_cached_idealo_urls(cached_offer_urls)
    else:
        idealo_product_urls = _find_product_urls(gtin)
        # Publish new results regardless of it being sucess or not.
        helpers.offers.publish_new_offer_urls(gtin, idealo_product_urls)
        if not idealo_product_urls:
            print(f"No product found for gtin {gtin}")
            return []

    # Scrape offers
    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for product_url in idealo_product_urls.values():
            if not product_url:
                continue
            future = executor.submit(get_offers_from_url, product_url)
            futures.append(future)

    all_offers = []
    for future in futures:
        offers = future.result()
        all_offers.extend(offers)

    return all_offers


def _has_cached_url(offer_urls: Dict[str, str]) -> bool:
    """Has cached url if at least one source is available"""
    for country in COUNTRIES:
        offer_source = f"idealo_{country}"
        if offer_source in offer_urls:
            return True

    return False


def _retrive_cached_idealo_urls(offer_urls: Dict[str, str]) -> dict:
    idealo_product_urls = {}
    for country in COUNTRIES:
        offer_source = f"idealo_{country}"
        product_url = offer_urls.get(offer_source)  # type: ignore
        if product_url is None:
            continue
        if offer_source in offer_urls:
            product_url = offer_urls[offer_source]  # type: ignore
            idealo_product_urls[offer_source] = product_url

    return idealo_product_urls


def _find_product_urls(gtin: str) -> Dict[str, Optional[str]]:
    new_product_urls: Dict[str, Optional[str]] = {
        f"idealo_{country}": None for country in COUNTRIES
    }
    print(f"No cached product url found for gtin {gtin}, searching on PriceAPI...")
    try:
        product_id = products.find_product_id(gtin)
    except Exception as ex:
        logger.warning("Cannot find product_id for product", gtin=gtin, ex=ex)
        return new_product_urls

    if product_id is None:
        logger.warning("Cannot find product_id for product", gtin=gtin)
        return new_product_urls

    print(f"Product with gtin {gtin} has id={product_id} on Idealo.")
    for country in COUNTRIES:
        offer_source = f"idealo_{country}"
        product_url = idealo_product_id_to_url(product_id, country)
        new_product_urls[offer_source] = product_url

    return new_product_urls


def idealo_product_id_to_url(idealo_product_id, country: str) -> str:
    return f"{base_product_urls[country]}/{idealo_product_id}"


def idealo_product_id_to_url_alternative(idealo_product_id, country: str) -> str:
    if country == "DE":
        base_url = "https://www.idealo.de/preisvergleich/Typ"
    elif country == "UK":
        base_url = "https://www.idealo.co.uk/type"
    elif country == "ES":
        base_url = "https://www.idealo.es/tipo"
    elif country == "IT":
        base_url = "https://www.idealo.it/tipo"
    elif country == "FR":
        base_url = "https://www.idealo.fr/type"
    return f"{base_url}/{idealo_product_id}"


def get_offers_from_url(idealo_product_url: str) -> List[dict]:
    """Retrieve the html page of the product and scrape its data."""
    try:
        response = _make_request(idealo_product_url)
    except errors.IdealoExpectedError as ex:
        logger.warning("expected idealo error", ex=ex)
        return []

    content = response.text
    country = _get_country_from_product_url(idealo_product_url)
    offers = _parse_offers(content, country)

    for offer in offers:
        # offer["product_id"] = product_id
        offer["country"] = country
        offer["offer_source"] = f"idealo_{country}"

    return offers


def _get_headers():
    return {
        "User-Agent": user_agents.choose_random(),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "test/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-gb",
    }


def _make_request(url) -> requests.Response:
    response = helpers.requests.get(url, headers=_get_headers(), proxy_country="DE")
    if response.status_code == 200:
        return response

    # Try an alternative url:
    alter_url = _switch_url(url)
    logger.warning(
        "Error when requesting url. Trying an alternative url",
        status_code=response.status_code,
        url=url,
        alter_url=alter_url,
    )
    if not alter_url:  # no alternative found -> request failed:
        if response.status_code == 410:
            raise errors.IdealoExpectedError(
                f"Status code: {response.status_code} when requesting to {alter_url}"
            )
        raise Exception(
            f"Status code: {response.status_code} when requesting to {alter_url}"
        )

    # Request to alt_url:
    response = helpers.requests.get(
        alter_url, headers=_get_headers(), proxy_country="DE"
    )

    if response.status_code == 200:
        return response

    # alt_url also failed:
    if response.status_code == 410:
        raise errors.IdealoExpectedError(
            f"Status code: {response.status_code} when requesting to {alter_url}"
        )
    raise Exception(
        f"Status code: {response.status_code} when requesting to {alter_url}"
    )


def _switch_url(url):
    if "idealo.de" in url:
        id = url.split("OffersOfProduct/")[1]
        country = "DE"
    elif "idealo.co.uk" in url:
        id = url.split("compare/")[1]
        country = "UK"
    elif "idealo.es" in url:
        id = url.split("precios/")[1]
        country = "ES"
    elif "idealo.it" in url:
        id = url.split("prezzi/")[1]
        country = "IT"
    elif "idealo.fr" in url:
        id = url.split("prix/")[1]
        country = "FR"
    else:  # idealo_AT
        return None
    new_url = idealo_product_id_to_url_alternative(id, country)
    return new_url


def _get_country_from_product_url(url: str):
    for country_code, base_url in base_product_urls.items():
        if base_url in url:
            return country_code
    return None


def _is_captcha_page(soup) -> bool:
    return soup.find("div", class_="captcha") is not None


def _parse_offers_results(soup):
    offers = []
    # Iterate over all offers on the first page (max 30)
    total_list = soup.find("ul", class_="productOffers-list")
    if total_list is None:
        return []

    offers = total_list.find_all("li", class_="productOffers-listItem")
    return offers


def _extract_retail_product_name(offer_div) -> str:
    name_tag = offer_div.find("span", class_="productOffers-listItemTitleInner")

    if name_tag.has_attr("title"):
        return name_tag["title"]

    # If we couldn't find the product name in a name tag,
    # then it's dynamically rendered.
    # But we can still get the data from a script tag which contains an encoded
    # text of the the product name.
    script_tag = name_tag.find("script")
    script_content = script_tag.get_text()

    # Converting:
    # idealoApp.getContents('!2?2D@?:4 {F>:I s|r\\{)`d q=24< cz q=24< {)\\`d');
    # -> !2?2D@?:4 {F>:I s|r\\{)`d q=24< cz q=24< {)\\`d
    # -> Panasonic Lumix DMC-LX15 Black 4K Black LX-15
    start = script_content.index("idealoApp.getContents('") + len(
        "idealoApp.getContents('"
    )
    end = script_content.index("');", start)
    encrypted_product_name = script_content[start:end]

    try:
        product_name = _decode_product_name(encrypted_product_name)
    except Exception as ex:
        logger.error(
            "Error when decoding product name",
            ciphertext=encrypted_product_name,
            ex=ex,
        )
        raise ex
    return product_name


def _decode_product_name(encrypted_product_name: str) -> str:
    product_name_html = _decode_rot47(encrypted_product_name)
    # There might be some html codes after decryption, so prune them:
    soup = BeautifulSoup(product_name_html, features="html.parser")
    product_name = soup.get_text()
    return product_name


def _extract_price_and_currency(offer_div) -> Tuple[int, str]:
    price_tag = offer_div.find("a", class_="productOffers-listItemOfferPrice")
    price_text = price_tag.text

    if "£" in price_text:
        price_text = price_text.replace("£", "")
        currency = "GBP"
    if "€" in price_text:
        price_text = price_text.replace("€", "")
        currency = "EUR"

    # Normalize characters such as non-breaking space /xa0:
    price_text = unidecode(price_text)
    price_text = price_text.replace(".", "").replace(",", "").replace(" ", "").strip()
    price = int(price_text)
    return price, currency


def _extract_stock_status(offer_div) -> str:
    # There are at least 7 different situations for gray icon,
    # We select 'Check availability in the shop' as 'unknown'
    unknown_filters = [
        # FR
        "Voir site",  # See website
        "Veuillez vé­ri­fier",  # Please check
        "Se ren­sei­gner auprès",  # Inquire with
        # ES
        "Con­sul­tar",  # Con­sul­tar
        "In­for­ma­ción no dis­po­ni­ble",  # Information not available
        # UK
        "Check",
        # DE
        "Shop er­fra­gen",  # Ask the shop
        # IT
        "Con­trol­la­re di­spo­ni­bi­li­tà",  # Check availability
        "con­tat­ta­re il ri­ven­di­to­re",  # Contact your dealer
    ]
    # Circle-icon has 3 color:
    # gray -    'out'
    # green -   'short','medium'
    # yellow -  'long'
    has_gray = offer_div.find(
        True,
        {"class": "productOffers-listItemOfferDelivery delivery delivery--circle out"},
    )
    if has_gray is None:
        return "in_stock"
    else:
        stock_content = offer_div.find(
            True, {"class": "productOffers-listItemOfferDeliveryStatus"}
        )
        if stock_content is not None:
            for filter in unknown_filters:
                if filter in str(stock_content.text):
                    return "unknown"
        return "out_of_stock"


def _parse_offers(html_content: str, country: str) -> List[dict]:
    soup = BeautifulSoup(html_content, features="html.parser")

    if _is_captcha_page(soup):
        raise Exception("Captcha page encountered.")

    # Iterate over the HTML of the page and grab all the retail offers
    offers_results = _parse_offers_results(soup)

    # Parse the offer DIVs and all other data
    formated_offers = []
    for offer_div in offers_results:
        price_tag = offer_div.find("a", class_="productOffers-listItemOfferPrice")
        offer_link = offer_div.find("a", class_="productOffers-listItemOfferCtaLeadout")
        if price_tag is None or offer_link is None:
            continue

        retail_prod_name = _extract_retail_product_name(offer_div)
        price, currency = _extract_price_and_currency(offer_div)
        stock_status = _extract_stock_status(offer_div)
        
        info_payload = json.loads(price_tag["data-gtm-payload"])
        retailer_name = info_payload["shop_name"]
        if retailer_name is None or retailer_name == "":
            logger.warn(
                "retailer name is empty",
                info_payload=info_payload,
                retailer_name=retailer_name,
                offer_url=base_urls[country] + offer_link["href"],
                retail_prod_name=retail_prod_name,
            )
            continue

        offer = {
            "retail_prod_name": retail_prod_name,
            "retailer_name": retailer_name,
            "price": price,
            "currency": currency,
            "offer_url": base_urls[country] + offer_link["href"],
            "stock_status": stock_status,
        }

        if not None in offer.values():
            formated_offers.append(offer)

    return formated_offers


# --- Helpers
def _decode_rot47(ciphertext: str) -> str:
    """Decrypting method for ROT47 cipher. Idealo used this to dynamically render some of the offers' product name."""
    # Note that ROT47 is reversable(?) cipher,
    # which means rot47(rot47(plaintext)) = plaintext

    original = ""
    text = ciphertext.replace(r"（", r"W").replace(
        r"）",
        r"X",
    )  # replace the weird parentheses
    text = codecs.decode(text, "unicode_escape")  # type:ignore
    for i, ch in enumerate(text):
        ascii_code = ord(ch)
        if ascii_code >= 33 and ascii_code <= 126:
            original += chr(33 + ((ascii_code + 14) % 94))
        else:
            original += ch

    return original
