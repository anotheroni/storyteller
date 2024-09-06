import requests
import json

from PyQt5.QtCore import QObject

# Define the URL
generateUrl = "http://localhost:5001/api/v1/generate"
tokenCountUrl = "http://localhost:5001/api/extra/tokencount"

# Define the headers for the request
headers = {
    'Content-Type': 'application/json'
}

class CountTask(QObject):
    def __init__(self, data, source):
        super(CountTask, self).__init__()
        self.data = data
        self.source = source
    def execute(self):
        response = requests.post(tokenCountUrl, headers=headers, data=json.dumps({"prompt":self.data}))
        if response.status_code == 200:
            response_data = json.loads(response.text)
            self.source.onTokensCounted(response_data["value"])
        else:
            self.source.onTokensCounted(-1)

class GenerateTask(QObject):
    def __init__(self, data, source):
        super(GenerateTask, self).__init__()
        self.data = data
        self.source = source
    def execute(self):
        prompt = json.dumps({
            "prompt": self.data,
            "max_length": 1024
        })
        response = requests.post(generateUrl, headers=headers, data=prompt)
        if response.status_code == 200:
            response_data = json.loads(response.text)
            app.beep()
            self.source.onResponseGenerated(response_data["results"][0]["text"].strip())
        else:
            self.source.onResponseGenerated("Error generating response")       
