import os
import requests
from bs4 import BeautifulSoup
from google import genai

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
    Select the optimal combination of items for both Lunch and Dinner to maximize protein while keeping the total calories for each meal strictly between 700-800 kcal. 
    
    CONSTRAINTS:
    1. Prioritize whole, single-ingredient protein sources (e.g., grilled chicken, plain beef) over mixed casseroles or stews to minimize hidden oil variances.
    2. Include at least one high-volume vegetable per meal.
    3. Ensure portion sizes are realistic for a dining hall setting.
    
    FORMATTING:
    Respond directly as a Discord message using markdown. Do not use conversational filler. 
    Format EXACTLY like this:
    **LUNCH**
    * [Serving Size]x [Item Name]
    * [Serving Size]x [Item Name]
    *Estimated Macros: [X] kcal | [X]g P | [X]g C | [X]g F*
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

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