import csv
import logging.config
import os.path
import random
import uuid
from typing import Optional, Annotated, List

import structlog
import typer
from google.cloud import storage
from structlog.dev import set_exc_info
from structlog.processors import (
    StackInfoRenderer,
    TimeStamper,
    add_log_level,
    LogfmtRenderer,
)
from tqdm import tqdm

from sherlock_offer_scrapers.persistence.db.db_source import DBProductsSource

from sherlock_offer_scrapers.persistence.db.db_sink import DBProductsResultSink
from sherlock_offer_scrapers.persistence.sink import ProductSearchResult
from sherlock_offer_scrapers.scrapers.google_shopping import uule_of_country
from sherlock_offer_scrapers.searcher.generic import (
    normalise_gtin14,
    find_gtin_from_retailer_url,
)
from sherlock_offer_scrapers.searcher.google_shopping import GoogleShoppingSearcher

app = typer.Typer(pretty_exceptions_show_locals=False)

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

google_shopping_searcher = GoogleShoppingSearcher()


@app.command()
def run(
    products_file: str,
    default_brand: Annotated[str, typer.Argument()] = "Muuto",
):
    logging.basicConfig(filename="output/logs", encoding="utf-8", level=logging.DEBUG)
    products = []

    # read the gtin and product name from the csv file
    with open(products_file, "r") as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            if len(row) == 4:
                products.append((row[0], row[1], row[2], row[3]))
            else:
                products.append((row[0], row[1], row[2], default_brand))

    google_shopping_searcher.load_from_disk()

    countries = [c for c in uule_of_country.keys()]

    # Select 4 countries at random. This ensures over time we cover all countries while making the script
    # take less time each week
    countries = random.sample(countries, 4)
    products = random.sample(products, 100)  # smaller run

    for c in tqdm(countries, desc="Countries"):
        for product in tqdm(products, desc="Input products"):
            logger.info(
                "Starting with parameters",
                product_name=product[2],
                gtin=product[1],
                sku=product[0],
                brand=product[3],
            )
            sku, gtin, name, brand = product
            gtin = normalise_gtin14(gtin)

            try:
                product_id = google_shopping_searcher.find_product_id(
                    name=name, gtin=gtin, sku=sku, country=c, brand=brand
                )

                logger.info("Found product id", id=product_id)
                google_shopping_searcher.save_to_disk()

                with open("output/products_results.csv", "a") as f:
                    f.write(f"{sku},{gtin},{product_id if product_id else ''}\n")
            except Exception as e:
                logger.warn("Exception encountered", exception=str(e))


@app.command()
def run_auto():
    """
    The purpose with this function is to connect to the db and create its own input, save its output, and sync the
    storage to google cloud storage.

    We want to have this no param script to run inside a container in Google Cloud Batch.
    """
    products_source = DBProductsSource()
    products = products_source.get_products()

    if not os.path.exists("input/"):
        os.makedirs("input/")

    # save to file
    with open("input/auto_input.csv", "w") as f:
        input_writer = csv.writer(f, delimiter=",", quotechar='"')
        for product in products:
            input_writer.writerow(
                [
                    product.sku,
                    product.gtin,
                    product.name,
                    product.brand_name,
                ]
            )

    if not os.path.exists("output/"):
        os.makedirs("output/")

    run("input/auto_input.csv")

    storage_client = storage.Client("panprices")
    bucket = storage_client.get_bucket("panprices_logs")
    run_id = uuid.uuid4().hex
    # Print not log, the logs go to the file on disk, we want to show this in console
    print(f"Logging run_id {run_id}")

    blob = bucket.blob(f"google_searches_cache/{run_id}/input.csv")
    blob.upload_from_filename("input/auto_input.csv")

    for file in os.listdir("output/"):
        blob = bucket.blob(f"google_searches_cache/{run_id}/{file}")
        blob.upload_from_filename(f"output/{file}")

    sink = DBProductsResultSink()
    product_results = []
    with open("output/products_results.csv") as results_file:
        csv_reader = csv.reader(results_file)
        for row in csv_reader:
            if len(row) < 3 or not row[2]:
                continue  # if we don't have an id now, we don't save it to the db

            product_results.append(
                ProductSearchResult(
                    sku=row[0],
                    gtin=row[1],
                    url=row[2],
                )
            )

    sink.persist(product_results)


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

    google_shopping_searcher.load_from_disk()

    for product_id in products:
        logger.info("Starting with parameters", product_id=product_id)

        google_shopping_searcher.search_for_gtin_within_offers(product_id, "no")

        # Save id_to_gtin_cache to a csv file
        google_shopping_searcher.save_to_disk()


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
    google_shopping_searcher.search_for_gtin_within_variants(
        product_id, country, expected_gtin
    )

    google_shopping_searcher.save_to_disk()


@app.command()
def extract_gtin_from_page(target_url: str):
    gtin = find_gtin_from_retailer_url(target_url)

    logger.info("Found gtin", gtin=gtin)


@app.command()
def extract_gtin_from_gs_variant(product_id: str, country: str):
    gtin = google_shopping_searcher.search_for_gtin_within_offers(product_id, country)

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

        for c in ["DK", "NL"]:
            image_url = google_shopping_searcher.extract_product_image(r[1], c)
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
    product_id = google_shopping_searcher.find_product_id_multiple_markets(
        name, gtin, countries, brand
    )
    print(product_id)


if __name__ == "__main__":
    app()
