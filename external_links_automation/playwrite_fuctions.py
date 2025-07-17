

def findingfileds(page):
    # Example function to find fields on the page
    fields = page.query_selector_all("input, textarea")
    for field in fields:
        print(f"Found field: {field.get_attribute('name') or field.get_attribute('id')} - {field.get_attribute('type')} ")
    
    return fields


