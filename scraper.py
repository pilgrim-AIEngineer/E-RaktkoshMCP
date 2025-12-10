import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext
from typing import List, Dict, Optional
from models import StockResult, BloodGroup

URL = "https://eraktkosh.mohfw.gov.in/BLDAHIMS/bloodbank/stockAvailability.cnt"

class ERaktKoshScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.playwright = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def get_hierarchy(self) -> Dict:
        """Scrapes all states and districts to build the hierarchy cache."""
        page = await self.context.new_page()
        try:
            await page.goto(URL, wait_until="networkidle")
            
            # Get States
            state_options = await page.locator("#stateCode option").all()
            states = {}
            for opt in state_options:
                val = await opt.get_attribute("value")
                text = await opt.inner_text()
                if val and val != "-1" and val != "-2" and "Select" not in text:
                    states[val] = text.strip()

            # Get Blood Groups
            bg_options = await page.locator("#bgType option").all()
            blood_groups = {}
            for opt in bg_options:
                val = await opt.get_attribute("value")
                text = await opt.inner_text()
                if val and val != "-1" and "Select" not in text:
                    blood_groups[val] = text.strip()

            # Get Blood Components
            bc_options = await page.locator("#bcType option").all()
            blood_components = {}
            for opt in bc_options:
                val = await opt.get_attribute("value")
                text = await opt.inner_text()
                if val and val != "-1" and "Select" not in text:
                    blood_components[val] = text.strip()

            districts_map = {}
            
            # Iterate states to get districts
            # Note: This can be slow, so we might want to limit or optimize.
            # For a real deployment, we'd persist this.
            for state_id, state_name in states.items():
                try:
                    print(f"Scraping districts for {state_name} ({state_id})...")
                    await page.select_option("#stateCode", value=state_id)
                    
                    # Wait for network/processing
                    await page.wait_for_timeout(2000)
                    
                    # Wait for district dropdown to populate
                    try:
                        await page.wait_for_function(
                            "document.getElementById('distList').options.length > 1",
                            timeout=5000
                        )
                    except:
                        print(f"Timeout waiting for districts for {state_name}")
                        # Continue to try scraping whatever is there or skip
                        pass

                    district_options = await page.locator("#distList option").all()
                    districts = {}
                    for opt in district_options:
                        val = await opt.get_attribute("value")
                        text = await opt.inner_text()
                        if val and val != "-1" and "Select" not in text:
                            districts[val] = text.strip()
                    
                    districts_map[state_id] = districts
                except Exception as e:
                    print(f"Error scraping {state_name}: {e}")
                    continue
                
            return {
                "states": states, 
                "districts": districts_map,
                "blood_groups": blood_groups,
                "blood_components": blood_components
            }
            
        finally:
            await page.close()

    async def fetch_stock(self, state_code: str, district_code: str, blood_group_code: str, blood_component_code: str) -> List[StockResult]:
        page = await self.context.new_page()
        results = []
        try:
            await page.goto(URL, wait_until="domcontentloaded")
            
            # Select State
            await page.select_option("#stateCode", value=state_code)
            await page.wait_for_function("document.getElementById('distList').options.length > 1")
            
            # Select District
            await page.select_option("#distList", value=district_code)
            
            # Select Blood Group
            await page.select_option("#bgType", value=blood_group_code)

            # Select Blood Component
            if blood_component_code:
                await page.select_option("#bcType", value=blood_component_code)
            
            # Search
            await page.click("#searchButton")
            
            # Wait for results
            # The results are usually in a table or a 'No records' message
            try:
                # Wait for either the grid or a no records message
                # Table ID is example-table
                # Increase timeout to 30s as the site can be slow
                # Wait for a row with at least 2 columns (to avoid Loading/No Data rows) OR the error message
                await page.wait_for_selector("#example-table tbody tr td:nth-child(2), #cphMst_lblMsg", timeout=30000)
            except:
                print("Timeout waiting for results.")
                return [] # Timeout or nothing found

            # Check for error/no records
            if await page.locator("#cphMst_lblMsg").is_visible():
                text = await page.locator("#cphMst_lblMsg").inner_text()
                if "not found" in text.lower():
                    return []

            # Parse Table and Pagination
            page_count = 0
            while True:
                # Table ID is example-table
                rows = await page.locator("#example-table tbody tr").all()
                
                # Skip header if needed, but tbody usually contains just data
                for row in rows:
                    cols = await row.locator("td").all()
                    if len(cols) >= 5:
                        # Columns: S.No, Blood Bank, Category, Availability, Last Updated, Type
                        name = await cols[1].inner_text()
                        category = await cols[2].inner_text()
                        availability = await cols[3].inner_text()
                        last_updated = await cols[4].inner_text()
                        
                        results.append(StockResult(
                            blood_bank_name=name.strip(),
                            category=category.strip(),
                            availability=availability.strip(),
                            last_updated=last_updated.strip()
                        ))
                
                page_count += 1
                if page_count >= 5:  # Safety limit
                    break

                # Check for Next button
                # The 'Next' button usually has id 'example-table_next' and class 'paginate_button next'
                # If disabled, it often has class 'disabled'
                next_btn = page.locator("#example-table_next")
                if await next_btn.is_visible():
                    classes = await next_btn.get_attribute("class")
                    if "disabled" not in classes:
                        await next_btn.click()
                        # Wait for table to update. 
                        # Simplest way is wait for a small timeout or network idle, 
                        # but ideally we'd wait for the processing class to disappear or table to reload.
                        # Given the site, a short sleep + wait for selector is often most robust.
                        await page.wait_for_timeout(1000) 
                        continue
                
                # If we're here, no next button or it's disabled
                break
            
            return results
            
        except Exception as e:
            print(f"Error scraping stock: {e}")
            return []
        finally:
            await page.close()
