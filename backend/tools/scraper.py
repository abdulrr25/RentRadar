"""
Universal Scraper tool — any arbitrary URL → clean Markdown via Anakin's /v1/scrape.
Handles JS-rendered React portals: NoBroker, MagicBricks, Housing.com.
"""

import httpx
import os

ANAKIN_API_KEY = os.getenv("ANAKIN_API_KEY")
SCRAPER_URL = "https://api.anakin.io/v1/scrape"

HEADERS = {
    "X-API-Key": ANAKIN_API_KEY or "",
    "Content-Type": "application/json",
}


async def scrape_url(url: str, source_name: str, render_js: bool = True) -> dict:
    """Universal Scraper — any URL → Markdown content, always returns a safe dict."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            response = await client.post(
                SCRAPER_URL,
                headers=HEADERS,
                json={"url": url, "format": "markdown", "render_js": render_js},
            )
            response.raise_for_status()
            data = response.json()
            return {
                "source": source_name,
                "status": "ok",
                "data": data.get("content", ""),
            }
    except Exception as e:
        return {"source": source_name, "status": "error", "data": str(e)}


async def fetch_nobroker(locality: str, bhk: str, max_rent: int) -> dict:
    """Scrape NoBroker listings (JS-rendered — not in Wire catalog)."""
    bhk_num = bhk.replace("BHK", "").strip()
    locality_slug = locality.lower().replace(" ", "-")
    url = (
        f"https://www.nobroker.in/property/rent/bangalore/{locality_slug}"
        f"?bhkTypes={bhk_num}BHK&maxRent={max_rent}&sortBy=Freshness"
    )
    return await scrape_url(url, "NoBroker", render_js=True)


async def fetch_magicbricks(locality: str, bhk: str, max_rent: int) -> dict:
    """Scrape MagicBricks listings (JS-rendered — not in Wire catalog)."""
    bhk_num = bhk.replace("BHK", "").strip()
    url = (
        f"https://www.magicbricks.com/property-for-rent/residential-real-estate"
        f"?proptype=Multistorey-Apartment,Builder-Floor-Apartment"
        f"&city=Bangalore&area={locality}&maxPrice={max_rent}&bhk={bhk_num}"
    )
    return await scrape_url(url, "MagicBricks", render_js=True)


async def fetch_housing(locality: str, bhk: str) -> dict:
    """Scrape Housing.com listings (JS-rendered — not in Wire catalog)."""
    bhk_num = bhk.replace("BHK", "").strip()
    locality_slug = locality.lower().replace(" ", "-")
    url = f"https://housing.com/in/rent/bangalore/{locality_slug}/{bhk_num}bhk"
    return await scrape_url(url, "Housing.com", render_js=True)
