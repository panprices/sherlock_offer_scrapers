import pytest

from sherlock_offer_scrapers.scrapers import kelkoo


@pytest.mark.integration
def test_scrape():
    gtin = "08806091153807"
    offers = kelkoo.scrape(gtin)
    assert len(offers) > 0
