from sherlock_offer_scrapers.scrapers import idealo


def test_scrape():
    gtin = "00194715600645"
    cached_offer_urls = {
        "idealo_DE": "https://www.idealo.de/preisvergleich/OffersOfProduct/201386993",
        "idealo_UK": "https://www.idealo.co.uk/compare/201386993",
        "idealo_ES": "https://www.idealo.es/precios/201386993",
        "idealo_IT": "https://www.idealo.it/confronta-prezzi/201386993",
        "idealo_FR": "https://www.idealo.fr/prix/201386993",
        "idealo_AT": "https://www.idealo.at/preisvergleich/OffersOfProduct/201386993",
    }
    offers = idealo.scrape(gtin, cached_offer_urls)
    assert len(offers) > 0
