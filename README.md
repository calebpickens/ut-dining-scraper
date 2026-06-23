# 🥩 Autonomous Dining Hall Macro Optimizer

A serverless Python pipeline that scrapes university dining hall menus, bypasses enterprise web application firewalls (WAF), and utilizes an LLM to generate an optimized, high-protein daily meal plan delivered directly to Discord.

## 🚀 The Architecture

Traditional scraping methods against the university's FoodPro software trigger an HTTP 403 Forbidden block when executed from cloud data centers (like Azure/GitHub) due to aggressive rate-limiting on the hidden `label.aspx` macro pages. 

This project circumvents the firewall by:
1. Executing a single, stealthy `GET` request to extract the raw, unstructured HTML of the daily menu.
2. Passing the unstructured text to **Google's Gemini 2.5 Flash API**.
3. Utilizing prompt engineering to heuristically parse the menu, estimate the macronutrients, and mathematically optimize a 1500-calorie, high-protein payload.
4. Dispatching the formatted results via a **Discord Webhook**.

*This entire process runs autonomously every morning at 6:30 AM via GitHub Actions.*

## 📸 Output Demonstration

*(Insert a screenshot of the Discord output here)*

## 🛠️ Tech Stack
* **Language:** Python 3.x
* **Parsing:** BeautifulSoup4, Requests
* **AI Integration:** Google Generative AI SDK (`google-genai`)
* **Automation:** GitHub Actions (cron scheduling)

## ⚙️ Deployment Instructions

To deploy your own instance of this optimizer:

1. **Fork** this repository.
2. Obtain a free [Google AI Studio API Key](https://aistudio.google.com/).
3. Create a [Discord Webhook URL](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) in your private server.
4. Navigate to your repository's **Settings** > **Secrets and variables** > **Actions**.
5. Add the following Repository Secrets:
   * `GEMINI_API_KEY`: Your Google API key.
   * `DISCORD_WEBHOOK`: Your Discord webhook URL.
6. The GitHub Action will automatically trigger daily at 06:30 AM server time, or you can trigger it manually via the **Actions** tab.

## ⚠️ Security Notice
Never hardcode your API keys or Webhook URLs directly into `main.py`. This repository relies exclusively on environment variables injected at runtime to maintain cryptographic hygiene.