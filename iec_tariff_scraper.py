import json
from datetime import datetime
import logging
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import os

# Constants
URL = "https://www.iec.co.il/content/tariffs/contentpages/homeelectricitytariff"
TAX_RATE = 0.18  # VAT rate (18%)
WAIT_TIMEOUT = 30  # seconds
PAGE_LOAD_WAIT = 15  # seconds
OUTPUT_DIR = "tariff_data"

# Table identifiers
TABLE_TYPES = {
    "base_rate": "תשלום לקוט\"ש",
    "fixed_distribution": "תשלום קבוע - חלוקה",
    "fixed_supply": "תשלום קבוע - אספקה"
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IECTariffScraper:
    def __init__(self):
        """Initialize the IEC tariff scraper."""
        self.url = URL
        self.tariffs: Dict = {}
        self.tax_rate = TAX_RATE
        self.driver = None
        self._ensure_output_directory()

    def _ensure_output_directory(self) -> None:
        """Ensure the output directory exists."""
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

    def setup_driver(self) -> None:
        """Set up the Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            self._setup_anti_detection()
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    def _setup_anti_detection(self) -> None:
        """Set up anti-detection measures."""
        try:
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception as e:
            logger.warning(f"Anti-detection setup failed: {e}")

    def _wait_for_element(self, by: By, value: str, timeout: int = WAIT_TIMEOUT) -> Optional[webdriver.remote.webelement.WebElement]:
        """Wait for an element to be present and return it."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {value}")
            return None

    def fetch_page(self) -> bool:
        """Navigate to the IEC tariff page and wait for content to load."""
        try:
            logger.info("Navigating to IEC tariff page")
            self.driver.get(self.url)
            
            # Wait for body to load
            if not self._wait_for_element(By.TAG_NAME, "body"):
                return False
            
            # Additional wait for dynamic content
            self.driver.implicitly_wait(PAGE_LOAD_WAIT)
            
            # Verify content loaded
            content = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'תעריף')]")
            if not content:
                logger.error("No tariff content found on page")
                return False
                
            logger.info(f"Found {len(content)} tariff elements")
            return True
            
        except Exception as e:
            logger.error(f"Error loading page: {e}")
            return False

    def _extract_table_data(self, table: webdriver.remote.webelement.WebElement) -> Dict:
        """Extract data from a single table."""
        data = {}
        try:
            header = table.find_element(By.CSS_SELECTOR, "th strong").text.strip()
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 3:
                    customer_type = cells[0].text.strip()
                    base_price = float(cells[1].text.strip())
                    price_with_tax = float(cells[2].text.strip())
                    
                    data[customer_type] = {
                        'base_price': base_price,
                        'price_with_tax': price_with_tax,
                        'tax_amount': round(price_with_tax - base_price, 2)
                    }
            
            return data
        except Exception as e:
            logger.warning(f"Error extracting table data: {e}")
            return {}

    def extract_tariffs(self) -> bool:
        """Extract tariff information from the page."""
        try:
            tables = self.driver.find_elements(By.CSS_SELECTOR, "table.content-table")
            if not tables:
                logger.error("No tables found on page")
                return False

            for table in tables:
                try:
                    header = table.find_element(By.CSS_SELECTOR, "th strong").text.strip()
                    
                    if TABLE_TYPES["base_rate"] in header:
                        data = self._extract_table_data(table)
                        if data:
                            self.tariffs['base_rate'] = next(iter(data.values()))
                    
                    elif TABLE_TYPES["fixed_distribution"] in header:
                        self.tariffs['fixed_distribution'] = self._extract_table_data(table)
                    
                    elif TABLE_TYPES["fixed_supply"] in header:
                        self.tariffs['fixed_supply'] = self._extract_table_data(table)
                
                except Exception as e:
                    logger.warning(f"Error processing table: {e}")
                    continue

            return bool(self.tariffs)
            
        except Exception as e:
            logger.error(f"Error extracting tariffs: {e}")
            return False

    def save_results(self) -> bool:
        """Save the extracted tariff information to a JSON file."""
        if not self.tariffs:
            logger.error("No tariffs to save")
            return False

        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'tax_rate': self.tax_rate,
                'tariffs': self.tariffs,
                'metadata': {
                    'source_url': self.url,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(OUTPUT_DIR, f'iec_tariffs_{timestamp}.json')
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Results saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return False

    def run(self) -> bool:
        """Run the complete scraping process."""
        success = False
        try:
            logger.info("Starting IEC tariff scraping process")
            self.setup_driver()
            
            if not self.fetch_page():
                return False
                
            if not self.extract_tariffs():
                return False
                
            success = self.save_results()
            
        except Exception as e:
            logger.error(f"Error in scraping process: {e}")
            success = False
            
        finally:
            if self.driver:
                self.driver.quit()
                
        return success

def main():
    scraper = IECTariffScraper()
    if scraper.run():
        logger.info("Scraping completed successfully")
    else:
        logger.error("Scraping failed")

if __name__ == "__main__":
    main() 