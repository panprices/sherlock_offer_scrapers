import pathlib

import bs4
import pytest

from sherlock_offer_scrapers.helpers.offers import Offer
from sherlock_offer_scrapers.scrapers.kuantokusta import kuantokusta


@pytest.mark.unit
def test_normal_search():
    normal_search_page = load_test_page('normal_result.html')
    product_url = kuantokusta.parse_results_page(normal_search_page)

    assert product_url == 'https://www.kuantokusta.pt/p/5637007/xiaomi-trotinete-mi-electric-scooter-essential'


@pytest.mark.unit
def test_normal_product_page():
    normal_product_page = load_test_page('product_page_normal.html')
    offers = kuantokusta.parse_product_page(normal_product_page)

    assert len(offers) == 14
    assert all([o['offer_url'] is not None for o in offers])


@pytest.mark.unit
def test_no_next_data():
    no_next_data_page = load_test_page('no_next_data.html')
    offers = kuantokusta.parse_product_page(no_next_data_page)

    assert len(offers) == 17


@pytest.mark.unit
def test_search_one_retailer():
    search_one_retailer = load_test_page('search_one_retailer.html')
    offers: list[Offer] = kuantokusta.fetch_offers_from_search_page(search_one_retailer)

    assert len(offers) == 1
    assert offers[0] is not None
    assert offers[0]['retail_prod_name'] == 'Gre Piscina em Composite 326x186x96cm'
    assert offers[0]['price'] == 406990


def load_test_page(name: str) -> bs4.BeautifulSoup:
    directory = pathlib.Path(__file__).parent.resolve()
    with open(f'{directory}/data/{name}', 'r') as f:
        soup = bs4.BeautifulSoup(f, 'html.parser')

    return soup
