import httpx
import asyncio
import os
import re
from dotenv import load_dotenv
import redis, json

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

load_dotenv()

OWM_API_KEY = os.getenv("OPENWEATHER_API_KEY")
RAPIDAPI_KEY = os.getenv("X_RAPIDAPI_KEY")

ZYLA_HOST = "global-city-cost-api.p.rapidapi.com"
ZYLA_URL = "https://global-city-cost-api.p.rapidapi.com/cost%2Bof%2Bliving%2Bby%2Bcity%2Bv2"

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"


# ─── HELPERS ────────────────────────────────────────

def parse_price(value: str) -> float:
    """Extract float from strings like '631.00 €' or '1,172.05 $'"""
    if not value:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def calculate_monthly_cost(data: dict) -> int:
    """
    Build a realistic monthly cost for a solo remote worker from line items.
    Covers: rent, utilities, transport, food basket, internet, phone.
    """
    rent        = parse_price(data.get("1 Bedroom Apartment Outside of City Centre", "0"))
    utilities   = parse_price(data.get("Basic Utilities for 915 Square Feet Apartment (Electricity, Heating, Cooling, Water, Garbage)", "0"))
    transport   = parse_price(data.get("Monthly Public Transport Pass (Regular Price)", "0"))
    internet    = parse_price(data.get("Broadband Internet (Unlimited Data, 60 Mbps or Higher)", "0"))
    phone       = parse_price(data.get("Mobile Phone Plan (Monthly, with Calls and 10GB+ Data)", "0"))

    # Simple food basket: 20 meals at inexpensive restaurants + basic groceries
    meal        = parse_price(data.get("Meal at an Inexpensive Restaurant", "0"))
    milk        = parse_price(data.get("Milk (Regular, 1 Liter)", "0"))
    bread       = parse_price(data.get("Fresh White Bread (1 lb Loaf)", "0"))
    eggs        = parse_price(data.get("Eggs (12, Large Size)", "0"))
    chicken     = parse_price(data.get("Chicken Fillets (1 lb)", "0"))

    food = (meal * 20) + (milk * 8) + (bread * 8) + (eggs * 4) + (chicken * 6)

    mid_range_meal = parse_price(data.get("Meal for Two at a Mid-Range Restaurant (Three Courses, Without Drinks)", "0"))
    food += mid_range_meal * 4  # once a week dinner out

    total = rent + utilities + transport + internet + phone + food
    print(f"[DEBUG] rent={rent} utilities={utilities} transport={transport} internet={internet} phone={phone} food={food}")
    return round(total)


def extract_wifi_speed(data: dict) -> int:
    """
    The Zyla API describes broadband as 'Unlimited Data, 60 Mbps or Higher'.
    We store 60 as a baseline — it's a floor, not an exact speed.
    """
    return 60

def detect_currency(data: dict) -> str:
    """Sniff currency symbol from price fields in Zyla response."""
    sample = data.get("1 Bedroom Apartment Outside of City Centre", "")
    if "€" in sample: return "EUR"
    if "£" in sample: return "GBP"
    if "฿" in sample: return "THB"
    if "¥" in sample: return "JPY"
    if "₹" in sample: return "INR"
    if "₩" in sample: return "KRW"
    if "R$" in sample: return "BRL"
    return "USD"

async def convert_to_usd(amount: float, currency_code: str) -> float:
    if currency_code == "USD":
        return amount
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"https://open.er-api.com/v6/latest/{currency_code}",
                timeout=10
            )
            data = resp.json()
            rate = data["rates"]["USD"]
            return round(amount * rate)
        except Exception as e:
            print(f"[FX] Conversion failed for {currency_code}: {e}")
            return amount

def get_cached(key: str):
    data = redis_client.get(key)
    return json.loads(data) if data else None

def set_cached(key: str, value: dict, ttl_seconds: int):
    redis_client.setex(key, ttl_seconds, json.dumps(value))

# ─── API CALLS ──────────────────────────────────────

async def fetch_weather(city_name: str) -> dict:
    """Fetch current weather from OpenWeatherMap. Returns avg_temp in Celsius."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(OWM_URL, params={
                "q": city_name,
                "appid": OWM_API_KEY,
                "units": "metric"       # Celsius
            }, timeout=10)
            resp.raise_for_status()
            owm_data = resp.json()
            temp = owm_data["main"]["temp"]
            return {"avg_temp": round(temp, 1)}
        except Exception as e:
            print(f"[OWM] Failed for {city_name}: {e}")
            return {"avg_temp": None}


async def fetch_cost_of_living(city_name: str, country_name: str) -> dict:
    """Fetch city cost of living from Zyla via RapidAPI."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(ZYLA_URL, params={
                "city": city_name,
                "country": country_name
            }, headers={
                "x-rapidapi-key": RAPIDAPI_KEY,
                "x-rapidapi-host": ZYLA_HOST,
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if not data.get("Success"):
                print(f"[Zyla] Unsuccessful response for {city_name}")
                return {"monthly_cost": None, "wifi_speed": None}

            # return {
            #     "monthly_cost": calculate_monthly_cost(data),
            #     "wifi_speed": extract_wifi_speed(data),
            # }

            raw_cost = calculate_monthly_cost(data)
            currency = detect_currency(data)
        
            print(f"[DEBUG] {city_name} raw cost: {raw_cost} {currency}")
            monthly_cost_usd = await convert_to_usd(raw_cost, currency)
            print(f"[DEBUG] {city_name} converted: {monthly_cost_usd} USD")

            return {
                "monthly_cost": monthly_cost_usd,
                "wifi_speed": extract_wifi_speed(data),
            }

        except Exception as e:
            print(f"[Zyla] Failed for {city_name}: {e}")
            return {"monthly_cost": None, "wifi_speed": None}


# ─── MAIN ENRICHMENT FUNCTION ───────────────────────

# async def enrich_city(city_name: str, country_name: str) -> dict:
#     """
#     Fan out to OWM + Zyla simultaneously using asyncio.gather.
#     Returns merged dict of enriched fields ready to update the DB.
#     """
#     weather_data, col_data = await asyncio.gather(
#         fetch_weather(city_name),
#         fetch_cost_of_living(city_name, country_name)
#     )

#     return {**weather_data, **col_data}


# with cache
async def enrich_city(city_name: str, country_name: str) -> dict:
    cache_key = f"city:{city_name.lower()}:{country_name.lower()}"
    
    cached = get_cached(cache_key)
    if cached:
        print(f"[CACHE HIT] {city_name}")
        return cached

    print(f"[CACHE MISS] {city_name} — fetching from APIs")
    weather_data, col_data = await asyncio.gather(
        fetch_weather(city_name),
        fetch_cost_of_living(city_name, country_name)
    )

    result = {**weather_data, **col_data}
    
    # Only cache if we got real data — don't cache API failures
    if result.get("monthly_cost") is not None:
        set_cached(cache_key, result, ttl_seconds=3600)
    else:
        print(f"[CACHE SKIP] {city_name} — incomplete data, not caching")
    
    return result