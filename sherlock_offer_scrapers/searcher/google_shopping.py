import asyncio
import csv
import functools
import os
import time
import urllib.parse
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from tqdm import tqdm

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.scrapers.google_shopping import (
    user_agents,
    uule_of_country,
)
from sherlock_offer_scrapers.searcher.generic import find_gtin_from_retailer_url
from structlog import get_logger
from requests.exceptions import ProxyError

logger = get_logger()


class GoogleShoppingSearcher:
    id_to_gtin_cache = {}
    searches_cache = set()
    products_without_gtin = set()
    ad_links = set()

    INTER_SEARCH_DELAY = 0
    INTER_NAVIGATION_DELAY = 0

    search_proxy_country = "SE"
    product_proxy_country = "SE"

    GOOGLE_SHOPPING_COOKIES = {
        "SOCS": "CAESNQgCEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwMTAyLjA1X3AwGgJlbiACGgYIgI3drAY",
        "CONSENT": "PENDING+105",
    }

    def find_gtin_from_gs_url(
        self, offer_url: str, expected_gtin: Optional[str], expected_sku: Optional[str]
    ):
        offer_url_after_redirect = urllib.parse.parse_qs(
            urllib.parse.urlparse(offer_url).query
        )["q"][0]

        try:
            gtin_from_offer = find_gtin_from_retailer_url(
                offer_url_after_redirect, expected_gtin, expected_sku
            )
        except Exception as e:
            logger.warning(e)
            gtin_from_offer = None

        return gtin_from_offer

    def __navigate_to_product_page_base(self, url: str):
        # insert some delay betwwen requests to google shopping
        time.sleep(self.INTER_NAVIGATION_DELAY)

        resp = helpers.requests.get(
            url,
            headers={"User-Agent": user_agents.choose_random()},
            cookies=self.GOOGLE_SHOPPING_COOKIES,
            proxy_country=self.product_proxy_country,
        )
        if resp.status_code == 429:
            raise Exception("Too many requests")
        html = resp.text
        soup = BeautifulSoup(html, features="html.parser")

        return soup

    def __navigate_to_product_page(self, product_id: str, country: str):
        url = f"https://www.google.com/shopping/product/{product_id}/offers?hl=en&gl={country}"
        return self.__navigate_to_product_page_base(url)

    def __navigate_to_single_offer_product_page(self, product_id: str, country: str):
        """Example product_id: epd:8370985928704265029,eto:8370985928704265029_0,pid:8370985928704265029"""

        url = f"https://www.google.com/shopping/product/1?prds={product_id}&hl=en&gl={country}"
        return self.__navigate_to_product_page_base(url)

    def extract_product_image(self, product_id: str, country: str):
        if product_id.isnumeric():
            soup = self.__navigate_to_product_page(product_id, country)
            image = soup.select_one("img.r4m4nf")
        else:  # product_id is like epd:8370985928704265029,eto:8370985928704265029_0,pid:8370985928704265029
            soup = self.__navigate_to_single_offer_product_page(product_id, country)
            image = soup.select_one("img.sh-div__image.sh-div__current")

        if not image:
            return None

        return image["src"] if image.has_attr("src") else None

    def search_for_gtin_within_offers(
        self,
        product_id: str,
        country: str,
        expected_gtin: Optional[str] = None,
        expected_sku: Optional[str] = None,
    ) -> Optional[str]:
        soup = self.__navigate_to_product_page(product_id, country)

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
                    self.find_gtin_from_gs_url,
                    offer_url,
                    expected_gtin=expected_gtin,
                    expected_sku=expected_sku,
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
            self.products_without_gtin.add((product_id, country))
            return None  # No gtins found

        # the one gtin with the most count is the gtin of this product id
        gtin_from_offer = max(aggregated_gtins.keys(), key=aggregated_gtins.get)

        self.id_to_gtin_cache[product_id] = gtin_from_offer

        return gtin_from_offer

    def search_for_gtin(
        self, product_id: str, search_gtin: str, search_sku: str, country: str
    ) -> Tuple[str, Optional[str]]:
        if product_id in self.id_to_gtin_cache:
            gtin_for_product = self.id_to_gtin_cache[product_id]
            if gtin_for_product == search_gtin:
                return product_id, gtin_for_product

            return product_id, None

        if (product_id, country) in self.products_without_gtin:
            return product_id, None

        variant_id, gtin_from_offer = self.search_for_gtin_within_variants(
            product_id, country, expected_gtin=search_gtin, expected_sku=search_sku
        )

        if gtin_from_offer == search_gtin:
            return variant_id, search_gtin

        return product_id, None

    def search_for_gtin_within_variants(
        self,
        product_id: str,
        country: str,
        expected_gtin: Optional[str] = None,
        expected_sku: Optional[str] = None,
        known_variant_products=None,
        retry_ttl=3,
    ) -> Tuple[str, Optional[str]]:
        if known_variant_products is None:
            known_variant_products = []

        if (product_id, country) in self.products_without_gtin:
            return product_id, None

        if product_id in self.id_to_gtin_cache:
            return product_id, self.id_to_gtin_cache[product_id]

        time.sleep(self.INTER_NAVIGATION_DELAY)

        url = f"https://www.google.com/shopping/product/{product_id}?hl=en&gl={country}"
        try:
            resp = helpers.requests.get(
                url,
                headers={"User-Agent": user_agents.choose_random()},
                cookies=self.GOOGLE_SHOPPING_COOKIES,
                proxy_country=self.product_proxy_country,
            )
        except ProxyError as e:
            logger.warning("Proxy error encountered, will retry")
            time.sleep(2 ** (3 - retry_ttl))
            return self.search_for_gtin_within_variants(
                product_id,
                country,
                expected_gtin,
                known_variant_products,
                retry_ttl=retry_ttl - 1,
            )

        html = resp.text
        soup = BeautifulSoup(html, features="html.parser")

        gtin_for_id = self.search_for_gtin_within_offers(
            product_id, country, expected_gtin, expected_sku
        )
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
            sub_variant_id, gtin = self.search_for_gtin_within_variants(
                variant_id,
                country,
                expected_gtin,
                known_variant_products=known_variant_products
                + list(sub_variant_products),
            )

            if gtin == expected_gtin:
                return sub_variant_id, gtin

        return product_id, None

    def find_product_id_multiple_markets(
        self,
        name: str,
        gtin: Optional[str],
        sku: Optional[str],
        countries=None,
        brand: str = "GUBI",
    ) -> Optional[str]:
        if countries is None:
            countries = ["DK", "SE", "DE"]

        for country in tqdm(countries, desc="Markets"):
            id_in_country = self.find_product_id(name, gtin, sku, country, brand)

            if id_in_country is not None:
                return id_in_country

        return None

    def find_product_id(
        self,
        name: str,
        gtin: Optional[str],
        sku: Optional[str],
        country: str = "se",
        brand: str = "GUBI",
    ) -> Optional[str]:
        """
        Find product_id of a google shopping product based on name and GTIN.

        The idea is to go through all the google shopping products that are returned when searching for the name and match
        them based on the GTIN we extract from one of the offers
        """

        if not gtin and not sku:
            return None

        main_name = name.split("(")[0].strip()
        full_name = f"{brand} {main_name}" if brand not in main_name else main_name
        search_term = urllib.parse.quote(full_name)

        time.sleep(self.INTER_SEARCH_DELAY)

        url = f"https://www.google.com/search?q={search_term}&gl={country}&hl=en&tbm=shop&uule={uule_of_country[country]}"
        resp = helpers.requests.get(
            url,
            headers={"User-Agent": user_agents.choose_random()},
            cookies=self.GOOGLE_SHOPPING_COOKIES,
            proxy_country=self.search_proxy_country,
        )
        if resp.status_code == 429:
            raise Exception("Too many requests")

        html = resp.text
        soup = BeautifulSoup(html, features="html.parser")

        all_a_tags = soup.select("a.Lq5OHe")
        # Only consider links to google shopping products. Ignore links directly to seller websites.
        product_a_tags = [a for a in all_a_tags if "/shopping/product/" in a["href"]]
        possible_product_ids = [
            a["href"].split("/shopping/product/")[1].split("?")[0]
            for a in product_a_tags
            # /shopping/product/2336121681419728525?q=05400653007411&hl=en&... -> 2336121681419728525
        ][:12]

        ad_tags = soup.find_all("a", attrs={"data-offer-id": True})
        current_ad_links = [
            (
                f"www.google.com{a['href']}"
                if a["href"].startswith("/")
                else a["href"],
                gtin,
                sku,
            )
            for a in ad_tags
        ]
        self.ad_links.update(current_ad_links)

        visited_product_pages_count = 0
        for possible_product_id in tqdm(
            possible_product_ids, "Google Shopping products"
        ):
            variant_id, found_gtin = self.search_for_gtin(
                possible_product_id, gtin, sku, country
            )
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

    def load_from_disk(self):
        if os.path.exists("output/id_to_gtin_cache.csv"):
            with open("output/id_to_gtin_cache.csv", "r") as f:
                csv_reader = csv.reader(f)
                next(csv_reader)
                for row in csv_reader:
                    self.id_to_gtin_cache[row[0]] = row[1]

        if os.path.exists("output/products_without_gtin.csv"):
            with open("output/products_without_gtin.csv", "r") as f:
                csv_reader = csv.reader(f)
                next(csv_reader)
                for row in csv_reader:
                    self.products_without_gtin.add((row[0], row[1]))

    def save_to_disk(self):
        # Save id_to_gtin_cache to a csv file
        with open("output/id_to_gtin_cache.csv", "w") as f:
            f.write("product_id,gtin\n")
            for product_id, gtin in self.id_to_gtin_cache.items():
                f.write(f"{product_id},{gtin}\n")

        # Save the products without a gtin
        with open("output/products_without_gtin.csv", "w") as f:
            f.write("product_id\n")
            for product_id, country in self.products_without_gtin:
                f.write(f"{product_id},{country}\n")

        with open("output/ad_links.csv", "w") as f:
            f.write("ad_link\n")
            for ad_link in self.ad_links:
                f.write(f'{ad_link[0]},{ad_link[1]},"{ad_link[2]}"\n')
