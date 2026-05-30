import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml

import scraper

CPH = ZoneInfo("Europe/Copenhagen")


def should_run() -> bool:
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return True
    return datetime.now(CPH).hour == 7


def load_settings(path: str = "config.yaml") -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}
    return cfg.get("settings", {})


def load_products(path: str = "products.txt") -> list[str]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def collect(products: list[str], settings: dict) -> list[dict]:
    top_n = settings.get("top_n", 3)
    delay = settings.get("request_delay_seconds", 2)
    result = []
    for query in products:
        offers = scraper.search(query, delay=delay)
        cheapest = scraper.top_cheapest(offers, n=top_n)
        result.append({"query": query, "count": len(offers), "offers": cheapest})
    return result


def write_json(products: list[dict], path: str = "docs/data.json") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "generated_at": datetime.now(CPH).isoformat(timespec="minutes"),
        "products": products,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    if not should_run():
        print("Det er ikke kl. 7 i Danmark lige nu – springer kørslen over.")
        return
    products = load_products()
    settings = load_settings()
    print(f"Tjekker {len(products)} produkter...")
    data = collect(products, settings)
    write_json(data)
    print("Skrev docs/data.json")


if __name__ == "__main__":
    main()