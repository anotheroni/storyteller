import requests
import json
import openai

from PyQt5.QtCore import QObject

class LLMBackend:
    def __init__(self, name, address, system_prompt, llm_type='Kobold'):
        self.name = name
        self.address = address
        self.system_prompt = system_prompt
        self.type = llm_type  # 'Kobold' or 'OpenAI'

    def test_connection(self):
        try:
            if self.type == 'Kobold':
                response = requests.get(f"{self.address}/api/v1/version")
                return response.status_code == 200
            elif self.type == 'OpenAI':
                openai.api_key = self.address  # In this context, address holds the API key
                openai.Model.list()
                return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

class LLMManager:
    def __init__(self):
        self.llms = []

    def load_llm_config(self):
        try:
            with open('llm_config.json', 'r') as f:
                data = json.load(f)
                for llm_data in data:
                    llm = LLMBackend(llm_data['name'], llm_data['address'], llm_data['system_prompt'], llm_data.get('type', 'Kobold'))
                    if llm.test_connection():
                        self.llms.append(llm)
                    else:
                        QMessageBox.warning(None, "LLM Connection Error", f"Failed to connect to LLM {llm.name}")
        except FileNotFoundError:
            pass  # No config file yet

    def save_llm_config(self):
        data = []
        for llm in self.llms:
            data.append({
                'name': llm.name,
                'address': llm.address,
                'system_prompt': llm.system_prompt,
                'type': llm.type
            })
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

