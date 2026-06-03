import httpx
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

async def generate_city_insight(city: dict, user_prefs: dict) -> str:
    """Generate a short AI insight for why a city matches a user's profile."""
    
    prompt = f"""You are a helpful nomad lifestyle advisor. Given a city's data and a user's preferences, write a 2-3 sentence insight explaining how well this city fits the user.

City: {city['name']}, {city['country']}
- Monthly cost: ${city['monthly_cost']}
- Avg temperature: {city['avg_temp']}°C
- Timezone: {city['timezone']}

User preferences:
- Max budget: ${user_prefs['max_budget']}
- Preferred temp: {user_prefs['preferred_temp']}°C
- Work hours: {user_prefs['work_start_hour']}:00 - {user_prefs['work_end_hour']}:00 ({user_prefs['client_timezone']})

Be specific and concise. No bullet points. Just 2-3 natural sentences."""
    
    # print(f"[Groq] Using key: {GROQ_API_KEY[:10]}...")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.7
                },
                timeout=15
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[Groq] Failed for {city['name']}: {e}")
            return None