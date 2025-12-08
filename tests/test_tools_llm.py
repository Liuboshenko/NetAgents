import requests
import json

# URL сервера
url = "http://10.27.192.116:8080/v1/chat/completions"

# Определение tools (пример: инструмент для получения погоды)
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit of temperature"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

# Пример реализации самого tool (симуляция выполнения функции на стороне клиента)
def execute_tool(tool_call):
    """
    Это пример реализации выполнения tool. В реальности здесь можно вызвать API или выполнить логику.
    Для теста - симулируем ответ.
    """
    name = tool_call["name"]
    arguments = json.loads(tool_call["arguments"])  # Аргументы как JSON

    if name == "get_current_weather":
        location = arguments.get("location", "Unknown")
        unit = arguments.get("unit", "celsius")
        # Симуляция: возвращаем фейковый результат
        return json.dumps({
            "location": location,
            "temperature": 22 if unit == "celsius" else 72,
            "unit": unit,
            "forecast": ["sunny", "windy"]
        })
    else:
        return json.dumps({"error": "Unknown tool"})

# Начальные messages
messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant that can use tools to get information."
    },
    {
        "role": "user",
        "content": "What's the weather like in Moscow?"
    }
]

# Базовый payload
payload = {
    "model": "Qwen3-14B-Q5_0",
    "messages": messages,
    "tools": tools,  # Добавляем tools
    "temperature": 0.7,
    "max_tokens": 512,
    "stream": False,
    "enable_thinking": True,  # Включаем thinking для размышлений модели
}

# Функция для отправки запроса и обработки ответа
def send_request(payload):
    print("=== ШАГ: Отправка запроса в модель ===")
    print("То, что мы отправляем в модель (payload):")
    print(json.dumps(payload, indent=4, ensure_ascii=False))
    print("\n")

    response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload))
    
    print("=== ШАГ: Получен ответ от модели ===")
    print(f"Статус-код ответа: {response.status_code}")
    
    if response.status_code == 200:
        response_json = response.json()
        print("[RAW_RESPONSE] Сырой ответ от модели (JSON):")
        print(json.dumps(response_json, indent=4, ensure_ascii=False))
        print("\n")
        return response_json
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        print("\n")
        return None

# Шаг 1: Отправляем начальный запрос с tools
print("=== НАЧАЛО ПАЙПЛАЙНА: Подготовка и отправка начального запроса ===")
print("Описание: Мы отправляем исходные сообщения и список tools. Модель решит, нужно ли вызвать tool.\n")
initial_response = send_request(payload)

if initial_response:
    # Проверяем, есть ли tool_calls в ответе
    assistant_message = initial_response["choices"][0]["message"]
    
    print("=== ШАГ: Анализ ответа модели ===")
    print("Сообщение от ассистента из ответа:")
    print(json.dumps(assistant_message, indent=4, ensure_ascii=False))
    print("\n")
    
    if "tool_calls" in assistant_message and assistant_message["tool_calls"]:
        print("=== ШАГ: Обнаружены вызовы tools ===")
        print("Описание: Модель решила использовать tool(s). Теперь мы выполним их локально и добавим результаты в сообщения.\n")

        # Для каждого tool_call выполняем и собираем responses
        tool_responses = []
        for tool_call in assistant_message["tool_calls"]:
            # Извлекаем function (в шаблоне tool_call.function)
            if "function" in tool_call:
                tool_call = tool_call["function"]
            
            print(f"=== ШАГ: Выполнение tool '{tool_call['name']}' ===")
            print(f"Аргументы tool: {tool_call['arguments']}")
            
            # Выполняем tool (здесь - наша реализация)
            result = execute_tool(tool_call)
            print(f"Результат выполнения tool: {result}\n")

            # Добавляем message role="tool"
            tool_responses.append({
                "role": "tool",
                "content": result
            })

        # Обновляем messages: добавляем assistant message (с tool_calls) и tool responses
        print("=== ШАГ: Обновление списка сообщений для второго запроса ===")
        print("Описание: Добавляем сообщение ассистента с tool_calls и ответы от tools.\n")
        
        updated_messages = payload["messages"].copy()
        updated_messages.append({
            "role": "assistant",
            "content": assistant_message.get("content", ""),
            "reasoning_content": assistant_message.get("reasoning_content", ""),
            "tool_calls": assistant_message["tool_calls"]  # Добавляем для шаблона
        })
        updated_messages.extend(tool_responses)
        
        print("Обновлённый список messages:")
        print(json.dumps(updated_messages, indent=4, ensure_ascii=False))
        print("\n")

        # Шаг 2: Отправляем новый запрос с обновленными messages (без tools, если не нужны повторно)
        payload["messages"] = updated_messages
        payload.pop("tools", None)  # Убираем tools, если цикл завершен
        
        print("=== ШАГ: Подготовка и отправка второго (follow-up) запроса ===")
        print("Описание: Теперь модель получит результаты tools и сгенерирует финальный ответ.\n")
        final_response = send_request(payload)

        if final_response:
            # Финальный контент от assistant
            final_assistant_message = final_response["choices"][0]["message"]
            print("=== ШАГ: Финальный анализ ответа ===")
            print("Финальное сообщение от ассистента:")
            print(json.dumps(final_assistant_message, indent=4, ensure_ascii=False))
            print("\n")
            
            final_content = final_assistant_message["content"]
            print(f"=== КОНЕЦ ПАЙПЛАЙНА: Финальный ответ ассистента: {final_content} ===")
    else:
        # Если нет tool_calls, это финальный ответ
        print("=== ШАГ: Нет вызовов tools ===")
        print("Описание: Модель ответила напрямую без использования tools.\n")
        print("Финальный ответ ассистента:")
        print(assistant_message["content"])
        print("=== КОНЕЦ ПАЙПЛАЙНА ===")
else:
    print("=== КОНЕЦ ПАЙПЛАЙНА: Ошибка в начальном запросе ===")