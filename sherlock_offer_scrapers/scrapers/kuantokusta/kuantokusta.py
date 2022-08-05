import json
import re
import urllib
from typing import Dict

import requests
import structlog
from bs4 import BeautifulSoup, Tag

from sherlock_offer_scrapers.helpers.offers import Offer
from sherlock_offer_scrapers.helpers.utils import gtin_to_ean

logger = structlog.get_logger()
root_url = 'https://www.kuantokusta.pt'


def scrape(gtin: str) -> list[Offer]:
    return fetch_offers(gtin)


def scrapfly_request(url: str) -> requests.Response:
    scrapfly_url = (
        f"https://api.scrapfly.io/scrape"
        "?key=9a8e8b7f96624616bb67b4129bdacd2b"
        f"&url={urllib.parse.quote(url)}"
        "&tags=player%2Cproject%3Adefault"
        "&country=pt"
        "&asp=true"
    )

    return requests.get(scrapfly_url)


def fetch_offers(gtin: str) -> list[Offer]:
    ean = gtin_to_ean(gtin)
    url = f'{root_url}/search?q={ean}'
    response = scrapfly_request(url)
    response_object = json.loads(response.text)
    if response.status_code >= 400 or response_object['result']['error']:
        logger.warn(f"Received error code from Scrapfly API: {response.status_code}", payload=response_object)
        return []

    soup = BeautifulSoup(response_object['result']['content'], "html.parser")
    return fetch_offers_from_search_page(soup)


def fetch_offers_from_search_page(soup: BeautifulSoup) -> list[Offer]:
    if len(soup.select(".products-empty")) > 0:
        logger.warn("Product does not exist")
        return []

    product_page_url = parse_results_page(soup)
    if product_page_url == f'{root_url}#':
        return [parse_results_page_with_unique_retailer(soup)]

    response = scrapfly_request(product_page_url)
    response_object = json.loads(response.text)
    if response.status_code >= 400 or response_object['result']['error']:
        logger.warn(f"Received error code from Scrapfly API: {response.status_code}", payload=response_object)
        return []
    soup = BeautifulSoup(response_object['result']['content'], "html.parser")

    return parse_product_page(soup)


def parse_results_page(soup: BeautifulSoup) -> str:
    """
    Takes the web page with the results from the search query and returns the url to
    the product page
    """

    product_element = soup.find('div', class_="product-item")
    image_element = product_element.find('a', class_="product-item-image")
    product_url = image_element['href']

    return f'{root_url}{product_url}'


def parse_results_page_with_unique_retailer(soup: BeautifulSoup) -> Offer:
    """
    There are special cases where only one retailer has that product in its offer, where the price aggregator will no
    longer redirect to its product page, but it would directly redirect to that unique retailer.

    In that case, we should return that offer directly from the search page
    """

    offer_url = soup.find('a', class_='product-item-image')['onclick'].split(';')[0].split(',')[2][2:-1]
    retailer_name: str = soup.find('span', class_='product-item-store-image').find('img')['alt']
    product_element = soup.find('div', class_='product-item')
    product_name = product_element.find('h2', itemprop='name').text.strip()
    price = int(float(product_element.find('a', class_='product-item-price')['data-max-price-raw']) * 100)

    return {
        'offer_source': 'kuantokusta_PT',
        'offer_url': offer_url,
        'retail_prod_name': product_name,
        'retailer_name': retailer_name,
        'country': 'PT',
        'price': price,
        'currency': 'eur',
        'stock_status': 'unknown',
        'metadata': None
    }


def parse_product_page(soup: BeautifulSoup) -> list[Offer]:
    product_json_element = soup.find('script', id='__NEXT_DATA__', type='application/json')
    offers = parse_product_page_by_json(product_json_element) if product_json_element is not None \
        else parse_product_page_by_schema_org(soup)

    # Sometimes this website displays offers without actual link to them, and this generates errors later in the
    # search process. So we choose to filter them out right away.
    return [o for o in offers if o['offer_url'] is not None]


def parse_product_page_by_json(product_json_element: Tag) -> list[Offer]:
    product_json = product_json_element.text
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
        'offer_source': 'kuantokusta_PT',
        'offer_url': o['businessRules']['cpc']['url'],
        'retail_prod_name': o['productName'],
        'retailer_name': o['storeName'],
        'country': 'PT',
        'price': round(float(o['price']) * 100),
        'currency': 'eur',
        'stock_status': 'unknown',
        'metadata': json.dumps(metadata)
    } for o in product['offers']]


def parse_product_page_by_schema_org(soup: BeautifulSoup) -> list[Offer]:
    product_element = soup.find('div', itemtype='http://schema.org/Product')
    if product_element is None:
        logger.warn('Neither __NEXT_DATA__, nor schema.org information is available', soup.contents)
        return []

    result: list[Offer] = []
    product_url = product_element.find('meta', itemprop='url')['content']
    product_id = product_url.split('/')[-2]

    metadata = extract_metadata_schema_org(soup)
    for offer_element in soup.find_all('div', itemtype='http://schema.org/Offer'):
        retailer_id = offer_element.find('span', class_='store-item-image')['data-seller'][2:]
        retailer_name: str = offer_element.find('div', itemtype='http://schema.org/Organization')\
            .find('meta', itemprop='name')['content']

        offer: Offer = {
            'offer_source': 'kuantokusta_PT',
            'offer_url': f'{root_url}/follow/products/{product_id}/offers/{retailer_id}',
            'retail_prod_name': offer_element.find('p', itemprop='alternateName').text,
            'retailer_name': retailer_name,
            'country': 'PT',
            'price': round(float(offer_element.find('meta', itemprop='price')['content']) * 100),
            'currency': 'eur',
            'stock_status': 'unknown',
            'metadata': metadata
        }
        result.append(offer)

    return result


def extract_metadata_schema_org(soup: BeautifulSoup) -> str:
    specs_element = soup.find('div', class_='product-specifications')
    specs: Dict[str, Dict[str, str]] = {}
    for specs_category in specs_element.find_all('div', class_='row'):
        category_name = specs_category.find('h3', class_='title').text
        specs[category_name] = {}
        for spec in specs_category.find_all('div', class_='product-specification-item'):
            specs[category_name][spec.find('p', class_='product-specification-label').text] = \
                spec.find('p', class_='product-specification-value').text

    description = soup.find('head').find('meta', {'name': 'description'})['content']
    category = [item.text for item in soup.find('ul', class_='breadcrumb').find_all('a')[1:]]
    images = [i['url_600'] for i in json.loads(soup.find('input', {'name': 'mobile-images'})['value'])]

    return json.dumps({
        'description': description,
        'category': category,
        'images': images,
        'specs': specs
    })


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
        if text_element is None:  # if it still doesn't have the expected structure, we skip it
            continue

        offer_name = text_element.string

        offer: Offer = {
            'offer_source': 'kuantokusta_PT',
            'offer_url': element['href'],
            'retail_prod_name': offer_name,
            'retailer_name': '',  # TODO: parse retailer name
            'country': 'pt',
            'price': round(extract_price(element) * 100),
            'currency': 'eur',
            'stock_status': 'unknown',
            'metadata': None
        }

        result.append(offer)

    return result


def extract_price(element: Tag) -> float:
    price_elements = element.find_all('span', text=re.compile('\\d+,\\d{2}€'))

    min_depth = 9999
    offer_price = 0.0
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
