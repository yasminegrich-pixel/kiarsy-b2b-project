import requests, time, json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KiarsyBot/1.0"}
PAGE_KEYWORDS = ['a-propos','about','qui-sommes','rse','csr','engagement','valeurs',
                 'values','mission','sustainability','durabilite','fondation','foundation','responsab']
MAX_CHARS_PER_SOURCE = 20000

def clean(soup):
    for tag in soup(["script","style","nav","footer","header","aside","form"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ", strip=True).split())

def fetch(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None

def source_website(start_url):
    """Homepage + keyword pages discovered via sitemap.xml and link hunting."""
    pages, texts = [], []
    base = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"

    html = fetch(start_url)
    if not html:
        return texts
    soup = BeautifulSoup(html, "html.parser")
    texts.append(clean(soup)); pages.append(start_url)

    # 1) sitemap hunt (defeats the JavaScript wall)
    candidates = set()
    for sm in [base + "/sitemap.xml", base + "/sitemap_index.xml"]:
        xml = fetch(sm)
        if xml:
            for loc in BeautifulSoup(xml, "xml").find_all("loc"):
                if loc.text and any(k in loc.text.lower() for k in PAGE_KEYWORDS):
                    candidates.add(loc.text.strip())

    # 2) link hunt on the homepage (fallback for sites without sitemaps)
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(k in href for k in PAGE_KEYWORDS):
            candidates.add(urljoin(start_url, a["href"]))

    for url in list(candidates)[:4]:
        if url in pages:
            continue
        h = fetch(url)
        if h:
            t = clean(BeautifulSoup(h, "html.parser"))
            if len(t) > 300:
                texts.append(t); pages.append(url)
        time.sleep(1)
    return texts[:MAX_CHARS_PER_SOURCE // 4000 + 1] or texts

def source_wikipedia(company_name):
    for lang in ["fr", "en"]:
        api = f"https://{lang}.wikipedia.org/w/api.php"
        try:
            s = requests.get(api, params={"action":"query","list":"search",
                "srsearch":company_name,"format":"json","srlimit":1},
                headers=HEADERS, timeout=10).json()
            hits = s.get("query", {}).get("search", [])
            if not hits:
                continue
            title = hits[0]["title"]
            e = requests.get(api, params={"action":"query","prop":"extracts",
                "explaintext":1,"titles":title,"format":"json"},
                headers=HEADERS, timeout=10).json()
            page = list(e["query"]["pages"].values())[0]
            if "extract" in page:
                return [page["extract"][:MAX_CHARS_PER_SOURCE]]
        except Exception:
            continue
    return []

def source_news(company_name):
    q = quote_plus(f'"{company_name}" (RSE OR engagements OR valeurs OR CSR OR sustainability OR partenariat OR award)')
    html = fetch(f"https://html.duckduckgo.com/html/?q={q}")
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    texts = []
    for a in soup.select("a.result__a")[:4]:
        href = a.get("href", "")
        if "duckduckgo" in href or not href.startswith("http"):
            continue
        h = fetch(href)
        if h:
            t = clean(BeautifulSoup(h, "html.parser"))
            if len(t) > 500:
                texts.append(t[:6000])
        time.sleep(1)
    return texts

def build_dossier(company_name, url):
    dossier = {}
    print(f"🌐 Website...");      dossier["website"] = source_website(url)
    print(f"📚 Wikipedia...");    dossier["wikipedia"] = source_wikipedia(company_name)
    print(f"📰 Press/news...");   dossier["news"] = source_news(company_name)
    return dossier

if __name__ == "__main__":
    NAME, URL = "Sopra HR Software", "https://www.soprahr.com/"
    d = build_dossier(NAME, URL)
    total = 0
    print("\n=== DOSSIER SUMMARY ===")
    for src, texts in d.items():
        n = sum(len(t) for t in texts)
        total += n
        print(f"  {src:10s}: {len(texts)} pages, {n} chars")
    print(f"  {'TOTAL':10s}: {total} chars")
    merged = "\n\n".join(t for texts in d.values() for t in texts)
    print("\n--- PREVIEW (first 700 chars) ---")
    print(merged[:700])
