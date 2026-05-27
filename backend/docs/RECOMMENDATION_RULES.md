# Recommendation Rules — Specifications & Explainability

This document details the rule-based specification boosts, purpose mapping, and explainable matching reason metadata implemented in BuySmart.

## 1. Query Purpose Mapping

Natural language queries are scanned for keywords to detect one of eight search purposes.

*   **gaming:** `gaming`, `gamer`, `play`, `graphics`, `gpu`
*   **coding:** `coding`, `program`, `developer`, `software`, `vscode`, `python`, `java`, `c++`
*   **machine_learning:** `machine learning`, `ml`, `ai`, `data science`, `neural`, `deep learning`, `nlp`
*   **office:** `office`, `work`, `business`, `excel`, `document`, `productivity`, `meeting`, `zoom`
*   **student:** `student`, `college`, `school`, `study`, `studies`, `education`, `learning`
*   **video_editing:** `video editing`, `premier`, `editor`, `rendering`, `da vinci`, `after effects`
*   **graphic_design:** `graphic design`, `photoshop`, `illustrator`, `designing`, `canva`, `creator`
*   **business:** `business`, `professional`, `enterprise`, `corporate`, `travel`, `thin`, `lightweight`

---

## 2. Specification Match Boosts

Based on the detected purpose, products receive spec boosts (up to `1.0`) if they match hardware indicators in the description/title:
*   **16GB+ RAM:** Checks for `16GB`, `32GB`, `64GB` RAM.
*   **SSD Storage:** Checks for `SSD`, `NVMe`, `solid state`.
*   **Strong CPU:** Checks for `i5`, `i7`, `i9`, `Ryzen 5/7/9`, `M1/M2/M3`.
*   **Dedicated GPU:** Checks for `RTX`, `GTX`, `Nvidia`, `dedicated graphics`, `Radeon RX`.

### Spec Boost Allocation Matrix
*   **gaming:** GPU (`0.5`), RAM (`0.3`), CPU (`0.2`)
*   **coding:** RAM (`0.4`), SSD (`0.3`), CPU (`0.3`)
*   **machine_learning:** GPU (`0.4`), RAM (`0.3`), CPU (`0.2`), SSD (`0.1`)
*   **office / business:** SSD (`0.5`), CPU (`0.3`), Brand Apple/Dell/HP/Lenovo (`0.2`)
*   **student:** Price < 40000 (`0.5`), CPU/SSD (`0.5`)
*   **video_editing / graphic_design:** RAM (`0.4`), GPU (`0.3`), CPU (`0.3`)
*   **default:** RAM (`0.4`), SSD (`0.3`), CPU (`0.3`)

---

## 3. Explainable Matching Reasons

Every product recommended or returned contains a clear matching explanation in the `"reason"` field:
*   *Gaming query:* `"Optimized for gaming"`
*   *Brand match:* `"Matches your preferred ASUS brand"`
*   *Budget match:* `"Fits within your ₹60,000 budget"`
*   *Combined example:* `"Optimized for coding & Fits within your ₹60,000 budget"`
