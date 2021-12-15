from sherlock_offer_scrapers.scrapers import google_shopping


def test_scrape():
    gtin = "08806091153807"
    cached_offer_urls = {
        "google_shopping_SE": "https://www.google.com/shopping/product/3112645306492221763",
    }
    offers = google_shopping.scrape(gtin, cached_offer_urls)
    assert len(offers) > 0
