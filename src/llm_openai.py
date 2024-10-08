# src/llm_openai.py

import openai
import os
from src.llm_base import LLMBase

class LLMOpenAI(LLMBase):
    def __init__(self, name, address, api_key, system_prompt, use_env_var=False):
        super().__init__(name, address, system_prompt)
        self.api_key = api_key
        self.use_env_var = use_env_var

    def generate(self, prompt, max_length=1024):
        try:
            self._set_api_key()
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=max_length
            )
            return response.choices[0].text.strip()
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def count_tokens(self, text):
        try:
            # Use an approximate count for now
            return len(text.split())
        except Exception:
            return -1

    def test_connection(self):
        try:
            self._set_api_key()
            openai.Model.list()  # Attempt a simple API call to test connection
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def _set_api_key(self):
        if self.use_env_var:
            openai.api_key = os.getenv(self.api_key)
        else:
            openai.api_key = self.api_key
        if self.address:
            openai.api_base = self.address

    def get_config(self):
        return {
            'name': self.name,
            'address': self.address,
            'api_key': self.api_key,
            'system_prompt': self.system_prompt,
            'use_env_var': self.use_env_var,
            'type': self.get_type()
        }

    @classmethod
    def from_config(cls, config):
        return cls(config['name'], config['address'], config['api_key'], config['system_prompt'], config.get('use_env_var', False))

    @staticmethod
    def get_type():
        return 'OpenAI'
