

def findingfileds(page):
    # Example function to find fields on the page
    fields = page.query_selector_all("input, textarea")
    for field in fields:
        print(f"Found field: {field.get_attribute('name') or field.get_attribute('id')} - {field.get_attribute('type')} - {field.get_attribute('option')}")


    # buttons = page.query_selector_all("button")
    # for button in buttons:
    #     print(f"Found button: {button.get_attribute('name') or button.get_attribute('id')} - {button.text_content()}")

    # and_links = page.query_selector_all("a")
    # for link in and_links:
    #     print(f"Found link: {link.get_attribute('href')} - {link.text_content()}")
    
    return fields


