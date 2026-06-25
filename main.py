import os
import requests
from bs4 import BeautifulSoup
from google import genai
import time

MENU_URL = "https://hf-foodpro.austin.utexas.edu/foodpro/shortmenu.aspx?sName=University+Housing+and+Dining&locationNum=12&locationName=J2+Dining&naFlag=1"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_raw_menu_text():
    response = requests.get(MENU_URL, headers=HEADERS, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Server returned status code {response.status_code}")
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text(separator='\n', strip=True)

def generate_recommendations(raw_text, api_key):
    client = genai.Client(api_key=api_key)
    prompt = f"""
    You are an elite sports nutritionist. Here is the raw text from a university dining hall menu today:
    
    {raw_text}
    
    TASK:
    Analyze the menu and construct THREE distinct meal options for Lunch and THREE distinct options for Dinner. Each option must strictly adhere to a caloric ceiling of 700-800 kcal while maximizing protein (aiming for 70g+ if mathematically viable).
    
    CONSTRAINTS:
    1. Option 1 (The Utilitarian): Prioritize absolute maximum protein efficiency (e.g., grilled poultry, lean beef).
    2. Option 2 (The Composite Bowl): Construct a meal mimicking a fast-casual bowl configuration, combining a bed of greens, a dense carbohydrate or grain base, a primary protein, and a vegetable.
    3. Option 3 (Culinary Diversity): Select a macro-friendly configuration featuring alternative cuisines (e.g., Asian-inspired dishes, Mexican profiles, or homestyle items) that still strictly meets the caloric parameters.
    
    FORMATTING:
    Respond directly as a Discord message using markdown. Keep it concise.
    Format EXACTLY like this:
    
    **LUNCH**
    **Option 1: Maximum Efficiency**
    * [Serving Size]x [Item Name]
    * [Serving Size]x [Item Name]
    *Macros: ~[X] kcal | [X]g P | [X]g C | [X]g F*
    
    **Option 2: The Composite Bowl**
    * [Serving Size]x [Item Name]
    * [Serving Size]x [Item Name]
    * [Serving Size]x [Item Name]
    *Macros: ~[X] kcal | [X]g P | [X]g C | [X]g F*
    
    **Option 3: Culinary Diversity**
    * [Serving Size]x [Item Name]
    * [Serving Size]x [Item Name]
    *Macros: ~[X] kcal | [X]g P | [X]g C | [X]g F*
    
    (Repeat identical structure for DINNER)
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < max_retries - 1:
                    print(f"[DEBUG] API overloaded. Retrying in 15 seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(15)
                    continue
            # If it's not a 503, or we run out of retries, throw the error to the crash handler
            raise e

if __name__ == "__main__":
    discord_webhook = os.environ.get("DISCORD_WEBHOOK")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not discord_webhook or not gemini_key:
        print("[ERROR] Missing environment variables.")
        exit(1)
        
    try:
        raw_menu = fetch_raw_menu_text()
        
        if len(raw_menu) < 500:
            requests.post(discord_webhook, json={"content": "⚠️ Failed to scrape page content. Payload too small."})
            exit(1)
            
        message_content = generate_recommendations(raw_menu, gemini_key)
        requests.post(discord_webhook, json={"content": message_content})
        
    except Exception as e:
        if discord_webhook:
            requests.post(discord_webhook, json={"content": f"⚠️ Execution Crash: {str(e)}"})