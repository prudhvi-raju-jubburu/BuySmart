# Search Quality Guide — Category Validation & Exclusions

This document outlines the category validation synonym mapping, strict budget bounds, and global exclusion filters implemented in BuySmart's search engine.

## 1. Category Validation Synonym Mapping

To prevent query leakage (e.g. returning "laptop toy" for a "laptop" query), we map intents to canonical categories and their synonyms.

### Configured Category Synonyms
*   **laptop**: `laptop`, `notebook`, `ultrabook`, `macbook`, `chromebook`, `computer`, `laptops`
*   **mobile**: `mobile`, `phone`, `smartphone`, `iphone`, `mobiles`, `phones`
*   **shoes**: `shoe`, `shoes`, `sneaker`, `sneakers`, `running shoes`, `sports shoes`, `footwear`, `sandal`, `sandals`, `slippers`
*   **fashion**: `clothing`, `fashion`, `apparel`, `shirt`, `tshirt`, `t-shirt`, `pant`, `jeans`, `dress`, `saree`, `kurti`, `jacket`, `hoodie`, `sweater`, `wear`, `garment`, `garments`
*   **electronics**: `electronics`, `gadget`, `gadgets`, `headphone`, `headphones`, `earbud`, `earbuds`, `watch`, `smartwatch`, `tv`, `television`, `monitor`, `speaker`, `audio`

### Matching Rules
1.  **Strong Match:** The product category matches one of the target synonyms and does not contain any irrelevant terms.
2.  **Weak Match:** The product category is generic (e.g., "electronics") but the title contains one of the synonyms and does not contain irrelevant terms.
3.  **Strict Confidence Check:** If query intent confidence is above `0.80`, category validation is enforced strictly. If confidence is lower, it allows broader matching to prevent false negatives.

---

## 2. Global Exclusions Filter

Accessories, skins, guides, and other related items are globally filtered out from primary product searches using word-boundary regex checks.

### Active Exclusions List
The engine automatically removes items matching the following words (unless explicitly requested in the query):
`toy`, `toys`, `cover`, `covers`, `case`, `cases`, `skin`, `skins`, `sticker`, `stickers`, `book`, `books`, `guide`, `guides`, `manual`, `manuals`, `accessory`, `accessories`, `sleeve`, `sleeves`, `protector`, `protectors`, `charger`, `adapter`, `keyboard`, `mouse`, `mousepad`, `bag`, `backpack`, `stand`, `holder`, `screen guard`, `replacement`, `repair`, `parts`, `spare`, `refurbished`, `dummy`, `sample`, `miniature`

---

## 3. Strict Budget Enforcement

Price filters are enforced as hard constraints rather than scoring signals.
*   **Maximum price**: Discards any product exceeding the limit.
*   **Minimum price**: Discards any product below the limit.
*   **Price Validation**: Globally excludes all products with `price <= 0` or missing (`None`) pricing information.
