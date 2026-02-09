import psycopg2

from sherlock_offer_scrapers.persistence.db.settings import (
    get_shelf_analytics_settings,
)


def connect_to_shelf_analytics():
    settings = get_shelf_analytics_settings()

    conn = psycopg2.connect(
        host=settings.db_host,
        database=settings.shelf_analytics_db_name,
        user=settings.db_user,
        password=settings.db_pass,
    )
    return conn
