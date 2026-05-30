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


def load_config(path: str = "config.yaml") -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def load_products(path: str = "products.txt") -> list[str]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def collect(products, settings, allowed_stores) -> list[dict]:
    delay = settings.get("request_delay_seconds", 2)
    result = []
    for query in products:
        offers = scraper.search(query, delay=delay)
        rows = scraper.best_per_store(offers, allowed_stores)
        result.append({"query": query, "count": len(rows), "offers": rows})
    return result


def write_json(products, path: str = "docs/data.json") -> None:
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
    config = load_config()
    settings = config.get("settings", {})
    allowed_stores = config.get("allowed_stores", [])
    products = load_products()
    print(f"Tjekker {len(products)} produkter i {len(allowed_stores)} butikker...")
    data = collect(products, settings, allowed_stores)
    write_json(data)
    print("Skrev docs/data.json")


if __name__ == "__main__":
    main()
