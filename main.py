import os
import re
import requests
from bs4 import BeautifulSoup
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatus

MENU_URL = "https://hf-foodpro.austin.utexas.edu/foodpro/shortmenu.aspx?sName=University+Housing+and+Dining&locationNum=12&locationName=J2+Dining&naFlag=1"
LABEL_BASE_URL = "https://hf-foodpro.austin.utexas.edu/foodpro/label.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_daily_menu():
    print("[DEBUG] Connecting to UT FoodPro...")
    response = requests.get(MENU_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    menu_data = {'Breakfast': [], 'Lunch': [], 'Dinner': []}
    current_meal = None
    
    # We iterate flatly through every single tag in the body in execution order
    for element in soup.find_all(True):
        text = element.get_text().strip()
        
        # Check if we are passing a major meal delimiter block
        if text == 'Breakfast':
            current_meal = 'Breakfast'
            continue
        elif text == 'Lunch':
            current_meal = 'Lunch'
            continue
        elif text == 'Dinner':
            current_meal = 'Dinner'
            continue
            
        # If we are currently tracking a valid meal segment and hit a recipe hyperlink
        if current_meal and element.name == 'a':
            href = element.get('href', '')
            if 'label.aspx?RecNumAndPort=' in href:
                item_name = text
                recipe_id = re.search(r'RecNumAndPort=([^&]+)', href).group(1)
                
                # Pull the individual food metrics
                macro_data = get_item_macros(recipe_id, item_name)
                if macro_data:
                    menu_data[current_meal].append({
                        "name": item_name,
                        "calories": macro_data["calories"],
                        "protein": macro_data["protein"]
                    })
                    
    print(f"[DEBUG] Processing complete. Scraped counts: { {k: len(v) for k, v in menu_data.items()} }")
    return menu_data

def get_item_macros(recipe_id, item_name):
    try:
        url = f"{LABEL_BASE_URL}?RecNumAndPort={recipe_id}"
        res = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        page_text = soup.get_text()
        
        # Flexibly extract integers adjacent to macro markers
        cal_match = re.search(r'Calories\s+(\d+)', page_text) or re.search(r'Calories:\s*(\d+)', page_text)
        prot_match = re.search(r'Protein\s+(\d+)', page_text) or re.search(r'Protein:\s*(\d+)', page_text)
        
        if cal_match and prot_match:
            return {"calories": int(cal_match.group(1)), "protein": int(prot_match.group(1))}
    except Exception:
        pass
    return None

def optimize_meal_selection(available_items, target_calories=800):
    if not available_items: 
        return ["No food items scraped for this section."]
    
    prob = LpProblem("J2_Optimize", LpMaximize)
    
    # FIX: Use clean alphanumeric index keys instead of Python's unstable hash() function
    item_vars = {}
    for i, item in enumerate(available_items):
        safe_key = f"item_{i}"
        item_vars[safe_key] = LpVariable(safe_key, 0, 2, cat='Integer')
        item['var_key'] = safe_key

    # Objective Function
    prob += lpSum([item_vars[item['var_key']] * item['protein'] for item in available_items])
    # Constraint
    prob += lpSum([item_vars[item['var_key']] * item['calories'] for item in available_items]) <= target_calories
    
    prob.solve()
    
    # Fallback checking if the solver can't find a perfect fit
    status = LpStatus[prob.status]
    if status != "Optimal":
        print(f"[WARNING] Solver returned non-optimal status: {status}. Sorting by raw protein density instead.")
        # Fallback list: return the top 3 highest protein items instead of failing
        sorted_items = sorted(available_items, key=lambda x: x['protein'], reverse=True)[:3]
        return [f"1x {item['name']} ({item['protein']}g P / {item['calories']} kcal) [Fallback Selection]" for item in sorted_items]

    recommendations = []
    for item in available_items:
        v = item_vars[item['var_key']].varValue
        if v and v > 0:
            recommendations.append(f"{int(v)}x {item['name']} ({item['protein']}g P / {item['calories']} kcal)")
            
    return recommendations if recommendations else ["Could not compute ideal targets with current menu constraints."]

if __name__ == "__main__":
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    
    try:
        data = fetch_daily_menu()
        
        message = "**🎰 J2 DAILY OPTIMIZATION MATRIX** 🎰\n\n"
        for meal in ['Lunch', 'Dinner']:
            items = data.get(meal, [])
            print(f"[DEBUG] Processing optimization for {meal}. Found {len(items)} eligible foods.")
            recs = optimize_meal_selection(items)
            
            message += f"**__{meal.upper()}__**\n" + "\n".join(recs) + "\n\n"
            
        requests.post(webhook_url, json={"content": message}, timeout=10)
        print("[DEBUG] Payload successfully deployed to Discord.")
    except Exception as e:
        if webhook_url:
            requests.post(webhook_url, json={"content": f"⚠️ Execution Crash: {str(e)}"}, timeout=10)