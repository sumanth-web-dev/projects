from playwright.sync_api import sync_playwright
import playwrite_fuctions






def run(playwright):
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    # Navigate to the URL
    page.goto("https://careers.wipro.com/job/Bengaluru-Data-Engineer-560035/1162782955/")
    playwrite_fuctions.findingfileds(page)
    
    # Perform actions on the page
    page.click("text=More information...")
    
    # Close the browser
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)