# Checks if gtin is a GTIN14 and if so, converts to GTIN13
def gtin_to_ean(gtin: str) -> str:
    if len(gtin) == 14:
        return gtin[1:14]
    if len(gtin) == 13:
        return gtin
    if len(gtin) < 13:
        return gtin.zfill(13)

    raise ValueError(f"cannot convert gtin to ean: {gtin} is not a valid gtin.")