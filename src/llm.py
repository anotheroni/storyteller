import requests
import json
import openai

from src.llm_kobold import LLMKobold
from src.llm_openai import LLMOpenAI

from PyQt5.QtCore import QObject

class LLMManager:
    def __init__(self):
        self.llms = []
        self.token_count_llm_name = None

    def load_llm_config(self):
        try:
            with open('llm_config.json', 'r') as f:
                data = json.load(f)
                for llm_data in data.get('llms', []):
                    llm = self.create_llm(llm_data)
                    if llm and llm.test_connection():
                        self.llms.append(llm)
                self.token_count_llm_name = data.get('token_count_llm_name', None)
        except FileNotFoundError:
            pass  # No config file yet

    def create_llm(self, llm_data):
        llm_type = llm_data.get('type', 'Kobold')
        if llm_type == 'Kobold':
            return LLMKobold(
                llm_data['name'],
                llm_data.get('address', ''),
                llm_data.get('system_prompt', '')
            )
        elif llm_type == 'OpenAI':
            return LLMOpenAI(
                llm_data['name'],
                llm_data.get('api_key', ''),
                llm_data.get('system_prompt', ''),
                llm_data.get('use_env_var', False)
            )
        return None

    def save_llm_config(self):
        data = {
            'llms': [
                {
                    'name': llm.name,
                    'system_prompt': llm.system_prompt,
                    'type': llm.__class__.__name__,
                    'address': getattr(llm, 'address', ''),
                    'api_key': getattr(llm, 'api_key', ''),
                    'use_env_var': getattr(llm, 'use_env_var', False)
                } for llm in self.llms
            ],
            'token_count_llm_name': self.token_count_llm_name
        }
        with open('llm_config.json', 'w') as f:
            json.dump(data, f)


class CountTask(QObject):
    def __init__(self, data, source, llm_backend):
        super(CountTask, self).__init__()
        self.data = data
        self.source = source
        self.llm_backend = llm_backend

    def execute(self):
        if self.llm_backend.type == 'Kobold':
            tokenCountUrl = f"{self.llm_backend.address}/api/extra/tokencount"
            headers = {'Content-Type': 'application/json'}
            response = requests.post(tokenCountUrl, headers=headers, data=json.dumps({"prompt":self.data}))
            if response.status_code == 200:
                response_data = json.loads(response.text)
                self.source.onTokensCounted(response_data["value"])
            else:
                self.source.onTokensCounted(-1)
        elif self.llm_backend.type == 'OpenAI':
            # Approximate token count for OpenAI models
            count = len(self.data.split())
            self.source.onTokensCounted(count)

class GenerateTask(QObject):
    def __init__(self, data, source, llm_backend):
        super(GenerateTask, self).__init__()
        self.data = data
        self.source = source
        self.llm_backend = llm_backend

    def execute(self):
        if self.llm_backend.type == 'Kobold':
            generateUrl = f"{self.llm_backend.address}/api/v1/generate"
            headers = {'Content-Type': 'application/json'}
            prompt = json.dumps({
                "prompt": self.data,
                "max_length": 1024
            })
            response = requests.post(generateUrl, headers=headers, data=prompt)
            if response.status_code == 200:
                response_data = json.loads(response.text)
                self.source.onResponseGenerated(response_data["results"][0]["text"].strip())
            else:
                self.source.onResponseGenerated("Error generating response")
        elif self.llm_backend.type == 'OpenAI':
            openai.api_key = self.llm_backend.address  # In this context, address holds the API key
            try:
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=self.llm_backend.system_prompt + "\n\n" + self.data,
                    max_tokens=1024
                )
                text = response.choices[0].text.strip()
                self.source.onResponseGenerated(text)
            except Exception as e:
                self.source.onResponseGenerated(f"Error generating response: {e}")

