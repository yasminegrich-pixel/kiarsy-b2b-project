"""
Kiarsy Dossier Builder v2.5
Smarter filtering: removes duplicates + low-value pages.
No Wikipedia.
"""

import requests
import time
import hashlib
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
import trafilatura
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
}

IMPORTANT_KEYWORDS = [
    "about", "a-propos", "qui-sommes", "qui-sommes-nous", "notre-groupe", "the-group",
    "company", "groupe", "presentation", "profile", "who-we-are",
    "mission", "vision", "valeurs", "values", "engagement", "rse", "csr",
    "sustainability", "durabilite", "responsable", "impact", "innovation",
    "strategy", "strategie", "expertise", "solutions", "activities", "activites"
]

COMMON_PATHS = [
    "/about", "/about-us", "/a-propos", "/qui-sommes-nous", "/notre-groupe",
    "/company", "/groupe", "/en/about", "/fr/a-propos", "/en/company",
    "/presentation", "/group", "/our-company", "/who-we-are"
]

# Pages we want to reject
LOW_VALUE_SIGNALS = [
    "accessibilité", "accessibility", "cookie", "confidentialité", "privacy policy",
    "mentions légales", "legal notice", "conditions générales", "terms of use",
    "politique de confidentialité", "gdpr", "rgpd", "nous nous engageons à rendre"
]

# Words that indicate useful business content
BUSINESS_SIGNALS = [
    "groupe", "company", "entreprise", "solutions", "innovation", "expertise",
    "clients", "products", "produits", "technologie", "automobile", "électronique",
    "systèmes", "mission", "vision", "stratégie", "rse", "développement", "marché",
    "filiale", "international", "ingénieurs", "recherche", "production"
]


def clean_with_trafilatura(html: str, url: str = None) -> str:
    if not html:
        return ""
    text = trafilatura.extract(html, include_comments=False, include_tables=False, no_fallback=False, url=url)
    if not text or len(text) < 150:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ", strip=True).split())
    return text.strip() if text else ""


def is_low_value(text: str) -> bool:
    text_lower = text.lower()
    low_hits = sum(1 for s in LOW_VALUE_SIGNALS if s in text_lower)
    business_hits = sum(1 for s in BUSINESS_SIGNALS if s in text_lower)

    if low_hits >= 2 and business_hits < 3:
        return True
    if "accessibilité" in text_lower and business_hits < 4:
        return True
    return False


def text_fingerprint(text: str) -> str:
    """Simple fingerprint to detect near-duplicates."""
    normalized = " ".join(text.lower().split()[:120])
    return hashlib.md5(normalized.encode()).hexdigest()


def fetch_simple(url: str, timeout: int = 12) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
            return r.text
    except Exception:
        pass
    return None


def fetch_with_playwright(url: str, wait_seconds: int = 4, retries: int = 1) -> str | None:
    """More resilient browser fetch with retry."""
    for attempt in range(retries + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    user_agent=HEADERS["User-Agent"],
                    locale="fr-FR"
                )
                page = context.new_page()
                page.set_default_timeout(30000)

                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(wait_seconds)

                # Try to scroll a bit to trigger lazy loading
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(1.5)

                html = page.content()
                browser.close()

                if html and len(html) > 1500:
                    return html
        except Exception as e:
            print(f"   Playwright attempt {attempt+1} failed on {url}: {str(e)[:80]}")
            time.sleep(2)

    return None

def fetch(url: str) -> str | None:
    """Try simple request first, then Playwright with retry."""
    html = fetch_simple(url)
    if html and len(html) > 3000:
        return html

    # Fallback to Playwright
    return fetch_with_playwright(url)

def get_website_content(start_url: str) -> list[str]:
    texts = []
    fingerprints = set()
    visited = set()
    base = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"

    def try_add(html, url):
        if not html or url in visited:
            return
        text = clean_with_trafilatura(html, url)
        if len(text) < 300:
            return
        if is_low_value(text):
            print(f"   ✗ Rejected (low value): {url}")
            return

        fp = text_fingerprint(text)
        if fp in fingerprints:
            print(f"   ✗ Rejected (duplicate): {url}")
            return

        texts.append(text)
        fingerprints.add(fp)
        visited.add(url)
        print(f"   ✓ Kept: {url} ({len(text)} chars)")

    print("   → Homepage...")
    html = fetch(start_url)
    try_add(html, start_url)

    # Common paths
    for path in COMMON_PATHS:
        url = urljoin(base, path)
        if url not in visited:
            h = fetch(url)
            try_add(h, url)
            time.sleep(0.6)

    # Discover more links from homepage
    if html:
        soup = BeautifulSoup(html, "html.parser")
        candidates = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            full = urljoin(start_url, a["href"])
            if any(k in href for k in IMPORTANT_KEYWORDS):
                if urlparse(full).netloc == urlparse(start_url).netloc:
                    candidates.add(full)

        for url in list(candidates)[:6]:
            if url not in visited:
                h = fetch(url)
                try_add(h, url)
                time.sleep(0.8)

    return texts


def get_news(company_name: str, max_articles: int = 3) -> list[str]:
    query = quote_plus(f'"{company_name}" (entreprise OR group OR société OR innovation OR électronique OR automobile)')
    url = f"https://html.duckduckgo.com/html/?q={query}"
    html = fetch_simple(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = []
    for a in soup.select("a.result__a")[:8]:
        href = a.get("href", "")
        if "duckduckgo" in href or not href.startswith("http"):
            continue
        art_html = fetch_simple(href)
        if art_html:
            text = clean_with_trafilatura(art_html, href)
            if len(text) > 400 and not is_low_value(text):
                articles.append(text[:4500])
            if len(articles) >= max_articles:
                break
        time.sleep(1.1)
    return articles


def build_dossier(company_name: str, website_url: str) -> dict:
    print(f"\n🔍 Building dossier for: {company_name}")
    print(f"   Website: {website_url}")

    dossier = {
        "company_name": company_name,
        "website_url": website_url,
        "sources": {}
    }

    print("\n1️⃣  Scraping official website...")
    website_texts = get_website_content(website_url)
    dossier["sources"]["website"] = website_texts
    print(f"   → {len(website_texts)} useful pages kept")

    print("\n2️⃣  Searching news & articles...")
    news = get_news(company_name)
    dossier["sources"]["news"] = news
    print(f"   → {len(news)} articles found")

    all_texts = []
    for source_texts in dossier["sources"].values():
        all_texts.extend(source_texts)

    full_text = "\n\n".join(all_texts)
    dossier["full_text"] = full_text
    dossier["total_chars"] = len(full_text)

    print(f"\n✅ Dossier ready — Total clean text: {len(full_text):,} characters")
    return dossier


if __name__ == "__main__":
    from pathlib import Path

    name = "ACTIA"
    url = "https://www.actia.com"

    dossier = build_dossier(name, url)

    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "dossier_actia_test.txt"
    output_file.write_text(dossier["full_text"], encoding="utf-8")

    print(f"\n📄 Saved to: {output_file}")
    print("\n--- Preview (first 900 characters) ---")
    print(dossier["full_text"][:900] if dossier["full_text"] else "No useful content collected.")
