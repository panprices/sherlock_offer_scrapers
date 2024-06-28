import json
import re
from typing import Optional

from bs4 import BeautifulSoup

from sherlock_offer_scrapers import helpers
from structlog import get_logger

logger = get_logger()


def find_gtin_from_retailer_url(
    url: str, expected_gtin: Optional[str] = None, expected_sku: Optional[str] = None
) -> Optional[str]:
    html = helpers.requests.get(url, timeout=300).text

    gtin = extract_gtin_from_html_schemaorg(html)
    if gtin is not None:
        logger.debug(f"Found gtin: {gtin} in the html of {url} using schema.org")
        return gtin

    gtin = extract_gtin_from_html_regex(html)
    if gtin is not None:
        logger.debug(f"Found gtin: {gtin} in the html of {url} using regex")
        return gtin

    gtin = extract_gtin_from_meta_property(html)
    if gtin is not None:
        logger.debug(f"Found gtin: {gtin} in the html of {url} using meta property")
        return gtin

    if expected_gtin is not None:
        gtin = search_for_gtin_in_page(html, expected_gtin)
        if gtin is not None:
            logger.debug(
                f"Found gtin {gtin} by searching for the expected gtin within the html of {url}"
            )

    if expected_sku is not None:
        sku = search_for_gtin_in_page(html, expected_sku)
        if sku is not None:
            logger.info(
                f"Found sku {sku} by searching for the expected sku within the html of {url}"
            )

    return None


def extract_gtin_from_meta_property(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, features="html.parser")
    meta_tags = soup.select("meta[itemprop='gtin13']")

    if len(meta_tags) == 0:
        return None

    gtin = meta_tags[0]["content"]
    return normalise_gtin14(gtin)


def search_for_gtin_in_page(html: str, gtin: str) -> Optional[str]:
    search_result = html.find(gtin)
    if search_result != -1:
        return gtin

    return None


def extract_gtin_from_html_schemaorg(html: str) -> Optional[str]:
    """Ref: https://schema.org/Product"""

    soup = BeautifulSoup(html, features="html.parser")
    shema_org_scripts = soup.select("script[type='application/ld+json']")

    shema_org_dicts = []
    for script in shema_org_scripts:
        try:
            schema = json.loads(script.get_text())
            if type(schema) is list:
                shema_org_dicts.extend(schema)
            else:
                shema_org_dicts.append(schema)
        except json.decoder.JSONDecodeError:
            pass

    shema_org_products = [
        schema for schema in shema_org_dicts if schema.get("@type") == "Product"
    ]

    for schema in shema_org_products:
        if "gtin" in schema:
            gtin = schema["gtin"]
        elif "gtin12" in schema:
            gtin = schema["gtin12"]
        elif "gtin13" in schema:
            gtin = schema["gtin13"]
        elif "gtin14" in schema:
            gtin = schema["gtin14"]
        else:
            continue

        # Guard against websites putting the wrong number into this field:
        if len(gtin) < 12 or len(gtin) > 14:
            continue

        return normalise_gtin14(gtin)

    return None


def normalise_gtin14(gtin: Optional[str]) -> Optional[str]:
    if not gtin:
        return None
    return gtin.rjust(14, "0")


def extract_gtin_from_html_regex(html: str) -> Optional[str]:
    """Using Regex to find gtin in a html."""

    # Why 1 to 5 characters in between? So that it matches even this case:  "gtin" : "1234..."
    possible_gtins = re.findall("upc.{1,5}\d{12,14}", html)
    possible_gtins.extend(re.findall("ean.{1,5}\d{12,14}", html))
    possible_gtins.extend(re.findall("gtin.{1,5}\d{12,14}", html))

    # Extract the numerial part.
    # For example,  "upc = 123412341234" -> "123412341234"
    possible_gtins = [
        re.search("\d{12,14}", gtin_match_str).group(0)
        for gtin_match_str in possible_gtins
    ]

    if len(possible_gtins) == 0:
        logger.info("No gtin found using regex")
        return None
    if len(set(possible_gtins)) >= 2:
        logger.warning("Multiple gtins found when using regex")
        return None

    gtin = possible_gtins[0]

    # Extract the numerial part.
    # For example,  "upc = 123412341234" -> "123412341234"
    gtin = re.search("\d{12,14}", gtin).group(0)

    gtin = normalise_gtin14(gtin)
    return gtin
