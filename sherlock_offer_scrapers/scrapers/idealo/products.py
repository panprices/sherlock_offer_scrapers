from typing import List, Dict, Optional

import logging
import time

from . import priceapi


def find_product_id(gtin: str) -> str:
    """Find Idealo's product_id based on a product gtin."""
    gtin_ids = find_product_ids([gtin])
    idealo_product_id = gtin_ids[gtin]
    return idealo_product_id


def find_product_ids(gtins: List[str]) -> Dict[str, str]:
    """Find multiple Idealo's product_id based on gtin."""
    gtin_ids = _get_product_ids(gtins)
    gtin_ids_cleaned = {}
    for gtin, product_id in gtin_ids.items():
        if product_id is None:
            gtin_ids_cleaned[gtin] = None
        else:
            gtin_ids_cleaned[gtin] = _clean_product_id(product_id)

    return gtin_ids_cleaned


def _clean_product_id(product_id: str) -> str:
    """Remove trailing non-digit character from product_id"""
    # 2149589_-17-50mm-f2-8-ex-dc-os-hsm-canon-sigma-foto -> 2149589
    end = 0
    while end < len(product_id) and product_id[end].isdigit():
        end += 1

    return product_id[:end]


def _get_product_ids(gtins: List[str]) -> Dict[str, str]:
    """Make request to PriceApi for product data on Idealo.

    Note that this method is blocking and will periodically call to check for
    the PriceAPI job status until the job is either finished or the maximum
    wait time has been reached.
    """
    job_id = priceapi.create_job(
        country="de",
        source="idealo",
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


def _parse_product_and_offers_result(job_result: dict) -> Dict[str, str]:
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
                products[gtin] = content.get("id")
            else:
                products[gtin] = None

        return products

    except Exception as ex:
        logging.error("Error when parsing PriceAPI result.")
        raise ex
