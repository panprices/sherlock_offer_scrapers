from sherlock_offer_scrapers.persistence.db.connector import connect_to_shelf_analytics
from sherlock_offer_scrapers.persistence.source import (
    AbstractProductsSource,
    SearchableProduct,
)


class DBProductsSource(AbstractProductsSource):
    def get_products(self) -> list[SearchableProduct]:
        conn = connect_to_shelf_analytics()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT bp.name, b.name as brand_name, bp.gtin, bp.sku 
            FROM brand_product bp 
                JOIN brand b ON bp.brand_id = b.id
            WHERE b.uses_shallow_data AND bp.active AND b.is_active
            UNION ALL 
            SELECT DISTINCT cp.name, cp.brand_name, cp.gtin, cp.sku
            FROM comparison_product cp 
                JOIN comparison_to_brand_product ctbp ON cp.id = ctbp.comparison_product_id
                JOIN brand_product bp ON ctbp.brand_product_id = bp.id
                JOIN brand b ON bp.brand_id = b.id
            -- By default all comparison products are active and use shallow data 
            -- (if the corresponding brand is active)
            WHERE b.uses_shallow_data AND bp.active AND b.is_active
        """
        )

        result = cur.fetchall()
        products = [
            SearchableProduct(name=row[0], brand_name=row[1], gtin=row[2], sku=row[3])
            for row in result
        ]

        cur.close()
        conn.close()
        return products
