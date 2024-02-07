import asyncio
import csv
import functools
import json
import logging.config
import os.path
import re
import time
import urllib.parse
from typing import Optional, Tuple, Annotated, List

import structlog
import typer
from bs4 import BeautifulSoup
from requests.exceptions import ProxyError
from tqdm import tqdm

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.scrapers.google_shopping import user_agents
from structlog.dev import set_exc_info, ConsoleRenderer
from structlog.processors import (
    StackInfoRenderer,
    TimeStamper,
    add_log_level,
    LogfmtRenderer,
)

app = typer.Typer()

structlog.configure_once(
    processors=[
        add_log_level,
        StackInfoRenderer(),
        set_exc_info,
        TimeStamper(fmt="%Y-%m-%d %H:%M.%S", utc=False),
        LogfmtRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


logger = structlog.get_logger()

id_to_gtin_cache = {}
gtin_to_id_cache = {}
searches_cache = set()
products_without_gtin = set()


INTER_SEARCH_DELAY = 0
INTER_NAVIGATION_DELAY = 0

search_proxy_country = "SE"
product_proxy_country = "SE"


GOOGLE_SHOPPING_COOKIES = {
    "SOCS": "CAESNQgCEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwMTAyLjA1X3AwGgJlbiACGgYIgI3drAY",
    "CONSENT": "PENDING+105",
}


def read_id_to_gtin_cache():
    if os.path.exists("output/id_to_gtin_cache.csv"):
        with open("output/id_to_gtin_cache.csv", "r") as f:
            csv_reader = csv.reader(f)
            next(csv_reader)
            for row in csv_reader:
                id_to_gtin_cache[row[0]] = row[1]
                gtin_to_id_cache[row[1]] = row[0]


def write_output():
    # Save id_to_gtin_cache to a csv file
    with open("output/id_to_gtin_cache.csv", "w") as f:
        f.write("product_id,gtin\n")
        for product_id, gtin in id_to_gtin_cache.items():
            f.write(f"{product_id},{gtin}\n")

    # Save the products without a gtin
    with open("output/products_without_gtin.csv", "w") as f:
        f.write("product_id\n")
        for product_id, country in products_without_gtin:
            f.write(f"{product_id},{country}\n")


def find_gtin_from_retailer_url(
    url: str, expected_gtin: Optional[str] = None
) -> Optional[str]:
    html = helpers.requests.get(url).text

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

    return None


def extract_gtin_from_meta_property(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, features="html.parser")
    meta_tags = soup.select("meta[itemprop='gtin13']")

    if len(meta_tags) == 0:
        return None

    gtin = meta_tags[0]["content"]
    return _normalise_gtin14(gtin)


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


def find_gtin_from_gs_url(offer_url: str, expected_gtin: str):
    offer_url_after_redirect = urllib.parse.parse_qs(
        urllib.parse.urlparse(offer_url).query
    )["q"][0]

    try:
        gtin_from_offer = find_gtin_from_retailer_url(
            offer_url_after_redirect, expected_gtin
        )
    except Exception as e:
        logger.warning(e)
        gtin_from_offer = None

    return gtin_from_offer


def __navigate_to_product_page(product_id: str, country: str):
    # insert some delay betwwen requests to google shopping
    time.sleep(INTER_NAVIGATION_DELAY)

    url = f"https://www.google.com/shopping/product/{product_id}/offers?hl=en&gl={country}"

    resp = helpers.requests.get(
        url,
        headers={"User-Agent": user_agents.choose_random()},
        cookies=GOOGLE_SHOPPING_COOKIES,
        proxy_country=product_proxy_country,
    )
    if resp.status_code == 429:
        raise Exception("Too many requests")
    html = resp.text
    soup = BeautifulSoup(html, features="html.parser")

    return soup


def extract_product_image(product_id: str, country: str):
    soup = __navigate_to_product_page(product_id, country)

    image = soup.select_one("img.r4m4nf")

    if not image:
        return None

    return image["src"] if image.has_attr("src") else None


def search_for_gtin_within_offers(
    product_id: str, country: str, expected_gtin: Optional[str] = None
) -> Optional[str]:
    soup = __navigate_to_product_page(product_id, country)

    all_offers = soup.select("tr.sh-osd__offer-row")
    offers_dict = {}
    for offer in all_offers:
        offer_retailer = offer.select_one("a.b5ycib").text.replace(
            "Opens in a new window", ""
        )
        offer_url = offer.select_one("a.b5ycib")["href"]

        offers_dict[offer_retailer] = offer_url

    # Parallelize going to each of the individual retailers
    futures = [
        asyncio.get_event_loop().run_in_executor(
            None,
            functools.partial(
                find_gtin_from_gs_url,
                offer_url,
                expected_gtin=expected_gtin,
            ),
        )
        for offer_retailer, offer_url in offers_dict.items()
    ]
    gtins_from_offers = asyncio.get_event_loop().run_until_complete(
        asyncio.gather(*futures)
    )

    aggregated_gtins = {}
    # count the number of times a gtin appears
    for gtin in gtins_from_offers:
        if not gtin:
            continue
        aggregated_gtins[gtin] = aggregated_gtins.get(gtin, 0) + 1

    if not aggregated_gtins:
        products_without_gtin.add((product_id, country))
        return None  # No gtins found

    # the one gtin with the most count is the gtin of this product id
    gtin_from_offer = max(aggregated_gtins.keys(), key=aggregated_gtins.get)

    id_to_gtin_cache[product_id] = gtin_from_offer
    gtin_to_id_cache[gtin_from_offer] = product_id

    return gtin_from_offer


def search_for_gtin(
    product_id: str, search_gtin: str, country: str
) -> Tuple[str, Optional[str]]:
    if product_id in id_to_gtin_cache:
        gtin_for_product = id_to_gtin_cache[product_id]
        if gtin_for_product == search_gtin:
            return product_id, gtin_for_product

        return product_id, None

    if (product_id, country) in products_without_gtin:
        return product_id, None

    variant_id, gtin_from_offer = search_for_gtin_within_variants(
        product_id, country, expected_gtin=search_gtin
    )

    if gtin_from_offer == search_gtin:
        return variant_id, search_gtin

    return product_id, None


def search_for_gtin_within_variants(
    product_id: str,
    country: str,
    expected_gtin: Optional[str] = None,
    known_variant_products=None,
    retry_ttl=3,
) -> Tuple[str, Optional[str]]:
    if known_variant_products is None:
        known_variant_products = []

    if (product_id, country) in products_without_gtin:
        return product_id, None

    if product_id in id_to_gtin_cache:
        return product_id, id_to_gtin_cache[product_id]

    time.sleep(INTER_NAVIGATION_DELAY)

    url = f"https://www.google.com/shopping/product/{product_id}?hl=en&gl={country}"
    try:
        resp = helpers.requests.get(
            url,
            headers={"User-Agent": user_agents.choose_random()},
            cookies=GOOGLE_SHOPPING_COOKIES,
            proxy_country=product_proxy_country,
        )
    except ProxyError as e:
        logger.warning("Proxy error encountered, will retry")
        time.sleep(2 ** (3 - retry_ttl))
        return search_for_gtin_within_variants(
            product_id,
            country,
            expected_gtin,
            known_variant_products,
            retry_ttl=retry_ttl - 1,
        )

    html = resp.text
    soup = BeautifulSoup(html, features="html.parser")

    gtin_for_id = search_for_gtin_within_offers(product_id, country, expected_gtin)
    if gtin_for_id == expected_gtin or expected_gtin is None:
        return product_id, gtin_for_id

    all_variants = soup.select("a.sh-dvc__item")
    sub_variant_products = set()
    for variant in all_variants:
        variant_url = variant["href"]
        variant_id = variant_url.split("?")[0].split("/")[-1]

        if variant_id not in known_variant_products:
            sub_variant_products.add(variant_id)

    for variant_id in sub_variant_products:
        sub_variant_id, gtin = search_for_gtin_within_variants(
            variant_id,
            country,
            expected_gtin,
            known_variant_products=known_variant_products + list(sub_variant_products),
        )

        if gtin == expected_gtin:
            return sub_variant_id, gtin

    return product_id, None


def find_product_id_multiple_markets(
    name: str, gtin: str, countries=None, brand: str = "GUBI"
) -> Optional[str]:
    if countries is None:
        countries = ["dk", "se", "de"]

    for country in tqdm(countries, desc="Markets"):
        id_in_country = find_product_id(name, gtin, country, brand)

        if id_in_country is not None:
            return id_in_country

    return None


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

    time.sleep(INTER_SEARCH_DELAY)

    url = f"https://www.google.com/search?q={search_term}&gl={country}&hl=en&tbm=shop"
    resp = helpers.requests.get(
        url,
        headers={"User-Agent": user_agents.choose_random()},
        cookies=GOOGLE_SHOPPING_COOKIES,
        proxy_country=search_proxy_country,
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
    ][:12]

    visited_product_pages_count = 0
    for possible_product_id in tqdm(possible_product_ids, "Google Shopping products"):
        variant_id, found_gtin = search_for_gtin(possible_product_id, gtin, country)
        visited_product_pages_count += 1

        if found_gtin:
            logger.info(
                "Visited product pages",
                visited_product_pages_count=visited_product_pages_count,
            )
            return variant_id

    logger.info(
        "Visited product pages",
        visited_product_pages_count=visited_product_pages_count,
    )
    return None


@app.command()
def run(products_file: str, default_brand: Annotated[str, typer.Argument()] = "Muuto"):
    logging.basicConfig(filename="output/logs", encoding="utf-8", level=logging.DEBUG)
    products = []

    # read the gtin and product name from the csv file
    with open(products_file, "r") as f:
        csv_reader = csv.reader(f)
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
                products_without_gtin.add((row[0], row[1]))
    countries = ["dk", "se", "de"]

    for product in tqdm(products, desc="Input products"):
        logger.info(
            "Starting with parameters",
            product_name=product[1],
            gtin=product[0],
            brand=product[2],
        )
        gtin, name, brand = product
        gtin = _normalise_gtin14(gtin)

        product_id = find_product_id_multiple_markets(
            name=name, gtin=gtin, countries=countries, brand=brand
        )

        logger.info("Found product id", id=product_id)
        write_output()

        with open("output/products_results.csv", "a") as f:
            f.write(f"{gtin},{product_id if product_id else ''}\n")


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
def explore_all_variants(product_id: str, country: str, expected_gtin: str):
    search_for_gtin_within_variants(product_id, country, expected_gtin)

    write_output()


@app.command()
def extract_gtin_from_page(target_url: str):
    gtin = find_gtin_from_retailer_url(target_url)

    logger.info("Found gtin", gtin=gtin)


@app.command()
def extract_gtin_from_gs_variant(product_id: str, country: str):
    gtin = search_for_gtin_within_offers(product_id, country)

    print(gtin)


@app.command()
def fetch_images_for_result(
    result_dir: Annotated[Optional[str], typer.Argument()] = "output"
):
    products_file = os.path.join(result_dir, "products_results.csv")
    images_file = os.path.join(result_dir, "products_results_with_images.csv")

    results = []
    with open(products_file, "r") as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            results.append(row)

    results_with_images = []
    for r in tqdm(results):
        if not r[1]:
            continue  # skip products we haven't found

        for c in ["DE", "NL", "FR", "DK"]:
            image_url = extract_product_image(r[1], c)
            if image_url is not None:
                break

        results_with_images.append(r + [image_url])

    with open(images_file, "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(results_with_images)


@app.command()
def find_single_product(
    gtin: str,
    name: str,
    brand: Annotated[Optional[str], typer.Argument()],
    countries: Annotated[Optional[List[str]], typer.Argument()],
):
    logging.basicConfig(filename="output/logs", encoding="utf-8", level=logging.DEBUG)
    product_id = find_product_id_multiple_markets(name, gtin, countries, brand)
    print(product_id)


if __name__ == "__main__":
    app()
