import re
import time

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "da-DK,da;q=0.9,en;q=0.8",
}

PRICE_RE = re.compile(r'(\d{1,4}(?:[.,]\d{1,2})?)\s*,-')
DATE_RE = re.compile(r'\d{2}\.\d{2}\s*-\s*\d{2}\.\d{2}')
SIZE_RE = re.compile(r'\d+\s*[a-zæøå]+\.?\s*af\s*[\d.,]+\s*[a-zæøå]+\.?', re.I)
UNITPRICE_RE = re.compile(r'([\d.,]+)\s*,-\s*/\s*([a-zæøå]+)', re.I)

def _to_float(price_text):
    if not price_text:
        return None
    try:
        return float(price_text.replace(".", "").replace(",", "."))
    except ValueError:
        return None

def _norm_unit(u: str) -> str:
    u = (u or "").lower().rstrip(".")
    return {"ltr": "l", "liter": "l"}.get(u, u)

def _matches_query(title: str, query: str) -> bool:
    if not title:
        return False
    title_l = title.lower()
    tokens = [t for t in re.findall(r'[a-zæøå0-9]+', query.lower()) if len(t) >= 3]
    if not tokens:                       # meget korte søgeord (fx "æg")
        return query.lower() in title_l
    return all(tok in title_l for tok in tokens)

def search(query: str, delay: float = 2.0) -> list[dict]:
    search_link = f"https://www.tilbudsugen.dk/offer/{query.replace(' ', '+')}"
    r = requests.get(search_link, headers=HEADERS, timeout=20)
    r.raise_for_status()
    time.sleep(delay)

    soup = BeautifulSoup(r.text, "lxml")
    offers, seen = [], set()
    for a in soup.select('a[href*="/single/"]'):
        href = a.get("href", "")
        m = re.search(r'/single/(\d+)', href)
        if not m or m.group(1) in seen:
            continue
        # mindste forælder med et kæde-logo = selve produktkortet
        card, chain_img = a, None
        for _ in range(6):
            card = card.parent
            if card is None:
                break
            chain_img = card.select_one('img[src*="/chains/"]')
            if chain_img is not None:
                break
        if card is None:
            continue
        seen.add(m.group(1))

        text = card.get_text(" ", strip=True)
        name_img = card.select_one('a[href*="/single/"] img[alt]')
        title = (name_img["alt"].strip() if name_img and name_img.get("alt")
                 else a.get_text(strip=True)) or None
        if not _matches_query(title, query):
            continue

        store = None
        if chain_img is not None:
            store = (chain_img.get("alt") or "").strip() or None
            if not store:
                ms = re.search(r'/chains/([^./]+)\.', chain_img.get("src", ""))
                store = ms.group(1) if ms else None

        prices = PRICE_RE.findall(text)
        size_m = SIZE_RE.search(text)
        dates = DATE_RE.findall(text)

        prices = PRICE_RE.findall(text)
        size_m = SIZE_RE.search(text)
        dates = DATE_RE.findall(text)
        unit_m = UNITPRICE_RE.search(text)

        offers.append({
            "query": query,
            "title": title,
            "size": size_m.group(0).strip() if size_m else None,
            "price": _to_float(prices[0]) if prices else None,
            "unit_price": _to_float(unit_m.group(1)) if unit_m else None,
            "unit_base": _norm_unit(unit_m.group(2)) if unit_m else None,
            "store": store,
            "dates": dates[0] if dates else None,
            "link": ("https://www.tilbudsugen.dk" + href) if href.startswith("/") else href,
            "search_link": search_link,
         })
    return offers


def top_cheapest(offers: list[dict], n: int = 5) -> list[dict]:
    """Rangordn efter enhedspris (kr pr. liter/kg). Varer uden enhedspris ryger bagerst."""
    def key(o):
        up = o.get("unit_price")
        return up if isinstance(up, (int, float)) else float("inf")
    candidates = [o for o in offers
                  if isinstance(o.get("unit_price"), (int, float))
                  or isinstance(o.get("price"), (int, float))]
    return sorted(candidates, key=key)[:n]
