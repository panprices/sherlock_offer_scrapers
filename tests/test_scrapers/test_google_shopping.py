import pytest

from sherlock_offer_scrapers.scrapers import google_shopping
from sherlock_offer_scrapers.scrapers.google_shopping import parser


def test_scrape():
    gtin = "08806091153807"
    cached_offer_urls = {
        "google_shopping_SE": "https://www.google.com/shopping/product/3112645306492221763",
    }
    offers = google_shopping.scrape(gtin, cached_offer_urls)
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
