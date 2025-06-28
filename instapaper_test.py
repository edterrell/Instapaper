import pandas as pd
from dateutil import parser
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup as bs

import time
#import sys
#sys.executable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
username_field = driver.find_element(By.ID, "username")
password_field = driver.find_element(By.ID, "password")

# Fill in login form
username_field.send_keys(username)
time.sleep(1)
password_field.send_keys(password)
password_field.send_keys(Keys.RETURN)

# Wait for redirect
time.sleep(3)

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
