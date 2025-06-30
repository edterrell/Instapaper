import selenium
print("Selenium is working in this environment!")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

driver = webdriver.Safari()
driver.get("https://www.instapaper.com/user/login")
wait = WebDriverWait(driver, 10)

# 1) Wait for *any* input to appear in the DOM
wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))

# 2) Grab them all and print their HTML and key attributes
all_inputs = driver.find_elements(By.TAG_NAME, "input")
for idx, inp in enumerate(all_inputs):
    print(f"Input #{idx}")
    print("  id:    ", inp.get_attribute("id"))
    print("  name:  ", inp.get_attribute("name"))
    print("  outer:", inp.get_attribute("outerHTML"))
    print("---")
