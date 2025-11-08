# config.py
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import logging

logger = logging.getLogger(__name__)


# Default configuration values
DEFAULT_LLM_BASE_URL = "http://10.27.192.116:8080/v1"
DEFAULT_LLM_MODEL = "Qwen3-14B-Q5_0"
DEFAULT_LLM_API_KEY = "sk-no-key-required"
DEFAULT_MAX_TOKENS = 32768
DEFAULT_TEMPERATURE = 0.7
DEFAULT_CACHE_SEED = None
DEFAULT_CODE_EXECUTION_CONFIG = {"use_docker": False}
TERMINATION_MSG = "TERMINATE"

# Updated Prompt templates
DOMINANT_PROMPT = """
Вы - DominantAgent. Планируйте по шагам: [REASON] рассуждение, [ACT] действие.
Используйте state для хранения данных. Всегда проверяйте доступность хоста перед выполнением команд.
Делегируйте: Network для ping/netmiko_show/netmiko_set, Analyzers для анализа. Выберите лучший анализ.
Определите команду (show или set) на основе запроса. Для обновлений state возвращайте чистый JSON в формате {"command": "команда или список", "command_type": "show/set"}.
Для запроса пользователя: покажи статус интерфейсов на хосте используй команду show interface brief
Eсли пользователь просит показать соседство на хосте используй команду 'show bgp neighbors' или 'show bgp summary'
Если пользователь просит показать Qos или таблицу качества обслуживания или таблицу qos на хосте, используй команду 'show qos classifiers dscp'
Если на вход в качестве промта поступил большой кусок данных и его нужно дальше передать по pipeline между агентами то не сокращай данные а передавай в исходном виде.
После завершения задачи верните результат на русском языке и завершите ответ словом TERMINATE.
"""

NETWORK_PROMPT = """
Вы - NetworkAgent. [REASON] о задаче, [ACT] вызов инструментов (ping_host, netmiko_show, netmiko_set).
Выполните инструмент, дождитесь результата, затем верните JSON в формате {"ping_result": "результат"} или {"show_result": "результат"} или {"set_result": "результат"}.
Завершите ответ словом TERMINATE.
"""

ANALYZER_PROMPT_TEMPLATE = """
Вы - Analyzer-{id}. Анализируйте данные из state (конфигурацию или результат). [REASON] о рисках/статусе, [ACT] генерируйте JSON анализ.
Конкурируйте: будьте глубже и профессиональнее других.
После генерации JSON завершите ответ словом TERMINATE.
"""

@dataclass
class SystemConfig:
    """Configuration class for the CoopetitionSystem, holding LLM and agent settings."""
    
    llm_base_url: str = field(default=DEFAULT_LLM_BASE_URL)
    llm_model: str = field(default=DEFAULT_LLM_MODEL)
    llm_api_key: str = field(default=DEFAULT_LLM_API_KEY)
    max_tokens: int = field(default=DEFAULT_MAX_TOKENS)
    temperature: float = field(default=DEFAULT_TEMPERATURE)
    cache_seed: Optional[int] = field(default=DEFAULT_CACHE_SEED)
    code_execution_config: Dict[str, Any] = field(default_factory=lambda: DEFAULT_CODE_EXECUTION_CONFIG)
    dominant_prompt: str = field(default=DOMINANT_PROMPT)
    network_prompt: str = field(default=NETWORK_PROMPT)  # Renamed from scanner_prompt
    analyzer_prompt_template: str = field(default=ANALYZER_PROMPT_TEMPLATE)
    termination_msg: str = field(default=TERMINATION_MSG)

    def __post_init__(self):
        """Validates configuration fields after initialization.

        Raises:
            ValueError: If max_tokens or temperature are out of valid ranges.
        """

        logger.info(f"LLM config: {self.__dict__}")

        if not (0 < self.max_tokens <= 65536):
            raise ValueError(f"max_tokens must be between 1 and 16384, got {self.max_tokens}")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(f"temperature must be between 0.0 and 2.0, got {self.temperature}")
        if not self.llm_base_url.startswith("http"):
            raise ValueError(f"llm_base_url must be a valid URL, got {self.llm_base_url}")