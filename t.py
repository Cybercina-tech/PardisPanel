import requests

currency_list = ["GBP_BUY", "GBP_SELL", "USDT_BUY", "USDT_SELL"]


URL = "https://sarafipardis.co.uk/wp-json/pardis/v1/rates"

payload = {
    "api_key": "PX9k7mN2qR8vL4jH6wE3tY1uI5oP0aS9dF7gK2mN8xZ4cV6bQ1wE3rT5yU8iO0pL",
    "currency": "USDT_SELL",
    "rate": 46000
}

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(URL, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    print("Success:", response.json())
except requests.exceptions.RequestException as e:
    print("Request failed:", e)
