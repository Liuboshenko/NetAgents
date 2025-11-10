# Updated orchestrator.py with improved streaming and formatting
import logging, time
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Generator
from autogen import UserProxyAgent, AssistantAgent, register_function
from autogen.coding import LocalCommandLineCodeExecutor
from config import SystemConfig
from agents import create_dominant_agent, create_network_agent, create_analyzer_agent
from state import SystemState
from tools import ping_host, netmiko_show, netmiko_set  # Removed port_scan if not needed; add if required

logger = logging.getLogger(__name__)

class CoopetitionSystem:
    """Manages a cooperative-competitive system for processing queries with multiple agents."""
    
    DEFAULT_IP = "10.27.192.116"
    STEPS = ["ping", "credential_check", "determine_command", "execute", "analyze"]  # Изменено: убрали "select" для consistency

    def __init__(self, config: SystemConfig):
        """Initializes the system with configuration, state, and agents.

        Args:
            config (SystemConfig): Configuration object containing system settings.
        """
        self.config = config
        self.state = SystemState()
        self.code_executor = self._setup_code_executor()
        self.config.code_execution_config = {"executor": self.code_executor}
        self.dominant: AssistantAgent = None
        self.network: AssistantAgent = None
        self.analyzer1: AssistantAgent = None
        #self.analyzer2: AssistantAgent = None
        self._setup_agents()

    def _setup_code_executor(self) -> LocalCommandLineCodeExecutor:
        """Sets up the code executor with a workspace directory.

        Returns:
            LocalCommandLineCodeExecutor: Configured code executor.
        """
        work_dir = Path("workspace")
        work_dir.mkdir(exist_ok=True)
        return LocalCommandLineCodeExecutor(work_dir=str(work_dir), timeout=60)

    def _setup_agents(self) -> None:
        """Initializes all agents using the provided configuration and state."""
        self.dominant = create_dominant_agent(self.config, self.state)
        self.network = create_network_agent(self.config, self.state)
        self.analyzer1 = create_analyzer_agent(1, self.config, self.state)
        #self.analyzer2 = create_analyzer_agent(2, self.config, self.state)

    def _create_user_proxy(self) -> UserProxyAgent:

        return UserProxyAgent(
            name="UserProxy",
            human_input_mode="NEVER",
            code_execution_config=self.config.code_execution_config,
            is_termination_msg=lambda x: isinstance(x, dict) and "content" in x and isinstance(x["content"], str) and x["content"].rstrip().endswith(self.config.termination_msg),
        )

    def _register_tools(self, user_proxy: UserProxyAgent) -> None:

        for func, desc in [(ping_host, ping_host.__doc__), (netmiko_show, netmiko_show.__doc__), (netmiko_set, netmiko_set.__doc__)]:
            register_function(
                func,
                caller=self.network,
                executor=user_proxy,
                name=func.__name__,
                description=desc
            )

    def _parse_json_response(self, response: Dict, step: str, key: str) -> Dict:

        try:
            content = response.get("content", "").split("TERMINATE")[0].strip()  # Добавлено: get с default для защиты
            if not content:
                raise ValueError("Empty content in response")
            return json.loads(content)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse JSON from Network in step {step}: {response}")
            raise ValueError(f"Invalid JSON from Network in step {step}: {str(e)}")

    def process_query_stream(self, user_query: str) -> Generator[str, None, None]:

        try:
            self.state.update("query", user_query)
            ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', user_query)
            ip = ip_match.group(1) if ip_match else self.DEFAULT_IP
            self.state.update("ip", ip)
            # Hardcoded credentials for demo; replace with secure loading
            self.state.update("credentials", {"username": "wbos", "password": "welcome", "device_type": "cisco_ios"})

            user_proxy = self._create_user_proxy()
            self._register_tools(user_proxy)

            start_message = f"🔄 **Начинаю обработку запроса...**\n"            
            yield "<think>\n"

            for char in start_message:
                time.sleep(0.013)
                yield char      
            #yield f"**Начинаю обработку запроса...**\n"
            yield f"Запрос: {user_query}\n"
            #yield f"IP: {ip}\n"
            yield "</think>\n"

            # Обновлённый список шагов: убрали "select"
            self.STEPS = ["ping", "credential_check", "determine_command", "execute", "analyze"]  # Изменение: удалён "select"

            for step in self.STEPS:
                self.state.advance_step(step)
                logger.info(f"Current step: {step}, State: {self.state.data}")
                yield "<think>\n"
                yield f"**Шаг: {step}**\n"
                #yield f"Состояние: ```json\n{json.dumps(self.state.data, indent=2, ensure_ascii=False)}\n```\n"
                yield "</think>\n"

                if step == "ping":
                    check_ping_message = f"🏓 Проверяю доступность хоста {ip} с помощью ping...\n"
                    yield "<think>\n"

                    for char in check_ping_message:
                        time.sleep(0.013)
                        yield char

                    #yield f"🏓 Проверяю доступность хоста **{ip}** с помощью ping ...\n"
                    yield "</think>\n"
                    user_proxy.initiate_chat(self.network, message=f"Выполни ping на IP {ip}. Обнови state.")
                    last_message = self.network.last_message()
                    if isinstance(last_message, dict) and "tool_calls" in last_message:
                        tool_response = user_proxy.last_message()["content"]
                        print(f"Ответ инструмента: {tool_response}\n")
                        yield "<think>\n"
                        yield f"Ответ инструмента: {tool_response}\n"
                        yield "</think>\n"
                        result_json = self._parse_json_response({"content": tool_response}, "ping", "ping_result")
                    else:
                        yield "<think>\n"
                        #yield f"Ответ Network: ```json\n{json.dumps(last_message, indent=2, ensure_ascii=False)}\n```\n"
                        yield "</think>\n"
                        result_json = self._parse_json_response(last_message, "ping", "ping_result")
                    self.state.update("ping_result", result_json.get("ping_result", "Нет результата"))
                    yield "<think>\n"
                    yield f"**Результат ping: {self.state.get('ping_result')}**\n"
                    if "unreachable" in self.state.get('ping_result').lower():
                        raise ValueError("Хост недоступен.")
                    yield "Хост доступен, перехожу к следующему шагу.\n"
                    yield "</think>\n"


#################################################################
                elif step == "credential_check":
                    credes_check_message = f"🔍 Проверяю наличие данных для входа на хост **{ip}**...\n"
                    yield "<think>\n"

                    for char in credes_check_message:
                        time.sleep(0.013)
                        yield char

                    #yield f"Проверяю наличие данных для входа на хост {ip}...\n"
                    yield "</think>\n"
                    creds = self.state.get("credentials")
                    if creds and all(key in creds for key in ["username", "password", "device_type"]):
                        self.state.update("credential_status", "Доступны")
                        yield "<think>\n"
                        yield "Данные для входа доступны, перехожу к следующему шагу.\n"
                        yield "</think>\n"
                    else:
                        raise ValueError("Нет данных для входа.")

                elif step == "determine_command":
                    determ_cmd_message = "🧩 Определяю подходящую команду для запроса ...\n"
                    yield "<think>\n"
                    for char in determ_cmd_message:
                        time.sleep(0.013)
                        yield char
                    
                    #yield "🧩 Определяю подходящую команду для запроса ...\n"
                    yield "</think>\n"
                    user_proxy.initiate_chat(self.dominant, message=f"Определи подходящую команду (show или set) для запроса: {user_query}. Обнови state с 'command' (строка или список для set) и 'command_type' (show/set).")
                    determine_content = self.dominant.last_message()["content"]
                    yield "<think>\n"
                    #yield f"Ответ Dominant: ```\n{determine_content}\n```\n"
                    yield "</think>\n"
                    try:
                        content = determine_content.split("TERMINATE")[0].strip()
                        # Ищем JSON-подобный блок (после [ACT] или напрямую)
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            det_json = json.loads(json_match.group(0))
                        else:
                            # Альтернативный парсинг из текста, если нет чистого JSON
                            command_line = re.search(r'command`?: (.*)', content)
                            type_line = re.search(r'command_type`?: (.*)', content)
                            if command_line and type_line:
                                command = command_line.group(1).strip('"')
                                command_type = type_line.group(1).strip('"')
                                det_json = {"command": command, "command_type": command_type}
                            else:
                                raise ValueError("Не удалось извлечь команду из ответа DominantAgent")
                        
                        self.state.update("command", det_json.get("command"))
                        self.state.update("command_type", det_json.get("command_type", "show"))
                        yield "<think>\n"
                        yield f"Команда: **{self.state.get('command')}**, Тип: {self.state.get('command_type')}\n"
                        
                        for char in "Команда определена, перехожу к следующему шагу.\n":
                            time.sleep(0.013)
                            yield char
                        #yield "Команда определена, перехожу к следующему шагу.\n"
                        yield "</think>\n"
                    except Exception as e:
                        raise ValueError(f"Не удалось определить команду: {str(e)}")
                    

                ############# execute stage ########################
                elif step == "execute":
                    command = self.state.get("command")
                    command_type = self.state.get("command_type")
                    creds = self.state.get("credentials")
                    exec_cmd_message = f"⏳ Выполняю команду **'{command}'** на wbos@{ip} ...\n"
                    yield "<think>\n"
                    for char in exec_cmd_message:
                        time.sleep(0.013)
                        yield char
                    #yield f"⏳ Выполняю команду **'{command}'** на wbos@{ip} ...\n"
                    yield "</think>\n"
                    tool_name = "netmiko_show" if command_type == "show" else "netmiko_set"
                    message = f"Выполни {tool_name} на IP {ip} с командой {command} и credentials {json.dumps(creds)}."
                    user_proxy.initiate_chat(self.network, message=message)
                    
                    # Изменено: Захватите сырой output из истории чата self.network
                    raw_tool_output = None
                    chat_history = self.network.chat_messages.get(user_proxy, [])  # Получаем список сообщений от user_proxy к network
                    for msg in chat_history:
                        # Изменено: Добавлена проверка на наличие и не-None content
                        if "content" in msg and msg["content"] is not None and "Response from calling tool" in msg["content"]:
                            # Извлеките полный output (он между ***** Response ... ***** и ***** )
                            try:
                                print(f'raw_tool_output_for_artem: {raw_tool_output}')
                                raw_tool_output = msg["content"].split("***** Response from calling tool")[1].split("*****")[1].strip()
                            except IndexError:
                                raw_tool_output = msg["content"].strip()  # Fallback, если парсинг не удался
                            break  # Прерываем после нахождения
                    
                    # Добавлено: Отладка, если raw_tool_output не найден (можно убрать позже)
                    if raw_tool_output is None:
                        logger.warning("Не удалось найти сырой output в истории чата. Использую parsed результат.")
                    
                    last_message = self.network.last_message()
                    print(f"*********************************************************************** last_message ********************************************************************************\n {last_message}")
                    
                    if isinstance(last_message, dict) and "tool_calls" in last_message:
                        tool_response = user_proxy.last_message()["content"]
                        yield "<think>\n"
                        yield f"Ответ инструмента: {tool_response}\n"
                        yield "</think>\n"
                        result_json = self._parse_json_response({"content": tool_response}, "execute", f"{command_type}_result")
                    else:
                        yield "<think>\n"
                        #yield f"Ответ Network: ```json\n{json.dumps(last_message, indent=2, ensure_ascii=False)}\n```\n"
                        yield "</think>\n"
                        result_json = self._parse_json_response(last_message, "execute", f"{command_type}_result")
                        print(f"************VIEW ********** result_json *********** \n {result_json}")
                    
                    # Используйте сырой output, если он доступен (fallback на parsed, если нет)
                    execute_result = raw_tool_output or result_json.get(f"{command_type}_result", "Нет результата")
                    self.state.update("execute_result", execute_result)
                    yield "<think>\n"
                    #yield f"Результат выполнения: {execute_result}\n"  # Теперь полный
                    yield "Команда выполнена, перехожу к анализу.\n"
                    yield "</think>\n"
                    
                    # Display the raw tool output to the user immediately as plain text
                    if execute_result:
                        execute_result_char = f"Результат выполнения команды:\n```\n{execute_result}\n```\n"
                        for char in execute_result_char:
                            time.sleep(0.0095) 
                            yield char                    
                        #yield f"Результат выполнения команды:\n```\n{execute_result}\n```\n"
##############################################################################################################
                elif step == "analyze":
                    if not self.state.get("execute_result"):
                        raise ValueError("Нет результата выполнения для анализа.")
                    # Изменение: убрали список analyses и цикл; используем только один анализатор (analyzer1)
                    start_analysis_message = f"🧠 Начинаю анализ с {self.analyzer1.name} ...\n"
                    yield "<think>\n"
                    for char in start_analysis_message:
                        time.sleep(0.013)
                        yield char
                    #yield f"🧠 Начинаю анализ с {self.analyzer1.name}...\n"
                    yield "</think>\n"
                    user_proxy.initiate_chat(self.analyzer1, message=f"Анализируй данные из state: {self.state.get('execute_result')}")
                    analysis_content = self.analyzer1.last_message()["content"]
                    yield "<think>\n"
                    #yield f"Ответ {self.analyzer1.name}: ```json\n{analysis_content}\n```\n"
                    yield "</think>\n"
                    analysis = analysis_content.split("TERMINATE")[0].strip()
                    # Изменено: убрали self.state.update("analysis", analysis) — храним как локальную переменную, чтобы избежать ошибки валидации
                    # yield "<think>\n"
                    # #yield f"Анализ добавлен: {analysis}\n"
                    # yield "Анализ завершен, подвожу резюме.\n"
                    # yield "</think>\n"
                    
                    # Изменение: вместо шага "select" сразу формируем резюме и отдаём ответ
                    # Здесь можно использовать DominantAgent или просто сгенерировать резюме на основе анализа
                    # Для примера: используем Dominant для формирования финального ответа
                    finally_analysis_message = "📊 Анализ завершен, подвожу резюме на основе анализа ...\n"
                    yield "<think>\n"
                    for char in finally_analysis_message:
                        time.sleep(0.013)
                        yield char
                    #yield "Анализ завершен, подвожу резюме на основе анализа ...\n"
                    yield "</think>\n"
                    user_proxy.initiate_chat(self.dominant, message=f"Сформируй финальный ответ на русском на основе анализа: {analysis} и результата выполнения: {self.state.get('execute_result')}. пусть ответ будет структурированным и разделен по логике повествования а так же пусть будут строгие эмодзи обозначающие разделы ответа")
                    summary_content = self.dominant.last_message()["content"]
                    yield "<think>\n"
                    #yield f"Резюме: ```\n{summary_content}\n```\n"
                    yield "</think>\n"
                    final_response = summary_content.split("TERMINATE")[0].strip()
                    print(final_response)
                    self.state.update("best_analysis", final_response)  # Изменено: используем "best_analysis" вместо "final_response" для совместимости с валидацией state
                    # Stream final response
                    for char in final_response:
                        time.sleep(0.0095) 
                        yield char
                    yield "\n"

                # Check for errors
                last_message = self.state.get("best_analysis") or self.state.get("execute_result") or self.state.get("ping_result")  # Изменено: используем "best_analysis" вместо "final_response"
                if last_message and isinstance(last_message, str) and "error" in last_message.lower():
                    raise ValueError(f"Ошибка на шаге {step}: {last_message}")
        except Exception as e:
            logger.error(f"Error: {e}")
            yield "<think>\n"
            yield f"Произошла ошибка: {str(e)}\n"
            yield "</think>\n"

    def process_query(self, user_query: str) -> str:
        """Non-streaming version for compatibility."""
        chunks = list(self.process_query_stream(user_query))
        return "".join(chunks)