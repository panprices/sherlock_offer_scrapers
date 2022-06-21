import pathlib

import bs4
import pytest

from sherlock_offer_scrapers.scrapers.kuantokusta import kuantokusta


@pytest.mark.unit
def test_normal_search():
    normal_search_page = load_test_page('normal_result.html')
    product_url = kuantokusta.parse_results_page(normal_search_page)

    assert product_url == 'https://www.kuantokusta.pt/p/5637007/xiaomi-trotinete-mi-electric-scooter-essential'


def test_normal_product_page():
    normal_product_page = load_test_page('product_page_normal.html')
    offers = kuantokusta.parse_product_page_by_json(normal_product_page)

    assert len(offers) == 18


def load_test_page(name: str) -> bs4.BeautifulSoup:
    directory = pathlib.Path(__file__).parent.resolve()
    with open(f'{directory}/data/{name}', 'r') as f:
        soup = bs4.BeautifulSoup(f, 'html.parser')

    return soup
