import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from datetime import datetime
import schedule

def get_electricity_plans():
    """Get electricity plans from the website."""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        url = "https://www.kamaze.co.il/Compare/52/electrical-power#ComparisonPanel"
        driver.get(url)
        time.sleep(10)
        
        driver.execute_script("document.getElementById('ComparisonPanel').scrollIntoView(true);")
        time.sleep(5)
        
        try:
            comparison_panel = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "ComparisonPanel"))
            )
        except TimeoutException:
            return []
            
        plans = []
        selectors_to_try = [
            ".compare-plans-container .plan-item",
            "#ComparisonPanel .comparison-item",
            ".comparison-panel .plan",
            "article.topitem"
        ]
        
        for selector in selectors_to_try:
            plan_elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if plan_elements:
                break
        else:
            return []
            
        for plan_element in plan_elements:
            try:
                plan = {
                    'company': '',
                    'name': '',
                    'description': '',
                    'discount': '',
                    'features': [],
                    'additional_details': [],
                    'contact_button_text': ''
                }
                
                # Company name
                for company_selector in [".company-logo img", ".company-name", ".topitem-logo img"]:
                    try:
                        company_element = plan_element.find_element(By.CSS_SELECTOR, company_selector)
                        plan['company'] = company_element.get_attribute('alt') or company_element.text.strip()
                        if plan['company']:
                            break
                    except NoSuchElementException:
                        continue
                
                # Plan name
                for name_selector in [".plan-title", ".plan-name", ".topitem-caption-heading"]:
                    try:
                        name_element = plan_element.find_element(By.CSS_SELECTOR, name_selector)
                        plan['name'] = name_element.text.strip()
                        if plan['name']:
                            break
                    except NoSuchElementException:
                        continue
                
                # Description
                for desc_selector in [".plan-description", ".topitem-caption-desc"]:
                    try:
                        desc_element = plan_element.find_element(By.CSS_SELECTOR, desc_selector)
                        plan['description'] = desc_element.text.strip()
                        if plan['description']:
                            break
                    except NoSuchElementException:
                        continue
                
                # Discount
                for discount_selector in [".discount-amount", ".topitem-pricebox-price"]:
                    try:
                        discount_element = plan_element.find_element(By.CSS_SELECTOR, discount_selector)
                        plan['discount'] = discount_element.text.strip().replace('\n', '')
                        if plan['discount']:
                            break
                    except NoSuchElementException:
                        continue
                
                # Features
                for features_selector in [".plan-features li", ".topitem-feature"]:
                    try:
                        feature_elements = plan_element.find_elements(By.CSS_SELECTOR, features_selector)
                        plan['features'] = [f.text.strip() for f in feature_elements if f.text.strip()]
                        if plan['features']:
                            break
                    except NoSuchElementException:
                        continue
                
                # Additional details
                for details_selector in [".plan-details li", ".topitem-details-panel li"]:
                    try:
                        detail_elements = plan_element.find_elements(By.CSS_SELECTOR, details_selector)
                        plan['additional_details'] = [d.text.strip() for d in detail_elements if d.text.strip()]
                        if plan['additional_details']:
                            break
                    except NoSuchElementException:
                        continue
                
                # Contact button
                for button_selector in [".contact-button", ".btn-main"]:
                    try:
                        button = plan_element.find_element(By.CSS_SELECTOR, button_selector)
                        plan['contact_button_text'] = button.text.strip()
                        if plan['contact_button_text']:
                            break
                    except NoSuchElementException:
                        continue
                
                plans.append(plan)
                
            except Exception:
                continue
        
        # Save results to JSON file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"electricity_plans_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(plans, f, ensure_ascii=False, indent=2)
        
        return plans
        
    except Exception:
        return []
        
    finally:
        try:
            driver.quit()
        except:
            pass

def run_scraper():
    """Run the scraper and print the number of plans found."""
    plans = get_electricity_plans()
    print(f"Found {len(plans)} plans at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    # Schedule the scraper to run daily at 8:00 AM
    schedule.every().day.at("08:00").do(run_scraper)
    
    # Run immediately on startup
    run_scraper()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60) 