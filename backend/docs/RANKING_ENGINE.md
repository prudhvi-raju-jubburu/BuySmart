# Ranking Engine — Weighted Scoring & Diversity

This document explains the unified product ranking formula, brand mismatch penalties, results quality threshold, and greedy diversity decay selection used in BuySmart.

## 1. Unified Weighted Scoring Formula

Search results and recommendation feeds are ranked using the same unified scoring function, ensuring consistent quality.

$$\text{Final Score} = 0.40 \times \text{Relevance} + 0.20 \times \text{Quality} + 0.15 \times \text{Preference} + 0.10 \times \text{Popularity} + 0.10 \times \text{Specs} + 0.05 \times \text{Freshness}$$

### Component Breakdown
1.  **Relevance (40%):** Keyword matches, TF-IDF cosine similarity, and category alignment.
2.  **Quality (20%):** Weighted product metadata quality:
    *   35% Rating (`rating / 5.0`)
    *   20% Reviews (`review_count / max_reviews`)
    *   20% Platform Trust (Amazon = 0.95, Myntra = 0.92, Flipkart = 0.90, Meesho = 0.75)
    *   15% Brand Quality (Bonus if brand is recognized)
    *   10% Completeness (Check for image, rating, reviews, category, price)
3.  **Preference Match (15%):** Alignment with user category, brand, platform, and price history.
4.  **Popularity (10%):** Normalized interaction volume and review count.
5.  **Specification Match (10%):** Purpose-specific hardware spec matching (e.g. 16GB RAM for coding).
6.  **Freshness (5%):** Boost for recently created/updated items (linearly decays from 30 days to 180 days).

---

## 2. Scaled Brand Mismatch Penalty

To avoid hard brand exclusions that might filter out excellent alternatives, relevance is adjusted dynamically:
*   **Brand Match:** `1.0` multiplier (full relevance).
*   **Unspecified/Unknown Brand:** `0.7` multiplier.
*   **Brand Mismatch:** `0.4` multiplier (`0.7` in relaxed pass).

---

## 3. Result Quality Threshold

To prevent low-quality, irrelevant filler items from appearing at the bottom of lists, the engine enforces a hard quality threshold:
*   **`MIN_ACCEPTABLE_SCORE = 0.35`**
*   Any product with a final score below `0.35` is discarded from search and recommendation payloads.

---

## 4. Recommendation Diversity (Greedy Decay)

To avoid brand or category clustering, we apply a decay multiplier to remaining candidates after selecting each result:
*   **`same_brand *= 0.90`**
*   **`same_category *= 0.95`**
*   This distributes brands and categories evenly throughout the top listings.
