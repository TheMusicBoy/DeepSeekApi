import requests
import sys
import json
import click

import marshal

class OllamaApi:
    def __init__(self, address, port, chat_file="chats_data.bin"):
        self.url = f"https://{address}:{port}/api/"
        self.chat_file = chat_file
        self.chat_data = {}
        # self.load()

    # def __def__(self):
    #     self.dump()

    def get_url(self, method):
        return self.url + method

    def load(self):
        with open(self.chat_file, "rb+") as f:
            self.chat_data = marshal.load(f)

    def dump(self):
        with open(self.chat_file, "wb+") as f:
            marshal.dump(self.chat_data, f)

    def generate(self, model, prompt, options={}):
        try:
            with requests.post(
                self.get_url("generate"),
                headers={"Content-Type": "application/json"},
                json={
                    "model": model,
                    "prompt": prompt,
                    "options": options,
                    "stream": False
                },
                stream=True
            ) as response:
                response.raise_for_status()

                chunks = response.iter_content(chunk_size=1024)

                buffer = b""
                for chunk in chunks:
                    if not chunk:
                        continue
                    for line in chunk.split(b'\r\n'):
                        if line:
                            buffer += line
                            try:
                                json_data = json.loads(buffer)
                                if 'response' in json_data:
                                    return json_data['response']
                                buffer = b""
                            except json.JSONDecodeError:
                                continue

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def generate_stream(self, model, prompt, options={}):
        try:
            with requests.post(
                self.get_url("generate"),
                headers={"Content-Type": "application/json"},
                json={
                    "model": model,
                    "prompt": prompt,
                    "options": options,
                    "stream": True
                },
                stream=True
            ) as response:
                response.raise_for_status()

                chunks = response.iter_content(chunk_size=1024)
                
                buffer = b""
                for chunk in chunks:
                    if not chunk:
                        continue
                    for line in chunk.split(b'\r\n'):
                        if line:
                            buffer += line
                            try:
                                json_data = json.loads(buffer)
                                if 'response' in json_data:
                                    yield json_data['response']
                                if 'done' in json_data and json_data['done']:
                                    return
                                buffer = b""
                            except json.JSONDecodeError:
                                continue

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    # def chat(self, chat_id, model, prompt, options={}):
    #     try:
    #         messages = self.chat_data.get(chat_id, [])
    #         messages.append({
    #             "role": "user",
    #             "content": prompt
    #         })

    #         with requests.post(
    #             self.get_url("chat"),
    #             headers={"Content-Type": "application/json"},
    #             json={
    #                 "model": model,
    #                 "messages": messages,
    #                 "options": options,
    #                 "stream": False
    #             },
    #             stream=True
    #         ) as response:
    #             response.raise_for_status()

    #             chunks = response.iter_content(chunk_size=1024)

    #             buffer = b""
    #             for chunk in chunks:
    #                 if not chunk:
    #                     continue
    #                 for line in chunk.split(b'\r\n'):
    #                     if line:
    #                         buffer += line
    #                         try:
    #                             json_data = json.loads(buffer)
    #                             if 'message' in json_data:
    #                                 messages.append(json_data['message'])
    #                                 self.chat_data[chat_id] = messages
    #                                 return json_data['message']['content']
    #                             buffer = b""
    #                         except json.JSONDecodeError:
    #                             continue

    #     except requests.exceptions.RequestException as e:
    #         print(f"Error: {e}")

    # def chat_stream(self, chat_id, model, prompt, options={}):
    #     try:
    #         messages = self.chat_data.get(chat_id, [])
    #         messages.append({
    #             "role": "user",
    #             "content": prompt
    #         })

    #         with requests.post(
    #             self.get_url("chat"),
    #             headers={"Content-Type": "application/json"},
    #             json={
    #                 "model": model,
    #                 "messages": messages,
    #                 "options": options,
    #                 "stream": True
    #             },
    #             stream=True
    #         ) as response:
    #             response.raise_for_status()

    #             chunks = response.iter_content(chunk_size=1024)
    #             
    #             message = {
    #                 "role": "assistent",
    #                 "content": ""
    #             }
    #             buffer = b""
    #             for chunk in chunks:
    #                 if not chunk:
    #                     continue
    #                 for line in chunk.split(b'\r\n'):
    #                     if line:
    #                         buffer += line
    #                         try:
    #                             json_data = json.loads(buffer)
    #                             if 'response' in json_data:
    #                                 message['content'] += json_data['message']['content']
    #                                 yield json_data['message']['content']
    #                             if 'done' in json_data and json_data['done']:
    #                                 messages.append(message)
    #                                 self.chat_data[chat_id] = messages
    #                                 return
    #                             buffer = b""
    #                         except json.JSONDecodeError:
    #                             continue

    #     except requests.exceptions.RequestException as e:
    #         print(f"Error: {e}")
