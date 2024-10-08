# src/llm_kobold.py

import requests
import json
from src.llm_base import LLMBase

class LLMKobold(LLMBase):
    def __init__(self, name, address, system_prompt):
        super().__init__(name, address, system_prompt)

    def generate(self, prompt, max_length=1024):
        url = f"{self.address}/api/v1/generate"
        headers = {'Content-Type': 'application/json'}
        data = {
            "prompt": prompt,
            "max_length": max_length
        }
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            response_data = response.json()
            return response_data["results"][0]["text"].strip()
        else:
            return f"Error generating response: {response.status_code}"

    def count_tokens(self, text):
        url = f"{self.address}/api/extra/tokencount"
        headers = {'Content-Type': 'application/json'}
        data = {"prompt": text}
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            response_data = response.json()
            return response_data["value"]
        else:
            return -1

    def test_connection(self):
        try:
            response = requests.get(f"{self.address}/api/v1/version")
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_config(self):
        return {
            'name': self.name,
            'address': self.address,
            'system_prompt': self.system_prompt,
            'type': self.get_type()
        }

    @classmethod
    def from_config(cls, config):
        return cls(config['name'], config['address'], config['system_prompt'])

    @staticmethod
    def get_type():
        return 'Kobold'
