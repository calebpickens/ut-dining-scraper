import requests

URL = "https://hf-foodpro.austin.utexas.edu/foodpro/shortmenu.aspx?sName=University+Housing+and+Dining&locationNum=12&locationName=J2+Dining&naFlag=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

if __name__ == "__main__":
    print(f"[TEST] Sending exactly one GET request to UT FoodPro...")
    
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        print(f"\n[RESULT] HTTP Status Code: {response.status_code}")
        
        # Print a small snippet of the page to verify it's actual HTML and not a Cloudflare/WAF captcha page
        print(f"[RESULT] HTML Snippet: {response.text[:250].strip()}")
        
    except requests.exceptions.RequestException as e:
        print(f"\n[FATAL ERROR] Connection dropped: {e}")