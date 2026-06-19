import os
import re
import time
import requests
from bs4 import BeautifulSoup
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatus

MENU_URL = "https://hf-foodpro.austin.utexas.edu/foodpro/shortmenu.aspx?sName=University+Housing+and+Dining&locationNum=12&locationName=J2+Dining&naFlag=1"
LABEL_BASE_URL = "https://hf-foodpro.austin.utexas.edu/foodpro/label.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive"
}

def fetch_daily_menu(session):
    response = session.get(MENU_URL, timeout=15)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    menu_data = {'Breakfast': [], 'Lunch': [], 'Dinner': []}
    current_meal = None
    
    for element in soup.find_all(True):
        text = element.get_text().strip()
        
        if text == 'Breakfast': current_meal = 'Breakfast'
        elif text == 'Lunch': current_meal = 'Lunch'
        elif text == 'Dinner': current_meal = 'Dinner'
        
        if current_meal and element.name == 'a':
            href = element.get('href', '')
            if 'label.aspx?RecNumAndPort=' in href:
                recipe_id = re.search(r'RecNumAndPort=([^&]+)', href).group(1)
                
                # Throttle execution to bypass heuristic rate-limiters
                time.sleep(0.5) 
                
                macro_data = get_item_macros(session, recipe_id)
                if macro_data == "BLOCKED":
                    return {"error": "Firewall blocked the request (HTTP 403)."}
                
                if macro_data:
                    menu_data[current_meal].append({
                        "name": text,
                        "calories": macro_data["calories"],
                        "protein": macro_data["protein"]
                    })
                    
    return menu_data

def get_item_macros(session, recipe_id):
    try:
        url = f"{LABEL_BASE_URL}?RecNumAndPort={recipe_id}"
        res = session.get(url, timeout=5)
        
        if res.status_code == 403:
            return "BLOCKED"
            
        soup = BeautifulSoup(res.text, 'html.parser')
        page_text = soup.get_text()
        
        cal = re.search(r'Calories\s+(\d+)', page_text) or re.search(r'Calories:\s*(\d+)', page_text)
        prot = re.search(r'Protein\s+(\d+)', page_text) or re.search(r'Protein:\s*(\d+)', page_text)
        
        if cal and prot:
            return {"calories": int(cal.group(1)), "protein": int(prot.group(1))}
    except Exception:
        pass
    return None

def optimize_meal_selection(available_items, target_calories=800):
    if not available_items: 
        return ["No food items parsed."]
    
    prob = LpProblem("J2_Optimize", LpMaximize)
    item_vars = {}
    
    for i, item in enumerate(available_items):
        key = f"item_{i}"
        item_vars[key] = LpVariable(key, 0, 2, cat='Integer')
        item['key'] = key

    prob += lpSum([item_vars[item['key']] * item['protein'] for item in available_items])
    prob += lpSum([item_vars[item['key']] * item['calories'] for item in available_items]) <= target_calories
    
    prob.solve()
    
    if LpStatus[prob.status] != "Optimal":
        sorted_items = sorted(available_items, key=lambda x: x['protein'], reverse=True)[:3]
        return [f"1x {item['name']} ({item['protein']}g P / {item['calories']} kcal) [Fallback Selection]" for item in sorted_items]

    recs = [f"{int(item_vars[item['key']].varValue)}x {item['name']} ({item['protein']}g P / {item['calories']} kcal)" 
            for item in available_items if item_vars[item['key']].varValue > 0]
            
    return recs if recs else ["Constraints could not be met."]

if __name__ == "__main__":
    webhook = os.environ.get("DISCORD_WEBHOOK")
    
    # Initialize persistent session
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        data = fetch_daily_menu(session)
        
        if "error" in data:
            requests.post(webhook, json={"content": f"⚠️ {data['error']}"}, timeout=10)
            exit(1)
            
        message = "**🎰 J2 DAILY OPTIMIZATION MATRIX** 🎰\n\n"
        for meal in ['Lunch', 'Dinner']:
            items = data.get(meal, [])
            recs = optimize_meal_selection(items)
            
            message += f"**__{meal.upper()}__**\n" + "\n".join(recs) + "\n\n"
            
        requests.post(webhook, json={"content": message}, timeout=10)
        
    except Exception as e:
        if webhook:
            requests.post(webhook, json={"content": f"⚠️ Crash: {str(e)}"}, timeout=10)