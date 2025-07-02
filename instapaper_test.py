#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
instapaper_test.py

Brief: 
   This program queries Instapaper and collects a list of the 
   web pages saved. In order, for the program to log in with your credentials, 
   safely store them locally in:
   '~/bin/passwords'. The files must be named instapaper_password.txt and instapaper_username.txt

Usage:
    $ python instapaper_test.py OR $ ./instapaper_test.py

Author: Ed Terrell
Created: 2025-07-01
Updated: 2025-07-01
Version: 0.1.0
"""

# Standard library and third party imports
#import os

import pandas as pd
from dateutil import parser
from urllib.parse import urlparse
from bs4 import BeautifulSoup as bs

import time
import sys
print (sys.executable)
#breakpoint()

# Program
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

# Get username and password and store them in variables
from pathlib import Path
base_path = Path.home() / "bin" / "passwords"
with open(base_path / "instapaper_username.txt", "r") as f:
    username = f.read().strip()
with open(base_path / "instapaper_password.txt", "r") as f:
    password = f.read().strip()

#print(username, password)  # Just for testing

# Start Safari (or Chrome)
driver = webdriver.Safari()
driver.get("https://www.instapaper.com/user/login")

# create a 10‑second WebDriverWait
wait = WebDriverWait(driver, 10)

USERNAME_LOCATOR = (By.ID, "username") 
PASSWORD_LOCATOR = (By.ID, "password")

def wait_click_and_type(driver, locator, text, timeout=10):
    """
    Waits for an element to be present, visible, enabled, and clickable,
    scrolls it into view, retries click via JS or ActionChains,
    clears it, and sends text.
    """
    wait = WebDriverWait(driver, timeout)
    # 1) Wait for presence
    el = wait.until(EC.presence_of_element_located(locator))
    # 2) Optionally wait for it to be visible
    el = wait.until(EC.visibility_of(el))
    # 3) Optionally wait for it to be clickable
    el = wait.until(EC.element_to_be_clickable(locator))
    # 4) Scroll into view
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
    # 5) Click / focus
    try:
        el.click()
    except Exception:
        # JS fallback
        driver.execute_script("arguments[0].click();", el)
    # 6) ActionChains fallback (if JS click still fails)
    try:
        ActionChains(driver).move_to_element(el).click().perform()
    except Exception:
        pass
    # 7) Clear and type
    el.clear()
    el.send_keys(text)
    return el

# Fill and submit
wait_click_and_type(driver, (By.ID, "username"), username)
pw_field = wait_click_and_type(driver, (By.ID, "password"), password)
pw_field.send_keys(Keys.RETURN)

# Wait for something that only appears when logged in
wait.until(EC.presence_of_element_located((By.ID, "main_container")))

def parse_url(url):
    all_clean_links = []
    try:
        # Go to archive and grab links
        driver.get(url)
        # Instead of time.sleep(2) we use WebDriverWait
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'article_text_content'))
        )
        html = driver.page_source
        
        # Now we are in the beautiful soup world
        soup = bs(html, "html.parser")
        links = [a['href'] for a in soup.find_all('a', href=True)]  
        clean_links = [link for link in links if link.startswith("http")]
        all_clean_links.extend(clean_links)
        
        # Check for "next page" link
        next_soup = None
        next_link_tag = soup.find('a', class_='paginate_older')
        if next_link_tag:
            next_url = next_link_tag['href']
            #if not next_url.startswith("http"):
                #next_url = "https://www.instapaper.com" + next_url
                
            # Follow next page and repeat
            driver.get(next_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'article_text_content'))
            )
            next_html = driver.page_source
            next_soup = bs(next_html, "html.parser")
            next_links = [a['href'] for a in next_soup.find_all('a', href=True)]
            clean_next_links = [link for link in next_links if link.startswith("http")]
            all_clean_links.extend(clean_next_links)      
                            
    except TimeoutException:
        print("Timeout while loading archive page.")
    
    
    return all_clean_links, soup, next_soup

# assign the function's return variables to be used out of scope
url = "https://www.instapaper.com/archive"
all_clean_links, soup, next_soup = parse_url(url)   

driver.quit()
# print(len(all_clean_links))


# Store clickable_links.html for web viewing 
# Filter out links containing "instapaper" or "ads/click"
urls = [
    url for url in all_clean_links
    if 'instapaper' not in url and 'ads/click' not in url
]

# Create an HTML file with clickable links
with open("clickable_links.html", "w") as outfile:
    outfile.write("<!DOCTYPE html>\n<html>\n<body>\n<h2>Clickable Links</h2>\n<ul>\n")
    for url in urls:
        outfile.write(f'  <li><a href="{url}" target="_blank">{url}</a></li>\n')
    outfile.write("</ul>\n</body>\n</html>")

    # Create titles,previews,urls 
def extract_article_data(soup):
    titles = [title.text.strip().replace('\xa0', ' ') for title in soup.find_all('a', class_='article_title')]
    previews = [prev.text.strip().replace('\xa0', ' ') for prev in soup.find_all('div', class_='article_preview')]
    url_links = [link['href'] for link in soup.find_all('a', class_='js_domain_linkout')]
    return titles, previews, url_links

titles, previews, url_links = extract_article_data(soup)

if next_soup:
    titles2, previews2, url_links2 = extract_article_data(next_soup)

titles = titles + titles2
previews = previews + previews2
url_links = url_links + url_links2

df = pd.DataFrame({'Title':titles,'Link':url_links,'Preview':previews})
df.tail()

# Pandas to csv file
df.to_csv('instapaper_articles.csv',index=False)

# Store article_listing.html file for web viewing 
# Save df_display for later use
df_display = df.copy()

def shorten_url(url):
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    return f'<a href="{url}" target="_blank">{domain}</a>'

df["Link"] = df["Link"].apply(shorten_url)

# Export to HTML
html_table = df.to_html(escape=False, index=False)

html_full = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Exported Table</title>
</head>
<body>
{html_table}
</body>
</html>
"""

with open("article_listing.html", "w", encoding="utf-8") as f:
    f.write(html_full)
