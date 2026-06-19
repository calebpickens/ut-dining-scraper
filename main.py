import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

MENU_URL = "https://hf-foodpro.austin.utexas.edu/foodpro/shortmenu.aspx?sName=University+Housing+and+Dining&locationNum=12&locationName=J2+Dining&naFlag=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch_menu_names():
    response = requests.get(MENU_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    menu_data = {'Lunch': [], 'Dinner': []}
    current_meal = None
    
    # Flat parsing to grab just the names from the main page
    for element in soup.find_all(True):
        text = element.get_text().strip()
        if text == 'Breakfast': current_meal = 'Breakfast'
        elif text == 'Lunch': current_meal = 'Lunch'
        elif text == 'Dinner': current_meal = 'Dinner'
        
        if current_meal in ['Lunch', 'Dinner'] and element.name == 'a' and 'label.aspx' in element.get('href', ''):
            if text and text not in menu_data[current_meal]:
                menu_data[current_meal].append(text)
                
    return menu_data

def generate_recommendations(menu_data, api_key):
    genai.configure(api_key=api_key)
    # Using the fast, free-tier model
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a nutrition bot. Here is the available menu for a university dining hall today:
    
    LUNCH: {', '.join(menu_data['Lunch'])}
    DINNER: {', '.join(menu_data['Dinner'])}
    
    Select the optimal combination of items for both Lunch and Dinner to maximize protein while keeping the total calories for each meal around 750-800. 
    Estimate the macros based on standard nutritional profiles for these foods.
    Format your response directly as a Discord message using markdown. Use bullet points. Keep it concise. Start immediately with the Lunch header.
    """
    
    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    discord_webhook = os.environ.get("DISCORD_WEBHOOK")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not discord_webhook or not gemini_key:
        print("[ERROR] Missing environment variables.")
        exit(1)
        
    try:
        menu_items = fetch_menu_names()
        
        if not menu_items['Lunch'] and not menu_items['Dinner']:
            requests.post(discord_webhook, json={"content": "⚠️ Failed to parse main menu names. Firewall may be blocking the root domain."})
            exit(1)
            
        message_content = generate_recommendations(menu_items, gemini_key)
        
        # Dispatch the AI's direct output to Discord
        requests.post(discord_webhook, json={"content": message_content})
        
    except Exception as e:
        requests.post(discord_webhook, json={"content": f"⚠️ Execution Crash: {str(e)}"})