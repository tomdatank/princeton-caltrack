#!/usr/bin/env python3
"""
Princeton Dining Menu Scraper
Fetches menus for all dining halls for today + next 6 days,
parses nutrition data, and writes data/menu.json.
Run manually or via GitHub Actions daily.
"""

import os
import json
import re
import sys
from datetime import date, timedelta
from urllib.parse import urlencode, quote

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://menus.princeton.edu/dining/_Foodpro/online-menu/menuDetails.asp"

DINING_HALLS = [
    {"name": "Rockefeller & Mathey",       "num": "01"},
    {"name": "Forbes College",              "num": "03"},
    {"name": "Graduate College",            "num": "04"},
    {"name": "Center for Jewish Life",      "num": "05"},
    {"name": "Yeh & New College West",      "num": "06"},
    {"name": "Whitman & Butler",            "num": "08"},
]

DAYS_AHEAD = 6  # scrape today + 6 more days (a full week)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_url(location_num: str, location_name: str, dt: date) -> str:
    params = {
        "sName": "Princeton University Campus Dining",
        "locationNum": location_num,
        "locationName": location_name,
        "dtdate": f"{dt.month}/{dt.day}/{dt.year}",
        "naFlag": "1",
        "myaction": "read",
    }
    return BASE_URL + "?" + urlencode(params)


def parse_float(text: str) -> float | None:
    """Extract the first number from a string like '13.1g' or '752.9mg'."""
    text = text.strip().replace("- - -", "").replace("---", "")
    m = re.search(r"[\d.]+", text)
    return float(m.group()) if m else None


def parse_nutrition_block(block) -> dict:
    """
    Parse a nutrition facts div into a dict.
    The block is the <div> or <section> that follows an <h2> item name.
    """
    nutrition = {}
    text = block.get_text(separator="\n")

    patterns = {
        "serving_size":     r"Serving Size[:\s]+(.+)",
        "calories":         r"Calories[:\s]+([\d.]+)",
        "total_fat_g":      r"Total Fat[:\s]+([\d.]+)",
        "saturated_fat_g":  r"Saturated Fat[:\s]+([\d.]+)",
        "trans_fat_g":      r"Trans Fat[:\s]+([\d.]+)",
        "cholesterol_mg":   r"Cholesterol[:\s]+([\d.]+)",
        "sodium_mg":        r"Sodium[:\s]+([\d.]+)",
        "carbs_g":          r"Total Carbohydrates[:\s]+([\d.]+)",
        "fiber_g":          r"Dietary Fiber[:\s]+([\d.]+)",
        "sugars_g":         r"Sugars[:\s]+([\d.]+)",
        "protein_g":        r"Protein[:\s]+([\d.]+)",
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if key == "serving_size":
                nutrition[key] = val
            else:
                try:
                    nutrition[key] = float(val)
                except ValueError:
                    nutrition[key] = None
        else:
            nutrition[key] = None

    # Allergens
    allergen_match = re.search(r"Allergens[:\s]+(.+?)(?:\n|Ingredients)", text, re.IGNORECASE | re.DOTALL)
    if allergen_match:
        allergens_raw = allergen_match.group(1).strip()
        nutrition["allergens"] = [a.strip() for a in allergens_raw.split(",") if a.strip()]
    else:
        nutrition["allergens"] = []

    # Ingredients (optional, kept short)
    ing_match = re.search(r"Ingredients[:\s]+(.+?)(?:\nAllergens|\*\[Open|$)", text, re.IGNORECASE | re.DOTALL)
    if ing_match:
        nutrition["ingredients"] = ing_match.group(1).strip()
    else:
        nutrition["ingredients"] = None

    return nutrition


def parse_menu_page(html: str, hall_name: str, dt: date) -> list[dict]:
    """
    Parse a full menuDetails page into a list of food item dicts.
    Returns [] if the page indicates the hall is closed / no menu.
    """
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # Current meal section and station, tracked as we walk the DOM
    current_meal = None
    current_station = None

    # Walk all relevant tags in document order
    for tag in soup.find_all(["h2", "h3", "h4", "h5", "strong", "p", "div", "section"]):

        # Meal headers appear as bold text inside certain containers
        # e.g. "Breakfast", "Lunch", "Dinner" appear as <strong> or in specific classes
        tag_text = tag.get_text(strip=True)

        # Detect meal period headers (they appear as bold standalone lines)
        if tag.name in ("strong", "b") and tag_text in ("Breakfast", "Lunch", "Dinner"):
            current_meal = tag_text
            current_station = None
            continue

        # Station sub-headers appear as plain text paragraphs or small headings
        # e.g. "At the grill", "Main Entree", "Salads"
        if tag.name in ("h4", "h5") and tag_text and len(tag_text) < 60:
            current_station = tag_text
            continue

        # Food item names appear as <h2> tags
        if tag.name == "h2" and tag_text:
            item_name = tag_text

            # The nutrition block immediately follows the h2 in the DOM
            nutrition_div = tag.find_next_sibling()
            nutrition = {}
            if nutrition_div:
                nutrition = parse_nutrition_block(nutrition_div)

            items.append({
                "hall": hall_name,
                "date": dt.isoformat(),
                "meal": current_meal,
                "station": current_station,
                "name": item_name,
                **nutrition,
            })

    return items


def scrape_hall_day(hall: dict, dt: date) -> list[dict]:
    url = build_url(hall["num"], hall["name"], dt)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️  {hall['name']} {dt}: request failed — {e}", file=sys.stderr)
        return []

    items = parse_menu_page(resp.text, hall["name"], dt)
    print(f"  ✓  {hall['name']} {dt.strftime('%a %b %-d')}: {len(items)} items")
    return items


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = date.today()
    dates = [today + timedelta(days=i) for i in range(DAYS_AHEAD + 1)]

    all_items = []

    for dt in dates:
        print(f"\n📅 {dt.strftime('%A, %B %-d %Y')}")
        for hall in DINING_HALLS:
            items = scrape_hall_day(hall, dt)
            all_items.extend(items)

    # Build output structure
    output = {
        "scraped_at": date.today().isoformat(),
        "item_count": len(all_items),
        "items": all_items,
    }

    out_path = "data/menu.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Wrote {len(all_items)} items to {out_path}")


if __name__ == "__main__":
    main()