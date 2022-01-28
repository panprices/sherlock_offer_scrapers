from google.cloud import storage
import structlog

logger = structlog.get_logger()


def dump_html(html, offer_source, gtin, country):
    filepath = f"offer_scrapers_html/{offer_source}/{gtin}.html"
    logger.warn(
        "taking a html dump",
        filepath=filepath,
        offer_source=offer_source,
        gtin=gtin,
        country=country,
    )

    storage_client = storage.Client("panprices")
    bucket = storage_client.get_bucket("panprices_logs")
    blob = bucket.blob(f"offer_scrapers_html/{offer_source}/{gtin}.html")

    blob.upload_from_string(html)
