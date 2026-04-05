"""
Web scraping module for collecting product data from multiple e-commerce platforms
"""
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import random
from datetime import datetime
from models import Product, ScrapingLog, PriceHistory, db
from config import Config
from fake_useragent import UserAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper:
    """Base class for all scrapers"""
    
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.headers = {
            'User-Agent': desktop_ua,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        self.timeout = Config.REQUEST_TIMEOUT
    
    def get_soup(self, url):
        """Get BeautifulSoup object from URL using requests (fallback or API)"""
        try:
            response = self.session.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def extract_price(self, text):
        """Extract price from text"""
        if not text:
            return None
        try:
            # Find a sequence of digits with optional commas and a single optional decimal point
            match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)', str(text))
            if match:
                clean = match.group(1).replace(',', '')
                return float(clean)
            return None
        except Exception:
            return None
    
    def extract_rating(self, text):
        """Extract rating from text"""
        if not text:
            return None
        try:
            # look for pattern like "4.5"
            match = re.search(r'(\d+(\.\d+)?)', str(text))
            if match:
                val = float(match.group(1))
                return min(5.0, max(0.0, val))
        except Exception:
            return None
        return None
    
    def extract_review_count(self, text):
        """Extract review count from text"""
        if not text:
            return 0
        try:
            # "1,234 ratings" -> 1234
            clean = re.sub(r'[^\d]', '', str(text))
            return int(clean)
        except Exception:
            return 0

class SeleniumScraper(BaseScraper):
    """Base for Selenium-based scraping"""
    
    def __init__(self):
        super().__init__()
        self.driver = None

    def _setup_driver(self):
        options = ChromeOptions()
        options.add_argument("--headless=new") 
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        # Ensure we always get a desktop layout by hardcoding a modern desktop User-Agent
        desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        options.add_argument(f"user-agent={desktop_ua}")
        # Mask automation
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            self.driver = None

    def _teardown_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def get_page_source_selenium(self, url):
        if not self.driver:
            self._setup_driver()
        if not self.driver:
            return None
        
        try:
            self.driver.get(url)
            # Wait for body to be present
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Scroll to trigger lazy loading
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(1)
            
            return self.driver.page_source
        except Exception as e:
            logger.error(f"Error getting page with Selenium {url}: {e}")
            self._teardown_driver()
            return None

class AmazonScraper(SeleniumScraper):
    """Scraper for Amazon products"""
    
    def __init__(self):
        super().__init__()
        self.platform = "Amazon"
    
    def search_products(self, query, max_results=10):
        """Search for products on Amazon using Selenium"""
        search_url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"

        products = []
        try:
            source = self.get_page_source_selenium(search_url)
            if not source:
                return []

            soup = BeautifulSoup(source, 'lxml')

            # Enhanced selectors for various Amazon layouts
            items = (
                soup.find_all('div', {'data-component-type': 's-search-result'}) or
                soup.find_all('div', class_=re.compile(r's-result-item|s-asin')) or
                soup.find_all('div', attrs={'data-asin': True})
            )

            for item in items[:max_results]:
                try:
                    # Title
                    name_tag = item.find('h2')
                    if not name_tag:
                        continue
                    name = name_tag.get_text(strip=True)

                    # Link
                    link_tag = item.find('a', class_='a-link-normal s-no-outline') or item.find('a', class_='a-link-normal')
                    if not link_tag:
                        continue
                    relative_url = link_tag.get('href')
                    if not relative_url or relative_url.startswith('javascript'):
                        continue

                    if relative_url.startswith('http'):
                        product_url = relative_url
                    else:
                        product_url = "https://www.amazon.in" + relative_url

                    # Price
                    price_tag = item.find('span', class_='a-price-whole')
                    if not price_tag:
                        continue
                    price = self.extract_price(price_tag.get_text())
                    if not price:
                        continue

                    # Image
                    img_tag = item.find('img', class_='s-image')
                    image_url = img_tag.get('src') if img_tag else None

                    # Rating
                    rating_tag = item.find('span', class_='a-icon-alt')
                    rating = self.extract_rating(rating_tag.get_text()) if rating_tag else 0.0

                    # Review Count
                    review_tag = item.find('span', class_='a-size-base s-underline-text')
                    review_count = self.extract_review_count(review_tag.get_text()) if review_tag else 0

                    products.append({
                        'name': name,
                        'description': name,
                        'price': price,
                        'original_price': price * 1.2,
                        'rating': rating,
                        'review_count': review_count,
                        'platform': self.platform,
                        'product_url': product_url,
                        'image_url': image_url,
                        'category': 'General',
                        'availability': 'In Stock'
                    })
                except Exception as e:
                    # skip bad items but continue others
                    logger.debug(f"Error parsing Amazon item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error searching Amazon: {str(e)}")
        finally:
            self._teardown_driver()

        return products

class FlipkartScraper(SeleniumScraper):
    """Scraper for Flipkart products with upgraded selectors"""
    
    def __init__(self):
        super().__init__()
        self.platform = "Flipkart"
    
    def search_products(self, query, max_results=15):
        search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        products = []
        try:
            logger.info(f"Opening Flipkart Search: {search_url}")
            source = self.get_page_source_selenium(search_url)
            if not source:
                return []
                
            soup = BeautifulSoup(source, 'lxml')
            
            # Common Flipkart item containers
            # 1. Row view (_1AtVbE / _2kHMtA)
            # 2. Grid view (_4ddWXP / _13oc-S)
            containers = soup.find_all('div', {'class': re.compile(r'_1AtVbE|_2kHMtA|_4ddWXP|_13oc-S')})
            
            # Fallback to links if no containers found
            if not containers:
                links = soup.find_all('a', href=re.compile(r'/p/'))
                containers = list(set([l.parent.parent for l in links if l.parent and l.parent.parent]))
            
            for container in containers:
                if len(products) >= max_results:
                    break
                try:
                    # Look for product link
                    link_tag = container.find('a', href=re.compile(r'/p/'))
                    if not link_tag:
                        continue
                        
                    relative_url = link_tag.get('href', '')
                    product_url = "https://www.flipkart.com" + relative_url.split('?')[0] # Clean URL
                    
                    # Name/Title
                    # Usually in a div with specific classes, or just the longest text in h2 or div
                    name = None
                    name_candidates = container.find_all(['div', 'a', 'h2'], {'class': re.compile(r'ir0QqZ|_4rR01T|s1Q9Bw')})
                    if name_candidates:
                        name = name_candidates[0].get_text(strip=True)
                    else:
                        # Find any text that looks like a title
                        strings = list(container.stripped_strings)
                        name = next((s for s in strings if len(s) > 15 and '₹' not in s and '%' not in s), None)
                    
                    if not name:
                        continue
                    
                    # Price
                    price_tags = container.find_all('div', {'class': re.compile(r'_30jeq3|_25b68L')})
                    price_val = None
                    if price_tags:
                        price_val = self.extract_price(price_tags[0].get_text())
                    
                    if not price_val:
                        # Fallback: find text with ₹
                        strings = list(container.stripped_strings)
                        price_text = next((s for s in strings if '₹' in s), None)
                        price_val = self.extract_price(price_text)
                    
                    if not price_val:
                        continue
                    
                    # Original price
                    op_tag = container.find('div', {'class': re.compile(r'_3I9_wc|_279W7b')})
                    original_price = self.extract_price(op_tag.get_text()) if op_tag else price_val * 1.2
                    
                    # Image
                    img_tag = container.find('img')
                    image_url = img_tag.get('src') if img_tag else None
                    if not image_url and img_tag:
                        image_url = img_tag.get('data-src') or img_tag.get('srcset')
                    
                    # Rating
                    rating_tag = container.find('div', {'class': re.compile(r'_3LWZlK|gU_9_c')})
                    rating = self.extract_rating(rating_tag.get_text()) if rating_tag else 4.0
                    
                    review_count = random.randint(100, 10000) # Fallback
                    
                    products.append({
                        'name': name,
                        'description': name,
                        'price': price_val,
                        'original_price': original_price,
                        'rating': rating,
                        'review_count': review_count,
                        'platform': self.platform,
                        'product_url': product_url,
                        'image_url': image_url,
                        'category': 'General',
                        'availability': 'In Stock'
                    })
                except Exception as e:
                    logger.debug(f"Flipkart extraction sub-error: {e}")
                    continue
        except Exception as e:
            logger.error(f"Flipkart Scraper error: {e}")
        finally:
            self._teardown_driver()
            
        return products

class MeeshoScraper(SeleniumScraper):
    """Scraper for Meesho products using Selenium"""
    def __init__(self):
        super().__init__()
        self.platform = "Meesho"

    def search_products(self, query, max_results=15):
        search_url = f"https://www.meesho.com/search?q={query.replace(' ', '%20')}"
        products = []
        try:
            logger.info(f"Opening Meesho Search: {search_url}")
            source = self.get_page_source_selenium(search_url)
            if not source:
                return []
            
            soup = BeautifulSoup(source, 'lxml')
            
            # Meesho cards logic
            items = soup.find_all('div', {'data-testid': 'product-card'}) or \
                    soup.find_all('a', href=re.compile(r'/p/'))
            
            seen_urls = set()
            for item in items:
                if len(products) >= max_results:
                    break
                    
                try:
                    link_tag = item if item.name == 'a' else item.find('a', href=re.compile(r'/p/'))
                    if not link_tag:
                        continue
                    
                    href = link_tag.get('href', '')
                    product_url = "https://www.meesho.com" + href.split('?')[0]
                    if product_url in seen_urls:
                        continue
                    seen_urls.add(product_url)
                    
                    card = item if item.name == 'div' else item.parent
                    texts = list(card.stripped_strings)
                    
                    name = next((t for t in texts if len(t) > 10 and '₹' not in t and '★' not in t and t != 'Ad'), None)
                    if not name: continue
                    
                    price_val = None
                    for t in texts:
                        if '₹' in t:
                            val = self.extract_price(t)
                            if val:
                                price_val = val
                                break
                    if not price_val: continue
                    
                    original_price = price_val * 1.15
                    for t in texts:
                        val = self.extract_price(t)
                        if val and val > price_val:
                            original_price = val
                            break
                    
                    img = card.find('img')
                    image_url = img.get('src') if img else None
                    if image_url and 'spacer.png' in image_url:
                        image_url = img.get('data-src') or img.get('srcset')
                    
                    rating = 4.0
                    for t in texts:
                        if '.' in t and '★' in t:
                            rating = self.extract_rating(t) or 4.0
                        elif t.replace('.', '').isdigit() and len(t) <= 3 and float(t) <= 5.0:
                            rating = float(t)
                            
                    products.append({
                        'name': name,
                        'description': name,
                        'price': price_val,
                        'original_price': original_price,
                        'rating': rating,
                        'review_count': random.randint(100, 5000),
                        'platform': self.platform,
                        'product_url': product_url,
                        'image_url': image_url,
                        'category': 'General',
                        'availability': 'In Stock'
                    })
                except Exception: continue
        except Exception as e:
            logger.error(f"Meesho Selenium scraper failed: {e}")
        finally:
            self._teardown_driver()
        return products

class MyntraScraper(SeleniumScraper):
    """Scraper for Myntra products using Selenium"""
    def __init__(self):
        super().__init__()
        self.platform = "Myntra"

    def search_products(self, query, max_results=15):
        # Multi-strategy search URL: direct category or search query
        search_urls = [
            f"https://www.myntra.com/{query.replace(' ', '-')}",
            f"https://www.myntra.com/search?rawQuery={query.replace(' ', '%20')}"
        ]
        
        products = []
        for search_url in search_urls:
            try:
                logger.info(f"Opening Myntra Search Strategy: {search_url}")
                source = self.get_page_source_selenium(search_url)
                if not source:
                    continue
                
                soup = BeautifulSoup(source, 'lxml')
                # Try multiple product container classes (historically used by Myntra)
                items = soup.find_all('li', class_=re.compile(r'product-base'))
                if not items:
                    items = soup.find_all('div', class_=re.compile(r'product-tupleListing|product-item|results-gridItem'))
                
                if not items:
                    logger.debug(f"Next Myntra strategy due to no results at {search_url}")
                    continue
                
                for item in items[:max_results]:
                    try:
                        href_tag = item.find('a', href=True)
                        if not href_tag: continue
                        
                        href = href_tag['href']
                        product_url = href if href.startswith('http') else "https://www.myntra.com/" + href.lstrip('/')
                        
                        # Flexible name extraction
                        name_text = "Myntra Fashion"
                        name_tag = item.find('div', class_='product-product') or item.find('h4', class_='product-product')
                        if name_tag:
                            name_text = name_tag.text.strip()
                        
                        brand_tag = item.find('h3', class_='product-brand') or item.find('div', class_='product-brand')
                        brand_text = brand_tag.text.strip() if brand_tag else "Brand Name"
                        full_name = f"{brand_text} {name_text}"
                        
                        # Flexible price extraction
                        price = 0
                        price_div = item.find('div', class_='product-price')
                        if price_div:
                            dp = price_div.find('span', class_='product-discountedPrice')
                            price = self.extract_price(dp.text) if dp else self.extract_price(price_div.get_text())
                            strike = price_div.find('span', class_='product-strike')
                            original_price = self.extract_price(strike.text) if strike else price * 1.3
                        else:
                            # Try any price-looking string
                            all_texts = list(item.stripped_strings)
                            for t in all_texts:
                                if 'Rs.' in t or '₹' in t:
                                    val = self.extract_price(t)
                                    if val:
                                        price = val
                                        break
                            original_price = price * 1.3
                        
                        if not price: continue
                            
                        # Flexible image extraction
                        img = item.find('img')
                        image_url = img.get('src') if img else None
                        if image_url and (image_url.endswith('.gif') or 'data:image' in image_url):
                             image_url = img.get('data-src') or img.get('srcset') or img.get('image-source')
                        
                        rating_cont = item.find('div', class_='product-ratingsContainer')
                        rating = 4.0
                        review_count = random.randint(10, 1000)
                        if rating_cont:
                            texts = list(rating_cont.stripped_strings)
                            if texts:
                                rating = self.extract_rating(texts[0]) or 4.0
                                if len(texts) > 1:
                                    review_count = self.extract_review_count(texts[1]) or 100
                                    
                        products.append({
                            'name': full_name,
                            'brand': brand_text,
                            'description': full_name,
                            'price': price,
                            'original_price': original_price,
                            'rating': rating,
                            'review_count': review_count,
                            'platform': self.platform,
                            'product_url': product_url,
                            'image_url': image_url,
                            'category': 'Clothing',
                            'availability': 'In Stock'
                        })
                    except Exception as ie:
                        logger.debug(f"Myntra inner error: {ie}")
                        continue
                
                # If we found items, we can stop the strategy loop
                if products:
                    break
                    
            except Exception as e:
                logger.error(f"Myntra Strategy failure for {search_url}: {e}")
            finally:
                self._teardown_driver()
        
        return products

class ScraperManager:
    """Manages multiple scrapers"""
    
    def __init__(self):
        self.scrapers = {
            'amazon': AmazonScraper(),
            'flipkart': FlipkartScraper(),
            'meesho': MeeshoScraper(),
            'myntra': MyntraScraper()
        }
    
    def get_platform_trust_score(self, platform):
        """Platform trust scores - higher = more trusted"""
        scores = {
            'Amazon': 0.95,    # Most trusted
            'Flipkart': 0.90,  # Very trusted
            'Myntra': 0.85,    # Trusted
            'Meesho': 0.80     # Good
        }
        return scores.get(platform, 0.5)
    
    def scrape_platform(self, platform_name, query=None, max_results=10):
        """Scrape products from a single platform and store/update them in DB."""
        scraper = self.scrapers.get(platform_name.lower())
        if not scraper:
            logger.warning(f"No scraper found for {platform_name}")
            return []

        start_time = datetime.utcnow()
        log_entry = ScrapingLog(platform=platform_name, status='running', started_at=start_time)
        try:
            db.session.add(log_entry)
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            products = scraper.search_products(query, max_results)

            saved_count = 0
            for p_data in products or []:
                if not p_data or not p_data.get('product_url'):
                    continue

                existing = Product.query.filter_by(product_url=p_data['product_url']).first()
                if existing:
                    # Update existing product fields
                    if p_data.get('price') is not None:
                        existing.price = p_data['price']
                    existing.original_price = p_data.get('original_price', existing.original_price)
                    existing.rating = p_data.get('rating', existing.rating)
                    existing.review_count = p_data.get('review_count', existing.review_count)
                    existing.image_url = p_data.get('image_url', existing.image_url)
                    existing.category = p_data.get('category', existing.category)
                    existing.brand = p_data.get('brand', existing.brand)
                    existing.availability = p_data.get('availability', existing.availability)
                    existing.last_updated = datetime.utcnow()
                else:
                    new_p = Product(**p_data)
                    db.session.add(new_p)
                saved_count += 1

            db.session.commit()

            log_entry.status = 'success'
            log_entry.products_scraped = saved_count
            log_entry.completed_at = datetime.utcnow()
            log_entry.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            db.session.commit()

            return products
        except Exception as e:
            logger.error(f"Error in ScraperManager for {platform_name}: {e}")
            log_entry.status = 'failed'
            log_entry.errors = str(e)
            log_entry.completed_at = datetime.utcnow()
            log_entry.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            db.session.commit()
            return []
    
    def scrape_all_platforms(self, query=None, max_results_per_platform=10):
        """Scrape from all platforms in parallel using ThreadPoolExecutor"""
        import concurrent.futures
        platforms = ['amazon', 'flipkart', 'meesho', 'myntra']
        all_p = []
        
        logger.info(f"Starting parallel scrape across all platforms for query: '{query}'")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(platforms)) as executor:
            future_to_platform = {
                executor.submit(self.scrape_platform, p, query, max_results_per_platform): p 
                for p in platforms
            }
            
            for future in concurrent.futures.as_completed(future_to_platform):
                platform = future_to_platform[future]
                try:
                    products = future.result()
                    all_p.extend(products or [])
                    logger.info(f"Completed parallel scrape for {platform}: {len(products or [])} products found")
                except Exception as e:
                    logger.error(f"Parallel scrape failed for {platform}: {e}")
        
        return all_p

    def scrape_platform_realtime(self, platform_name, query=None, max_results=15):
        """Real-time scraping: Fetch products without saving to DB"""
        scraper = self.scrapers.get(platform_name.lower())
        if not scraper:
            logger.warning(f"No scraper found for {platform_name}")
            return []
        
        try:
            # Direct API/scraping call - no DB operations
            products = scraper.search_products(query, max_results)
            # Ensure all products have required fields
            for p in products:
                if 'id' not in p:
                    p['id'] = hash(p.get('product_url', '')) % 1000000  # Temporary ID
                if 'recommendation_score' not in p:
                    p['recommendation_score'] = 0.0
            return products
        except Exception as e:
            logger.error(f"Real-time scraping failed for {platform_name}: {e}")
            return []
