import pytest
import asyncio

import bs4

from sherlock_offer_scrapers.scrapers import google_shopping
from sherlock_offer_scrapers.scrapers.google_shopping import parser


def test_scrape():
    gtin = "08806091153807"
    cached_offer_urls = {
        "google_shopping": "3112645306492221763",
    }
    offers = asyncio.run(google_shopping.scrape(gtin, cached_offer_urls))
    assert len(offers) > 0


@pytest.mark.parametrize(
    "input,expected",
    [
        (("19 990,00 kr", "SE"), (1999000, "SEK")),
        (("€1,449.00", "NL"), (144900, "EUR")),
        (("PLN 1,117.00", "PL"), (111700, "PLN")),
    ],
)
def test_extract_price_and_currency(input, expected):
    assert parser._extract_price_and_currency(*input) == expected


@pytest.mark.skip(reason="does not implement this test yet")
def test_parser_offer_page():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/gg_CH_cannot_parse_product_name.html", "r") as f:
        soup = bs4.BeautifulSoup(f)

    offers = parser.parser_offer_page(soup, "BE")
    print(offers)
