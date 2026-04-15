# Princeton Dining Meal Planner

A static website that helps you plan daily meals across Princeton dining halls to hit your calorie and protein goals.

Menu data is automatically scraped from [menus.princeton.edu](https://menus.princeton.edu) every morning and saved as JSON in this repo. The frontend reads directly from that file — no backend or API key needed.

---

## Project Structure

```
princeton-dining/
├── .github/
│   └── workflows/
│       └── scrape.yml      # GitHub Action: runs scraper daily at 6am ET
├── data/
│   └── menu.json           # Auto-generated daily — do not edit by hand
├── scrape.py               # Python scraper
├── requirements.txt
├── index.html              # Frontend (to be built)
└── README.md
```

---

## Data Format

`data/menu.json` contains:

```json
{
  "scraped_at": "2026-04-15",
  "item_count": 423,
  "items": [
    {
      "hall": "Rockefeller & Mathey",
      "date": "2026-04-15",
      "meal": "Breakfast",
      "station": "At the grill",
      "name": "Scrambled Eggs",
      "serving_size": "3 oz",
      "calories": 150.0,
      "protein_g": 10.2,
      "total_fat_g": 11.2,
      "saturated_fat_g": 3.0,
      "carbs_g": 1.3,
      "fiber_g": 0.0,
      "sugars_g": 0.0,
      "cholesterol_mg": 365.7,
      "sodium_mg": 110.6,
      "allergens": ["Eggs"],
      "ingredients": "Eggs, Canola Oil"
    }
  ]
}
```

**Dining halls scraped:**
| Hall | Location Num |
|---|---|
| Rockefeller & Mathey | 01 |
| Forbes College | 03 |
| Graduate College | 04 |
| Center for Jewish Life | 05 |
| Yeh & New College West | 06 |
| Whitman & Butler | 08 |

---

## Running the Scraper Locally

```bash
pip install -r requirements.txt
python scrape.py
```

This writes `data/menu.json` with today + 6 days of menu data.

---

## GitHub Actions Setup

The workflow in `.github/workflows/scrape.yml` runs automatically every day at 6am ET. It:
1. Runs `scrape.py`
2. Commits the updated `data/menu.json` back to the repo

The workflow needs **write permissions** — make sure your repo settings allow Actions to create commits:
> Settings → Actions → General → Workflow permissions → "Read and write permissions"

You can also trigger it manually from the **Actions** tab in GitHub at any time.

---

## GitHub Pages Setup

To host the frontend on GitHub Pages:
> Settings → Pages → Source → Deploy from branch → `main` → `/ (root)`

The site will be live at `https://<your-username>.github.io/princeton-dining/`
