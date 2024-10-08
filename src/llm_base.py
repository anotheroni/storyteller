from abc import ABC, abstractmethod

class LLMBase(ABC):
    def __init__(self, name, address, system_prompt):
        self.name = name
        self.address = address
        self.system_prompt = system_prompt

    @abstractmethod
    def generate(self, prompt, max_length=1024):
        pass

    @abstractmethod
    def count_tokens(self, text):
        pass

    @abstractmethod
    def test_connection(self):
        pass

    @abstractmethod
    def get_config(self):
        pass

    @classmethod
    @abstractmethod
    def from_config(cls, config):
        pass

    @staticmethod
    @abstractmethod
    def get_type():
        pass

    @staticmethod
    def create_llm(config):
        llm_type = config.get('type')
        if llm_type == 'Kobold':
            from src.llm_kobold import LLMKobold
            return LLMKobold.from_config(config)
        elif llm_type == 'OpenAI':
            from src.llm_openai import LLMOpenAI
            return LLMOpenAI.from_config(config)
        else:
            raise ValueError(f"Unknown LLM type: {llm_type}")
