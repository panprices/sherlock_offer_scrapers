from bs4 import BeautifulSoup, Tag
import structlog
import re
import json

from sherlock_offer_scrapers import helpers
from sherlock_offer_scrapers.helpers.utils import gtin_to_ean
from sherlock_offer_scrapers.helpers.offers import Offer

logger = structlog.get_logger()
root_url = 'https://www.kuantokusta.pt'


def scrape(gtin: str) -> list[Offer]:
    return fetch_offers(gtin)


def fetch_offers(gtin: str) -> list[Offer]:
    ean = gtin_to_ean(gtin)
    url = f'{root_url}/search?q={ean}'
    response = helpers.requests.get(url)

    soup = BeautifulSoup(response.text, "html.parser")
    if len(soup.select(".products-empty")) > 0:
        logger.warn("Product does not exist")
        return []

    product_url = parse_results_page(soup)
    response = helpers.requests.get(product_url)
    soup = BeautifulSoup(response.text, "html.parser")

    return parse_product_page_by_json(soup)


def parse_results_page(soup: BeautifulSoup) -> str:
    """
    Takes the web page with the results from the search query and returns the url to
    the product page
    """

    product_element = soup.find('div', class_="product-item")
    image_element = product_element.find('a', class_="product-item-image")
    product_url = image_element['href']

    return f'{root_url}{product_url}'


def parse_product_page_by_json(soup: BeautifulSoup) -> list[Offer]:
    product_json = soup.find('script', id='__NEXT_DATA__', type='application/json').text
    product_dict = json.loads(product_json)
    page_props = product_dict['props']['pageProps']
    product = page_props['productPage']['product']

    dirty_description = page_props['productPageFeatures']['description']
    description = BeautifulSoup(dirty_description, 'html.parser').text
    specs = {g['name']: standardize_features_group(g['features'])
             for g in page_props['productPageFeatures']['featuresGroup']}
    images = product['images']
    category = [c['name'] for c in page_props['productPage']['breadcrumb'][:-1]]
    metadata = {
        'category': category,
        'description': description,
        'images': images,
        'specs': specs
    }

    return [{
        'offer_source': 'kuantokusta',
        'offer_url': o['businessRules']['cpc']['url'],
        'retail_prod_name': o['productName'],
        'retailer_name': o['storeName'],
        'country': 'pt',
        'price': round(o['price']),
        'currency': 'eur',
        'stock_status': 'unknown',
        'metadata': metadata
    } for o in product['offers']]


def standardize_features_group(features_group: list[dict]) -> dict:
    return {f['name']: f['value'] for f in features_group}


"""
###################################################################################
############################# NOT USED BELOW ######################################
###################################################################################
"""


def _parse_product_page_by_html(soup: BeautifulSoup) -> list[Offer]:
    """
    Takes the product page and returns the list of offers advertised on the web page

    NOT USED !!!
    This method looks at the html, but after that we found, a json with all the details we need
    This method is left here as a starting point in case the JSON disappears in the future
    """

    # we avoided using the class because it looks like compiled / obfuscated so it might change with a new version
    # with a future version of the website.
    # Class example: c-jPlLps

    result: list[Offer] = []
    offer_url_pattern = r'https:\/\/www\.kuantokusta\.pt\/follow\/products\/(\\d+)\/offers\/(\\d+)'
    url_elements = soup.find_all('a', href=True)
    for element in url_elements:
        if not re.match(offer_url_pattern, element['href']):
            continue
        text_element = next(element.find('h3').children, None)
        offer_name = text_element.string

        offer: Offer = {
            'offer_source': 'kuantokusta',
            'offer_url': element['href'],
            'retail_prod_name': offer_name,
            'retailer_name': '',  # TODO: parse retailer name
            'country': 'pt',
            'price': round(extract_price(element)),
            'currency': 'eur',
            'stock_status': 'unknown',
            'metadata': {}  # TODO: parse metadata
        }

        result.append(offer)

    return result


def extract_price(element: Tag) -> float:
    price_elements = element.find_all('span', text=re.compile('\\d+,\\d{2}€'))

    min_depth = 9999
    offer_price = 0
    for price_element in price_elements:
        depth = find_depth(element, price_element)
        if depth < min_depth:
            min_depth = depth
            offer_price = float(price_element.string[:-1])

    return offer_price


def find_depth(root: Tag, element: Tag) -> int:
    if root == element or not element.parent:
        return 0

    return find_depth(root, element.parent) + 1
