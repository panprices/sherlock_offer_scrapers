from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_host: str
    db_user: str
    db_pass: str


class ShelfAnalyticsSettings(BaseDatabaseSettings):
    shelf_analytics_db_name: str


class PanpricesSettings(BaseDatabaseSettings):
    panprices_db_name: str


@lru_cache()
def get_shelf_analytics_settings():
    return ShelfAnalyticsSettings()


@lru_cache()
def get_panprices_settings():
    return PanpricesSettings()
