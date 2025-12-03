import requests
import json

# URL сервера
url = "http://10.27.192.116:8080/v1/chat/completions"

# Пример JSON-запроса с messages (основан на вашем шаблоне)
payload = {
    "model": "Qwen3-14B-Q5_0",  # Имя модели (опционально, если сервер знает)
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Tell me a joke about programming."
        }
    ],
    "temperature": 1,  # Температура (опционально)
    "max_tokens": 256,   # Максимальное количество токенов
    "stream": False,      # Не стримить ответ
    "enable_thinking": False,
}

# Если хотите протестировать с tools, раскомментируйте и добавьте:
# payload["tools"] = [
#     {
#         "type": "function",
#         "function": {
#             "name": "get_weather",
#             "description": "Get the current weather in a city",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "city": {"type": "string", "description": "The city name"}
#                 },
#                 "required": ["city"]
#             }
#         }
#     }
# ]

# Отправка POST-запроса
response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload))

# Проверка статуса
if response.status_code == 200:
    # Вывод сырого JSON-ответа
    print("Raw response from model:")
    print(json.dumps(response.json(), indent=4))
else:
    print(f"Error: {response.status_code} - {response.text}")