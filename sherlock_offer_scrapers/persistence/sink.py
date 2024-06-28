import abc

from sherlock_offer_scrapers.persistence.base import BaseProduct


class ProductSearchResult(BaseProduct):
    url: str  # more like an id but named to keep consistency


class AbstractProductsSink(abc.ABC):
    @abc.abstractmethod
    def persist(self, products: list[ProductSearchResult]):
        pass
