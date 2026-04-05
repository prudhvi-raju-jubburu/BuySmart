import scraper
sm = scraper.ScraperManager()

f_laptops = sm.scrape_platform_realtime('flipkart', 'laptops')
print(f"Flipkart Laptops ({len(f_laptops)}):")
for p in f_laptops[:2]:
    print(f"- {p.get('name')[:40]} | Price: {p.get('price')} | Rating: {p.get('rating')}")

a_mobiles = sm.scrape_platform_realtime('amazon', 'mobiles')
print(f"\nAmazon Mobiles ({len(a_mobiles)}):")
for p in a_mobiles[:2]:
    print(f"- {p.get('name')[:40]} | Price: {p.get('price')} | Rating: {p.get('rating')}")
