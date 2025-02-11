import requests
import sys
import json
import click
import os
import copy
import re

import marshal


class OllamaApi:
    def __init__(self, config_path):
        self.config = self.get_config(config_path)
        self.url = f"{'https' if self.config['ssl_connection'] else 'http'}://{self.config['ollama_endpoint']}/api/"
        self.load()

    def __del__(self):
        self.dump()

    def extract_think_text(self, text):
        match = re.search(r'<think>(.*?)</think>', text, re.DOTALL)
        if match:
            think_text = match.group(1).strip()
            
            # Разделяем текст на части вне тегов <think>
            parts = re.split(r'<think>.*?</think>', text, flags=re.DOTALL)
            non_think_text = "".join(part.strip() for part in parts if part.strip())
            
            return think_text, non_think_text
        else:
            return None, text.strip()

    def concat_think_text(self, think, text):
        if think:
            return f"<think>\n{think}\n</think>\n{text}"
        else:
            return text

    def get_config(self, config_dir):
        try:
            os.makedirs(config_dir)
        except FileExistsError:
            pass

        config_path = os.path.join(config_dir, 'config.json')

        try:
            with open(config_path, 'r') as file:
                return json.load(file)
        except Exception:
            with open(config_path, 'w+') as file:
                data = {
                    'ollama_endpoint': '89.169.145.6:8080',
                    'chat_data_path': os.path.join(config_dir, 'chat_data.bin'),
                }
                json.dump(data, file)
                return data

    def get_url(self, method):
        return self.url + method

    def load(self):
        try:
            with open(self.config['chat_data_path'], "rb") as file:
                self.chat_data = marshal.load(file)
        except FileNotFoundError:
            self.chat_data = {}
        except TypeError:
            self.chat_data = {}
        except ValueError:
            self.chat_data = {}

    def dump(self):
        with open(self.config['chat_data_path'], "wb+") as file:
            marshal.dump(self.chat_data, file)

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
                                    return self.extract_think_text(json_data['response'])
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
                
                def process(content, stage):
                    if stage == 0:
                        if content == '<think>':
                            content = ""
                            stage += 1
                    elif stage == 1:
                        content = re.sub(r"^[\s\n]*", "", content)
                        if content == '</think>':
                            stage = 3
                            content = ""
                        elif content:
                            stage = 2
                    elif stage == 2:
                        if content == '</think>':
                            content = ""
                            stage += 1
                    elif stage == 3:
                        content = re.sub(r"^[\s\n]*", "", content)
                        if content:
                            stage += 1

                    return content, stage

                stage = 0
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
                                    text, stage = process(json_data['response'], stage)
                                    yield text, stage > 2
                                if 'done' in json_data and json_data['done']:
                                    return
                                buffer = b""
                            except json.JSONDecodeError:
                                continue

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def chat(self, chat_id, model, prompt, options={}):
        try:
            messages = self.chat_data.get(chat_id, [])
            messages.append({
                "role": "user",
                "think": None,
                "text": prompt
            })

            parsed = copy.deepcopy(messages)
            for message in parsed:
                message['content'] = self.concat_think_text(message['think'], message['text'])
                del message['think']
                del message['text']

            with requests.post(
                self.get_url("chat"),
                headers={"Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": parsed,
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
                                if 'message' in json_data:
                                    content = json_data['message']['content']
                                    think, text = self.extract_think_text(content)
                                    messages.append({
                                        "role": "user",
                                        "think": think,
                                        "text": text
                                    })
                                    self.chat_data[chat_id] = messages
                                    return think, text
                                buffer = b""
                            except json.JSONDecodeError:
                                continue

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def chat_stream(self, chat_id, model, prompt, options={}):
        try:
            messages = self.chat_data.get(chat_id, [])
            messages.append({
                "role": "user",
                "think": None,
                "text": prompt
            })

            parsed = copy.deepcopy(messages)
            for message in parsed:
                message['content'] = self.concat_think_text(message.get('think', ''), message['text'])
                del message['think']
                del message['text']

            with requests.post(
                self.get_url("chat"),
                headers={"Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": parsed,
                    "options": options,
                    "stream": True
                },
                stream=True
            ) as response:
                response.raise_for_status()

                chunks = response.iter_content(chunk_size=1024)
                
                message = {
                    "role": "assistent",
                    "think": "",
                    "text": ""
                }

                def process(content, stage):
                    if stage == 0:
                        if content == '<think>':
                            content = ""
                            stage += 1
                    elif stage == 1:
                        content = re.sub(r"^[\s\n]*", "", content)
                        if content == '</think>':
                            stage = 3
                            content = ""
                        elif content:
                            stage = 2
                    elif stage == 2:
                        if content == '</think>':
                            content = ""
                            stage += 1
                    elif stage == 3:
                        content = re.sub(r"^[\s\n]*", "", content)
                        if content:
                            stage += 1

                    return content, stage

                stage = 0
                buffer = b""
                for chunk in chunks:
                    if not chunk:
                        continue
                    for line in chunk.split(b'\r\n'):
                        if line:
                            buffer += line
                            try:
                                json_data = json.loads(buffer)
                                if 'message' in json_data:
                                    text, stage = process(json_data['message']['content'], stage)

                                    if stage < 2:
                                        message['think'] += text
                                    else:
                                        message['text'] += text
                    
                                    buffer = b""
                                    yield text, stage > 2
                                if 'done' in json_data and json_data['done']:
                                    messages.append(message)
                                    self.chat_data[chat_id] = messages
                                    return
                                buffer = b""
                            except json.JSONDecodeError:
                                continue

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def delete_chat(self, chat_id):
        if chat_id not in self.chat_data:
            print(f"No chat with name '{chat_id}'")
        else:
            del self.chat_data[chat_id]

    def chat_from_message(self, chat_id, message_id, model, prompt, options={}):
        if chat_id not in self.chat_data:
            print(f"No chat with name '{chat_id}'")

        if message_id >= len(self.chat_data[chat_id]):
            print(f"No message {chat_id} in chat '{chat_id}'")

        messages = self.chat_data.get(chat_id)[:message_id]

        return self.chat(chat_id, model, prompt, options)

    def chat_from_message_stream(self, chat_id, message_id, model, prompt, options={}):
        if chat_id not in self.chat_data:
            print(f"No chat with name '{chat_id}'")

        if message_id >= len(self.chat_data[chat_id]):
            print(f"No message {chat_id} in chat '{chat_id}'")

        messages = self.chat_data.get(chat_id)[:message_id]

        for token in self.chat_stream(chat_id, model, prompt, options):
            yield token

    def chat_list(self):
        result = []

        for chat_name, message in self.chat_data.items():
            result.append(chat_name)

        return result

    def get_chat(self, chat_id):
        return self.chat_data.get(chat_id, [])
