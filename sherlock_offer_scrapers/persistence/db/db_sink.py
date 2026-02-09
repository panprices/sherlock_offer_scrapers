from psycopg2.extras import execute_values

from sherlock_offer_scrapers.persistence.db.connector import connect_to_shelf_analytics
from sherlock_offer_scrapers.persistence.sink import (
    AbstractProductsSink,
    ProductSearchResult,
)


class DBProductsResultSink(AbstractProductsSink):
    def persist(self, products: list[ProductSearchResult]):
        conn = connect_to_shelf_analytics()
        cur = conn.cursor()

        execute_values(
            cur,
            """
            WITH data(gtin, sku, url) AS (
                VALUES %s
            )
            INSERT INTO b2c_offer_url (gtin, sku, offer_source, url)
            SELECT gtin, sku, 'google_shopping', url
            FROM data
            ON CONFLICT DO NOTHING
            """,
            ((p.gtin, p.sku, p.url) for p in products),
        )

        conn.commit()
        cur.close()
        conn.close()
