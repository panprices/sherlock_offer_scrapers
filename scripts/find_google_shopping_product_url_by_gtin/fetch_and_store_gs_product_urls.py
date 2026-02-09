import os
import time
from typing import Optional
import logging
import json

import priceapi
from offers import publish_new_offer_urls

logger = logging.getLogger()


def find(gtins: list[str], country: str):
    products = fetch_products_using_priceapi(gtins, country)
    print(products)

    for gtin, google_pid in products.items():
        publish_new_offer_urls(gtin, {"google_shopping": google_pid})


def fetch_products_using_priceapi(gtins: list[str], country: str) -> dict[str, str]:
    job_id = priceapi.create_job(
        country=country.lower(),
        source="google_shopping",
        topic="product_and_offers",
        key="gtin",
        values=gtins,
    )
    job_status = _pull_for_job_completion(job_id)
    if job_status == "cancelled":
        raise Exception(
            f"The job {job_id} has been cancelled and thus received no data."
        )

    job_result = priceapi.get_result(job_id)

    this_dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(
        f"{this_dir_path}/job_results/{job_id}_result.json", "w", encoding="utf-8"
    ) as f:
        json.dump(job_result, f, indent=2)

    products = _parse_product_and_offers_result(job_result)

    return products


def _pull_for_job_completion(
    job_id: str, max_wait_time: int = 240, interval: float = 1.2
) -> Optional[str]:
    """Keep pulling for job completion every <interval> seconds for <max_wait_time> seconds.

    Note that min interval is 1 second.
    """

    start_time = time.time()
    time_elapsed = 0.0
    job_completed, status = False, None
    while time_elapsed < max_wait_time and not job_completed:
        time.sleep(interval)
        time_elapsed = time.time() - start_time

        job_completed, status = priceapi.job_completed(job_id)

    if not job_completed:
        raise Exception(f"Time limit of {max_wait_time} exceeded.")

    return status


def _parse_product_and_offers_result(job_result: dict) -> dict[str, str]:
    """Get Idealo's product id from job result from product_and_offers topic."""
    products = {}
    try:
        results = job_result["results"]
        for result in results:
            gtin = result["query"]["value"]
            product_id_found = True

            if not result["success"]:
                product_id_found = False
                reason = result["reason"]

                if reason == "to_be_searched":
                    logging.warning(
                        f"PriceAPI does not have the data for product {gtin} yet, reason: to_be_searched."
                    )
                # Other reasons
                logging.error(
                    f"Request for product {gtin} results in error. Reason: {reason}."
                )

            # Request is sucess, and "not found" is the correct result:
            if result.get("reason") == "not found":
                product_id_found = False
                logging.warning(f"PriceAPI said product {gtin} does not exist.")

            if product_id_found:
                content = result["content"]

                priceapi_gtins = content.get("gtins")
                priceapi_gtin = priceapi_gtins[0] if priceapi_gtins else None

                # ! CHECK IF PRICEAPI GTIN IS THE SAME AS OUR GTIN:
                if priceapi_gtin and (
                    priceapi_gtin.rjust(14, "0") != result["query"]["value"]
                ):
                    raise Exception(
                        "Product's gtin from the result does not our input gtin!"
                    )

                products[gtin] = content.get("id")
            else:
                products[gtin] = None

        return products

    except Exception as ex:
        logging.error("Error when parsing PriceAPI result.")
        raise ex


def check_correctness(gtin, google_pid):
    return True


if __name__ == "__main__":
    # COUNTRY = "SE"
    COUNTRY = "PT"

    from input_gtins import gtins

    chunk_size = 20
    for start_i in range(0, len(gtins), chunk_size):
        stop_i = start_i + chunk_size
        print("searching for gtins from", start_i, "to", stop_i, "...")
        find(gtins[start_i:stop_i], COUNTRY)
