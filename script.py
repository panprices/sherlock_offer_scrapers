import json
import os.path
import re
import time
import urllib.parse
from typing import Optional

import structlog
import typer
from bs4 import BeautifulSoup

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.scrapers.google_shopping import user_agents
import csv

app = typer.Typer()

logger = structlog.get_logger()

id_to_gtin_cache = {}
gtin_to_id_cache = {}
retailer_gtin_success_count = {}
searches_cache = set()
products_without_gtin = set()


INTER_REQUEST_DELAY = 90

proxy_country = None

GOOGLE_SHOPPING_COOKIES = {
    "NID": "511=i3rfMEZFKEb_UtdoCUGW0DwOkG4s1dAqCELqh3BeG7w9yWQnmTVesrUuvelzgxezPSyfMetkjVBxaXlMmd0CNEcMh8J2oCQYTSyJ5T"
    "9YVYyQP2eif2vpVQDwEBg_dSo-iPVMS-vajMeNghBfAkSwyWPPFWGF1lYtptf7ioIjKrKikWURqYTPCXL6qkVk1x87eDGQl0hu9LXeFbSh7"
    "tWLTFgyrEoGAvC1GMs6O1UNRjmeu8VTofLnJk4_Iy6fAOrimwncF0kVCO81_nL_zzAgLGuPxQyRw0fwGqPzAv8TMhJSbkW682w4kDtJ-Otm"
    "F8eCGORgUN2H4YBKXtadY_qj8Islgxc4m54ugnwY_9vQn_NFpsUjFVr1XGh-7Bkr92C1YRwFUR9ntaX9ajGxcQ1MuvODlXKMVzQwNZv6miL"
    "CjiCwuqEvneqazsfZWLeZI5X6SIpRuG0SUxIg0PNv_sdZxuSLMpq5ehmAiAtMRHnn",
    "SOCS": "CAISNQgCEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMxMDI3LjA5X3AwGgJlbiACGgYIgPCQqgY",
}


def read_id_to_gtin_cache():
    if os.path.exists("output/id_to_gtin_cache.csv"):
        with open("output/id_to_gtin_cache.csv", "r") as f:
            csv_reader = csv.reader(f)
            next(csv_reader)
            for row in csv_reader:
                id_to_gtin_cache[row[0]] = row[1]
                gtin_to_id_cache[row[1]] = row[0]


def find_gtin_from_retailer_url(url: str) -> Optional[str]:
    html = helpers.requests.get(url).text

    gtin = extract_gtin_from_html_schemaorg(html)
    if gtin is not None:
        print(f"Found gtin: {gtin} in the html of {url} using schema.org")
        return gtin

    gtin = extract_gtin_from_html_regex(html)
    if gtin is not None:
        print(f"Found gtin: {gtin} in the html of {url} using regex")
        return gtin

    if gtin is None:
        gtin = extract_gtin_from_meta_property(html)
        if gtin is not None:
            print(f"Found gtin: {gtin} in the html of {url} using meta property")
            return gtin

    return None


def extract_gtin_from_meta_property(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, features="html.parser")
    meta_tags = soup.select("meta[itemprop='gtin13']")

    if len(meta_tags) == 0:
        return None

    gtin = meta_tags[0]["content"]
    return _normalise_gtin14(gtin)


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

        return _normalise_gtin14(gtin)

    return None


def _normalise_gtin14(gtin: str) -> str:
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

    gtin = _normalise_gtin14(gtin)
    return gtin


def search_for_gtin_within_offers(product_id: str, country: str) -> Optional[str]:
    # insert some delay betwwen requests to google shopping
    time.sleep(INTER_REQUEST_DELAY)

    url = f"https://www.google.com/shopping/product/{product_id}/offers?hl=en&gl={country}"

    resp = helpers.requests.get(
        url,
        headers={"User-Agent": user_agents.choose_random()},
        cookies=GOOGLE_SHOPPING_COOKIES,
        proxy_country=proxy_country,
    )
    if resp.status_code == 429:
        raise Exception("Too many requests")

    html = resp.text
    soup = BeautifulSoup(html, features="html.parser")

    all_offers = soup.select("tr.sh-osd__offer-row")
    offers_dict = {}
    for offer in all_offers:
        offer_retailer = offer.select_one("a.b5ycib").text.replace(
            "Opens in a new window", ""
        )
        offer_url = offer.select_one("a.b5ycib")["href"]

        offers_dict[offer_retailer] = offer_url

    sorted_offers_tuples = sorted(
        offers_dict.items(),
        key=lambda item: retailer_gtin_success_count.get(item[0], 0),
        reverse=True,
    )

    for offer_retailer, offer_url in sorted_offers_tuples:
        # The actual url is in the offer_url as a query parameter with key q
        offer_url_after_redirect = urllib.parse.parse_qs(
            urllib.parse.urlparse(offer_url).query
        )["q"][0]

        try:
            gtin_from_offer = find_gtin_from_retailer_url(offer_url_after_redirect)
        except Exception as e:
            logger.warning(e)
            gtin_from_offer = None

        if not gtin_from_offer:
            continue

        id_to_gtin_cache[product_id] = gtin_from_offer
        gtin_to_id_cache[gtin_from_offer] = product_id
        retailer_gtin_success_count[offer_retailer] = (
            retailer_gtin_success_count.get(offer_retailer, 0) + 1
        )

        return gtin_from_offer

    products_without_gtin.add(product_id)
    return None


def check_gtin_matches(product_id: str, search_gtin: str, country: str):
    if product_id in id_to_gtin_cache:
        return id_to_gtin_cache[product_id] == search_gtin

    if product_id in products_without_gtin:
        return False

    gtin_from_offer = search_for_gtin_within_offers(product_id, country)

    if gtin_from_offer == search_gtin:
        return True

    return False


def find_product_id(
    name: str, gtin: str, country: str = "se", brand: str = "GUBI"
) -> Optional[str]:
    """
    Find product_id of a google shopping product based on name and GTIN.

    The idea is to go through all the google shopping products that are returned when searching for the name and match
    them based on the GTIN we extract from one of the offers
    """

    if not gtin:
        return None

    if gtin in gtin_to_id_cache:
        return gtin_to_id_cache[gtin]

    main_name = name.split("(")[0].strip()
    full_name = f"{brand} {main_name}" if brand not in main_name else main_name
    search_term = urllib.parse.quote(full_name)

    if search_term in searches_cache:
        return None

    time.sleep(INTER_REQUEST_DELAY)

    url = f"https://www.google.com/search?q={search_term}&gl={country}&hl=en&tbm=shop"
    resp = helpers.requests.get(
        url,
        headers={"User-Agent": user_agents.choose_random()},
        cookies=GOOGLE_SHOPPING_COOKIES,
        proxy_country=proxy_country,
    )
    if resp.status_code == 429:
        raise Exception("Too many requests")

    html = resp.text
    soup = BeautifulSoup(html, features="html.parser")

    all_a_tags = soup.select("a.Lq5OHe")
    # Only consider links to google shopping products. Ignore links directly to seller websites.
    product_a_tags = [a for a in all_a_tags if "/shopping/product" in a["href"]]
    possible_product_ids = [
        a["href"].split("?")[0].split("/")[3]
        for a in product_a_tags
        # /shopping/product/2336121681419728525?q=05400653007411&hl=en&... -> 2336121681419728525
    ][:8]

    visited_product_pages_count = 0
    for possible_product_id in possible_product_ids:
        is_good_offer = check_gtin_matches(possible_product_id, gtin, country)
        visited_product_pages_count += 1

        if is_good_offer:
            logger.info(
                "Visited product pages",
                visited_product_pages_count=visited_product_pages_count,
            )
            return possible_product_id

    logger.info(
        "Visited product pages",
        visited_product_pages_count=visited_product_pages_count,
    )
    return None


@app.command()
def run(products_file: str, default_brand: str = "Muuto"):
    products = []

    # read the gtin and product name from the csv file
    with open(products_file, "r") as f:
        csv_reader = csv.reader(f)
        next(csv_reader)  # skip the header
        for row in csv_reader:
            if len(row) == 3:
                products.append((row[0], row[1], row[2]))
            else:
                products.append((row[0], row[1], default_brand))

    read_id_to_gtin_cache()

    if os.path.exists("output/products_without_gtin.csv"):
        with open("output/products_without_gtin.csv", "r") as f:
            csv_reader = csv.reader(f)
            next(csv_reader)
            for row in csv_reader:
                products_without_gtin.add(row[0])

    for country in ["dk"]:
        # Allow for the same search in different countries
        searches_cache.clear()

        for product in products:
            logger.info(
                "Starting with parameters", product_name=product[1], gtin=product[0]
            )

            product_id = find_product_id(product[1], product[0], country, product[2])

            logger.info("Found product id", id=product_id)

            # Save id_to_gtin_cache to a csv file
            with open("output/id_to_gtin_cache.csv", "w") as f:
                f.write("product_id,gtin\n")
                for product_id, gtin in id_to_gtin_cache.items():
                    f.write(f"{product_id},{gtin}\n")

            # Save the products without a gtin
            with open("output/products_without_gtin.csv", "w") as f:
                f.write("product_id\n")
                for product_id in products_without_gtin:
                    f.write(f"{product_id}\n")


@app.command()
def check_found_count():
    product_file = "gubi_products.csv"
    searched_gtins = []

    with open(product_file, "r") as f:
        csv_reader = csv.reader(f)
        next(csv_reader)
        for row in csv_reader:
            searched_gtins.append(row[0])

    found_set = set()

    if os.path.exists("output/id_to_gtin_cache.csv"):
        with open("output/id_to_gtin_cache.csv", "r") as f:
            csv_reader = csv.reader(f)
            next(csv_reader)
            for row in csv_reader:
                if row[1] in searched_gtins:
                    found_set.add(row[1])

    logger.info(
        "Found count", found_count=len(found_set), total_count=len(searched_gtins)
    )


@app.command()
def revisit_products_without_gtin():
    products_without_gtin_file = "output/products_without_gtin.csv"
    products = []

    # read the gtin and product name from the csv file
    with open(products_without_gtin_file, "r") as f:
        csv_reader = csv.reader(f)
        next(csv_reader)

        for row in csv_reader:
            products.append(row[0])

    read_id_to_gtin_cache()
    for product_id in products:
        logger.info("Starting with parameters", product_id=product_id)

        search_for_gtin_within_offers(product_id, "no")

        # Save id_to_gtin_cache to a csv file
        with open("output/id_to_gtin_cache.csv", "w") as f:
            f.write("product_id,gtin\n")
            for cached_product_id, gtin in id_to_gtin_cache.items():
                f.write(f"{product_id},{gtin}\n")


@app.command()
def analyze_logs():
    logs_file = "logs.txt"

    with open(logs_file, "r") as f:
        logs = f.readlines()

    total_pages_visited = 0
    for log in logs:
        if "visited_product_pages_count" in log:
            pages_count = int(log.split("=")[-1])
            total_pages_visited += pages_count

    logger.info("Total pages visited", total_pages_visited=total_pages_visited)


@app.command()
def extract_gtin_from_page(target_url: str):
    gtin = find_gtin_from_retailer_url(target_url)

    logger.info("Found gtin", gtin=gtin)


if __name__ == "__main__":
    app()
