from typing import Optional

from pydantic import BaseModel, model_validator


class BaseProduct(BaseModel):
    gtin: Optional[str]
    sku: Optional[str]

    @model_validator(mode="after")
    def ensure_unique_identifier(self):
        if not self.sku and not self.gtin:
            raise ValueError("Either sku or gtin must be provided")
        return self
