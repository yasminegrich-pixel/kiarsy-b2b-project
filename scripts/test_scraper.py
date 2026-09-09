import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Kiarsy Cultural Affinity Engine)"}

def clean(soup):
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ", strip=True).split())

def try_fetch(url, timeout=15):
    r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    if r.status_code == 200:
        return r.text
    return None

def scrape(url, timeout=15):
    # 1) Try the exact URL
    html = try_fetch(url, timeout)
    if html:
        return clean(BeautifulSoup(html, "html.parser")), url

    # 2) Fall back: site root + common about-page guesses
    from urllib.parse import urlparse
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    guesses = [base + p for p in ["/", "/about", "/about-us", "/who-we-are", "/en/about-us", "/fr/a-propos"]]
    for g in guesses:
        html = try_fetch(g, timeout)
        if html and len(clean(BeautifulSoup(html, "html.parser"))) > 300:
            return clean(BeautifulSoup(html, "html.parser")), g
    raise Exception(f"Could not fetch {url} or any fallback page")

if __name__ == "__main__":
    for url in [
        "https://www.totalenergies.com/tn/en/about-us",
        "https://www.ooredoo.tn/",
    ]:
        print(f"\n=== {url} ===")
        try:
            text, used = scrape(url)
            print(f"✅ Got {len(text)} chars from: {used}")
            print("   Preview:", text[:300].replace("\n", " "))
        except Exception as e:
            print(f"❌ Failed: {e}")
