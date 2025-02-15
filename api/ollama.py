import requests
import sys
import json
import click
import os
import copy
import re

import marshal


class OllamaObjectNotFoundException(Exception):
    pass


class OllamaBadRequestException(Exception):
    pass


class OllamaInternalExceptionException(Exception):
    pass


class OllamaApi:
    def __init__(self, config_dir=os.path.expanduser('~/.config/ollama_api')):
        self.load_config(config_dir)
        self.url = f"{'https' if self.config['ssl_connection'] else 'http'}://{self.config['ollama_endpoint']}/api/"
        self.load()

    def __del__(self):
        self.dump()

    def load_config(self, config_dir):
        self.config = {
            'ollama_endpoint': '89.169.145.6:8080',
            'cache_path': os.path.join(config_dir, 'cache.bin'),
            'ssl_connection': True
        }

        try:
            config_path = os.path.join(config_dir, 'config.json')
            with open(config_path, 'r') as file:
                self.config |= json.load(file)
        except Exception:
            pass

    def get_url(self, method):
        return self.url + method
    
    def get_chat(self, chat_id, autocreate=True):
        if autocreate and chat_id not in self.data['chat_list']:
            self.data['chat_list'][chat_id] = {
                'messages': [],
                'tags': set()
            }
        return self.data['chat_list'][chat_id] 

    def set_chat(self, chat_id, data):
        self.data['chat_list'][chat_id] = data

    def load(self):
        self.data = {
            "chat_list" : {
            }
        }
        try:
            with open(self.config['cache_path'], "rb") as file:
                self.data = marshal.load(file)
        except Exception:
            pass

    def dump(self):
        with open(self.config['cache_path'], "wb+") as file:
            marshal.dump(self.data, file)

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

    def chat(self, chat_id, model, prompt, options={}):
        try:
            messages = self.get_chat(chat_id)['messages']
            messages.append({
                "role": "user",
                "content": prompt
            })

            with requests.post(
                self.get_url("chat"),
                headers={"Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": messages,
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
                                    messages.append({
                                        "role": "user",
                                        "content": json_data['message']['content']
                                    })
                                    self.data['chat_list'][chat_id] = messages
                                    return json_data['message']['content']
                                buffer = b""
                            except json.JSONDecodeError:
                                continue

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def chat_stream(self, chat_id, model, prompt, options={}):
        try:
            messages = self.get_chat(chat_id)['messages']
            messages.append({
                "role": "user",
                "content": prompt
            })

            with requests.post(
                self.get_url("chat"),
                headers={"Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": messages,
                    "options": options,
                    "stream": True
                },
                stream=True
            ) as response:
                response.raise_for_status()

                chunks = response.iter_content(chunk_size=1024)
                
                message = {
                    "role": "assistent",
                    "content": ""
                }

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
                                    message['content'] += json_data['message']['content']
                                    yield json_data['message']['content']
                                if 'done' in json_data and json_data['done']:
                                    messages.append(message)
                                    self.data['chat_list'][chat_id]['messages'] = messages
                                    return
                                buffer = b""
                            except json.JSONDecodeError:
                                continue

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def delete_chat(self, chat_id):
        if chat_id not in self.data['chat_list']:
            raise OllamaObjectNotFoundException(f"No chat with name '{chat_id}'")
        else:
            del self.data['chat_list'][chat_id]

    def chat_from_message(self, chat_id, message_id, model, prompt, options={}):
        if chat_id not in self.data['chat_list']:
            raise OllamaObjectNotFoundException(f"No chat with name '{chat_id}'")

        if message_id >= len(self.data['chat_list'][chat_id]):
            raise OllamaObjectNotFoundException(f"No message {message_id} in chat '{chat_id}'")

        messages = self.data['chat_list'][chat_id][:message_id]
        return self.chat(chat_id, model, prompt, options)

    def chat_from_message_stream(self, chat_id, message_id, model, prompt, options={}):
        if chat_id not in self.data['chat_list']:
            raise OllamaObjectNotFoundException(f"No chat with name '{chat_id}'")

        if message_id >= len(self.data['chat_list'][chat_id]):
            raise OllamaObjectNotFoundException(f"No message {message_id} in chat '{chat_id}'")

        messages = self.data.get(chat_id)[:message_id]
        for token in self.chat_stream(chat_id, model, prompt, options):
            yield token

    def chat_list(self):
        result = []

        for chat_name, data in self.data['chat_list'].items():
            result.append({
                'id': chat_name,
                'tags': data['tags']
            })

        return result
