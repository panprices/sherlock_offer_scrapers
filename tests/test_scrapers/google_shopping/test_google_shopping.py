import pytest
import asyncio

import bs4

from sherlock_offer_scrapers.scrapers import google_shopping
from sherlock_offer_scrapers.scrapers.google_shopping import parser


@pytest.mark.integration
def test_scrape():
    gtin = "08806091153807"
    cached_offer_urls = {
        "google_shopping": "3112645306492221763",
    }
    offers, errors = asyncio.run(google_shopping.scrape(gtin, cached_offer_urls))
    assert len(offers) > 0
    assert len(errors) == 0


@pytest.mark.unit
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


@pytest.mark.unit
def test_parser_offer_page_variant_0():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/variant_0.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "NL")

    assert len(offers) == 6

    assert offers[0] == {
        "offer_source": "google_shopping_NL",
        "offer_url": "https://www.google.com/aclk?sa=L&ai=DChcSEwiTofLZ8tH1AhUZqncKHSzjCVgYABABGgJlZg&sig=AOD64_1L0RK8PcIMOzLLxeyFEdN7RB9ZtA&ctype=5&q=&ved=0ahUKEwiLwe_Z8tH1AhVMg_0HHYSmC84Q2ikIGA&adurl=",
        "retail_prod_name": 'AOC Agon AG493UCX 49" Curved Gaming Monitor(25)',
        "retailer_name": "buykingston.co.uk",
        "country": "NL",
        "price": 112665,
        "currency": "EUR",
        "stock_status": "in_stock",
        "metadata": {
            "image": "https://encrypted-tbn2.gstatic.com/shopping?q=tbn:ANd9GcRRI8YV7Fx14oOr8dR0XXmpWDy-kiQqEv79YUfcO2gjjTGIKsPHtMy-9gkO9HJLRKGLhPP67xI&usqp=CAY"
        },
    }

    assert offers[1] == {
        "offer_source": "google_shopping_NL",
        "offer_url": "https://www.google.com/aclk?sa=L&ai=DChcSEwiTofLZ8tH1AhUZqncKHSzjCVgYABADGgJlZg&sig=AOD64_3eUyndFT115pX3JPzpseH2xOFEpQ&ctype=5&q=&ved=0ahUKEwiLwe_Z8tH1AhVMg_0HHYSmC84Q2ikIGw&adurl=",
        "retail_prod_name": 'AOC Agon AG493UCX 49" Curved Gaming Monitor(25)',
        "retailer_name": "Tinkerer Computers & Components",
        "country": "NL",
        "price": 119194,
        "currency": "EUR",
        "stock_status": "in_stock",
        "metadata": {
            "image": "https://encrypted-tbn2.gstatic.com/shopping?q=tbn:ANd9GcRRI8YV7Fx14oOr8dR0XXmpWDy-kiQqEv79YUfcO2gjjTGIKsPHtMy-9gkO9HJLRKGLhPP67xI&usqp=CAY"
        },
    }

    assert offers[5] == {
        "offer_source": "google_shopping_NL",
        "offer_url": "https://www.google.com/aclk?sa=L&ai=DChcSEwiTofLZ8tH1AhUZqncKHSzjCVgYABALGgJlZg&sig=AOD64_2EHLoapZU7SQY19NlfEjFRWpN42A&ctype=5&q=&ved=0ahUKEwiLwe_Z8tH1AhVMg_0HHYSmC84Q2ikIKg&adurl=",
        "retail_prod_name": 'AOC Agon AG493UCX 49" Curved Gaming Monitor(25)',
        "retailer_name": "Dustin Home NL",
        "country": "NL",
        "price": 123602,
        "currency": "EUR",
        "stock_status": "in_stock",
        "metadata": {
            "image": "https://encrypted-tbn2.gstatic.com/shopping?q=tbn:ANd9GcRRI8YV7Fx14oOr8dR0XXmpWDy-kiQqEv79YUfcO2gjjTGIKsPHtMy-9gkO9HJLRKGLhPP67xI&usqp=CAY"
        },
    }


@pytest.mark.unit
def test_parser_offer_page_variant_1():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/variant_1.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "BE")

    assert len(offers) == 2

    assert offers[0]["offer_source"] == "google_shopping_BE"
    assert (
        offers[0]["offer_url"]
        == "https://www.galaxus.ch/de/product/14341970?utm_campaign=organicshopping&utm_source=google&utm_medium=organic"
    )
    assert offers[0]["retail_prod_name"] == "AOC Monitor AG493UCX"
    assert offers[0]["retailer_name"] == "galaxus.ch"
    assert offers[0]["country"] == "BE"
    assert offers[0]["price"] == 102200
    assert offers[0]["currency"] == "CHF"
    assert offers[0]["stock_status"] == "in_stock"
    assert offers[0]["metadata"] == None

    assert offers[1]["offer_source"] == "google_shopping_BE"
    assert (
        offers[1]["offer_url"]
        == "https://www.digitec.ch/de/product/14341970?utm_campaign=organicshopping&utm_source=google&utm_medium=organic"
    )
    assert offers[1]["retail_prod_name"] == "AOC Monitor AG493UCX"
    assert offers[1]["retailer_name"] == "digitec.ch"
    assert offers[1]["country"] == "BE"
    assert offers[1]["price"] == 102200
    assert offers[1]["currency"] == "CHF"
    assert offers[1]["stock_status"] == "in_stock"
    assert offers[1]["metadata"] == None


@pytest.mark.unit
def test_parser_offer_page_nzd_currency():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/nzd_currency.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "PT")

    assert len(offers) == 16

    assert offers[0] == {
        "offer_source": "google_shopping_PT",
        "offer_url": "https://www.google.com/aclk?sa=L&ai=DChcSEwjr7qOCjdL1AhV_BaIDHWvjAMcYABABGgJsZQ&sig=AOD64_3v4BPx6YlNNhfQhKpUIJUs3KkxIQ&ctype=5&q=&ved=0ahUKEwjMg6GCjdL1AhWlk4sKHTggAIQQ2ikIGQ&adurl=",
        "retail_prod_name": 'ASUS PG259QNR 62.2 cm (24.5") 1920 x 1080 pixels Full HD LED Black(2)',
        "retailer_name": "PCDiga",
        "country": "PT",
        "price": 73990,
        "currency": "EUR",
        "stock_status": "in_stock",
        "metadata": {
            "image": "https://encrypted-tbn2.gstatic.com/shopping?q=tbn:ANd9GcQYfzPI5e1g2RQU_VO4lBeAYeh2362L87URvuHSbTVcaTfU5yAKrxk4wo4jb9NLoML_8g3xBzyYKElmgmK16E3fw5P4uHWqzO-JY4CzEIlTW1VN3MoWYhTzRQ&usqp=CAY"
        },
    }

    assert offers[1] == {
        "offer_source": "google_shopping_PT",
        "offer_url": "https://www.google.com/aclk?sa=L&ai=DChcSEwjr7qOCjdL1AhV_BaIDHWvjAMcYABADGgJsZQ&sig=AOD64_3YBYovJD-IkkhqsDl4epet-B9N7Q&ctype=5&q=&ved=0ahUKEwjMg6GCjdL1AhWlk4sKHTggAIQQ2ikIHw&adurl=",
        "retail_prod_name": 'ASUS PG259QNR 62.2 cm (24.5") 1920 x 1080 pixels Full HD LED Black(2)',
        "retailer_name": "Conrad Electronic International",
        "country": "PT",
        "price": 124899,
        "currency": "NZD",  # New Zealand Dollar. This is the strange part that is being tested
        "stock_status": "in_stock",
        "metadata": {
            "image": "https://encrypted-tbn2.gstatic.com/shopping?q=tbn:ANd9GcQYfzPI5e1g2RQU_VO4lBeAYeh2362L87URvuHSbTVcaTfU5yAKrxk4wo4jb9NLoML_8g3xBzyYKElmgmK16E3fw5P4uHWqzO-JY4CzEIlTW1VN3MoWYhTzRQ&usqp=CAY"
        },
    }


@pytest.mark.unit
def test_parser_offer_page_product_not_found_0():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/product_not_found_0.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "LT")

    assert len(offers) == 0


@pytest.mark.unit
def test_parser_offer_page_product_not_found_1():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/product_not_found_1.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "LT")

    assert len(offers) == 0


@pytest.mark.unit
def test_parser_offer_page_usd_currency():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/usd_currency.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "EE")

    assert len(offers) == 20

    assert offers[0] == {
        "offer_source": "google_shopping_EE",
        "offer_url": "https://www.google.com/aclk?sa=L&ai=DChcSEwimzoWv1NT1AhWBAOYKHSC_B9sYABABGgJscg&sig=AOD64_2mYVd5m8Dcwn2Gg4CG6BwcKCMuNQ&ctype=5&q=&ved=0ahUKEwjPv4Ov1NT1AhXooosKHXJQDi8Q2ikIGA&adurl=",
        "retail_prod_name": "Apple - AirTag Leather Loop - Saddle Brown(387)",
        "retailer_name": "Apple",
        "country": "EE",
        "price": 4154,
        "currency": "USD",
        "stock_status": "in_stock",
        "metadata": {
            "image": "https://encrypted-tbn2.gstatic.com/shopping?q=tbn:ANd9GcS2tFVHDdo52LocsfffA8q-lM_vOSlyiln3rB_FjLv_RYXLOTD1okoVmIO12nJ8XasAZ3nk2hDeUSs4aF9qmfAp0e6lEJtP3WnWGpbcl94FJeuz7OaNOjbxcw&usqp=CAY"
        },
    }


@pytest.mark.unit
def test_parser_offer_page_zero_price():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/zero_price.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "BE")

    for offer in offers:
        assert offer["price"] != 0

    assert len(offers) == 19


@pytest.mark.unit
def test_parser_offer_page_no_content():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/no_content.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "EE")

    assert len(offers) == 0


@pytest.mark.unit
def test_parser_offer_page_almost_no_content():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/almost_no_content.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "EE")

    assert len(offers) == 0


@pytest.mark.unit
def test_get_image_variant_0():
    import pathlib

    dir = pathlib.Path(__file__).parent.resolve()
    with open(f"{dir}/data/variant_0.html", "r") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")

    offers = parser.parser_offer_page(soup, "NL")

    for offer in offers:
        assert (
            offer["metadata"]["image"]
            == "https://encrypted-tbn2.gstatic.com/shopping?q=tbn:ANd9GcRRI8YV7Fx14oOr8dR0XXmpWDy-kiQqEv79YUfcO2gjjTGIKsPHtMy-9gkO9HJLRKGLhPP67xI&usqp=CAY"
        )
