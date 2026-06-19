import os
import re
import requests
from bs4 import BeautifulSoup
from pulp import LpProblem, LpMaximize, LpVariable, lpSum

MENU_URL = "https://hf-foodpro.austin.utexas.edu/foodpro/shortmenu.aspx?sName=University+Housing+and+Dining&locationNum=12&locationName=J2+Dining&naFlag=1"
LABEL_BASE_URL = "https://hf-foodpro.austin.utexas.edu/foodpro/label.aspx"

def fetch_daily_menu():
    response = requests.get(MENU_URL, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    current_meal, menu_data = None, {}

    for element in soup.find_all(['div', 'table', 'a']):
        text = element.get_text().strip()
        if text in ['Breakfast', 'Lunch', 'Dinner']:
            current_meal = text
            menu_data[current_meal] = []
            continue
            
        if element.name == 'a' and 'label.aspx?RecNumAndPort=' in element.get('href', ''):
            href = element.get('href')
            recipe_id = re.search(r'RecNumAndPort=([^&]+)', href).group(1)
            macro_data = get_item_macros(recipe_id)
            if macro_data:
                menu_data[current_meal].append({"name": text, **macro_data})
    return menu_data

def get_item_macros(recipe_id):
    try:
        url = f"{LABEL_BASE_URL}?RecNumAndPort={recipe_id}"
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        page_text = soup.get_text()
        return {
            "calories": int(re.search(r'Calories\s+(\d+)', page_text).group(1)),
            "protein": int(re.search(r'Protein\s+(\d+)g', page_text).group(1))
        }
    except Exception:
        return None

def optimize_meal_selection(available_items, target_calories=750):
    if not available_items: return []
    prob = LpProblem("J2_Optimize", LpMaximize)
    item_vars = {item['name']: LpVariable(f"eat_{hash(item['name'])}", 0, 2, cat='Integer') for item in available_items}
    
    prob += lpSum([item_vars[item['name']] * item['protein'] for item in available_items])
    prob += lpSum([item_vars[item['name']] * item['calories'] for item in available_items]) <= target_calories
    prob.solve()
    
    return [f"{int(item_vars[item['name']].varValue)}x {item['name']} ({item['protein']}g P / {item['calories']} kcal)" 
            for item in available_items if item_vars[item['name']].varValue and item_vars[item['name']].varValue > 0]

if __name__ == "__main__":
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if webhook_url:
        try:
            data = fetch_daily_menu()
            message = "**🎰 J2 DAILY OPTIMIZATION MATRIX** 🎰\n\n"
            for meal in ['Lunch', 'Dinner']:
                recs = optimize_meal_selection(data.get(meal, []))
                message += f"**__{meal.upper()}__**\n" + ("\n".join(recs) if recs else "No data found.") + "\n\n"
            requests.post(webhook_url, json={"content": message}, timeout=10)
        except Exception as e:
            requests.post(webhook_url, json={"content": f"⚠️ Execution Error: {str(e)}"}, timeout=10)