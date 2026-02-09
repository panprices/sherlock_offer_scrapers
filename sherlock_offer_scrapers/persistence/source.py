import abc

from sherlock_offer_scrapers.persistence.base import BaseProduct


class SearchableProduct(BaseProduct):
    name: str
    brand_name: str


class AbstractProductsSource(abc.ABC):
    @abc.abstractmethod
    def get_products(self) -> list[SearchableProduct]:
        pass
