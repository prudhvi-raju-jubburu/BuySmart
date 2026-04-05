import scraper
from recommender import ProductRecommender

sm = scraper.ScraperManager()

print("--- Testing Flipkart Laptops ---")
f_laptops = sm.scrape_platform_realtime('flipkart', 'laptops')
print(f"Count: {len(f_laptops)}")
for p in f_laptops[:3]:
    print(f"- {p.get('name')[:40]} | {p.get('price')} | {p.get('rating')}")

print("\n--- Testing Amazon Mobiles ---")
a_mobiles = sm.scrape_platform_realtime('amazon', 'mobiles')
print(f"Count: {len(a_mobiles)}")
for p in a_mobiles[:3]:
    print(f"- {p.get('name')[:40]} | {p.get('price')} | {p.get('rating')}")
