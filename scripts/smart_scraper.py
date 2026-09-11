import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (Kiarsy Cultural Affinity Engine)"}
TARGET_KEYWORDS = ['a-propos', 'qui-sommes-nous', 'rse', 'csr', 'engagement', 'valeurs', 'about', 'mission', 'vision']

def clean_text(soup):
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ", strip=True).split())

def fetch_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            return r.text
    except:
        pass
    return None

def smart_scrape(start_url):
    print(f"🕵️ Step 1: Landing on homepage {start_url}...")
    html = fetch_page(start_url)
    if not html:
        return "Failed to load homepage."

    soup = BeautifulSoup(html, "html.parser")
    full_text = clean_text(soup)
    
    # Hunt for deep links
    print("🔍 Step 2: Hunting for 'About', 'RSE', or 'Values' pages...")
    links = soup.find_all('a', href=True)
    target_urls = set()
    
    for link in links:
        href = link['href'].lower()
        if any(kw in href for kw in TARGET_KEYWORDS):
            # Convert relative URLs to absolute
            full_url = urljoin(start_url, link['href'])
            target_urls.add(full_url)
            
    # Scrape the top 3 most relevant internal pages
    scraped_pages = [start_url]
    for url in list(target_urls)[:3]:
        if url not in scraped_pages:
            print(f"   -> Found deep page: {url}")
            sub_html = fetch_page(url)
            if sub_html:
                sub_soup = BeautifulSoup(sub_html, "html.parser")
                full_text += "\n\n" + clean_text(sub_soup)
                scraped_pages.append(url)
            time.sleep(1) # Be polite
            
    print(f"\n✅ Scraped {len(scraped_pages)} pages total. Length: {len(full_text)} characters.")
    return full_text

if __name__ == "__main__":
    url = "https://www.soprahr.com/"
    text = smart_scrape(url)
    print("\n--- PREVIEW (First 800 chars) ---")
    print(text[:800])
