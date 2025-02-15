#!/usr/bin/env python

import click
import json
import requests
import os
import sys

from api.ollama import OllamaApi


DEFAULT_CONFIG_PATH = os.path.expanduser('~/.config/dpsk')


class Printer:
    def applyFormat(self, option):
        if ':' not in option:
            self.format = option
            self.chunk_align = 0
        else:
            result = option.split(':')
            self.format = result[0]
            self.chunk_align = int(result[1])

    def __init__(self, format_option):
        self.applyFormat(format_option)
        self.current_mode = 0

    def chunkPrint(self, text):
        if self.chunk_align == 0:
            print(text, end="", flush=True)
        else:
            for i in range(0, len(text), self.chunk_align):
                data_size = min(len(text) - i, self.chunk_align)
                chunk = text[i:i + data_size] + ' ' * (self.chunk_align - data_size)
                print(chunk, end="", flush=True)

    def token_print(self, text):
        if self.format == 'text':
            self.chunkPrint(text)
        elif self.format == 'json':
            data = {
                'out_loud': mode,
                'content': text,
                'done': False
            }
            self.chunkPrint(json.dumps(data))

    def print_list(self, obj):
        if self.format == 'text':
            for element in obj:
                self.chunkPrint(f"{element['id']} -- tags: {', '.join(element['tags'])}")
        elif self.format == 'json':
            data = {
                'list': obj,
                'done': False
            }
            self.chunkPrint(json.dumps(data))

    def print_messages(self, obj):
        if self.format == 'text':
            for e in obj:
                self.chunkPrint(f"{e['role'] if e['role'] != 'user' else 'you'}: {e['content']}\n")
        elif self.format == 'json':
            data = {
                'messages': obj,
                'done': False
            }
            self.chunkPrint(json.dumps(data))

    def print_exception(self, ex):
        if self.format == 'text':
            print(f"Error: {ex}")
        elif self.format == 'json':
            data = {
                'exception': ex,
                'done': False
            }
            self.chunkPrint(json.dumps(data))

    def finish(self):
        if self.format == 'text':
            self.chunkPrint('\n')
        else:
            self.chunkPrint(json.dumps({'done': True}))


@click.group()
def cli():
    """
    """
    pass


format_option = click.option(
    '-f',
    '--format',
    default="text",
    help="model <dpsk7, dpsk14, dpsk32>"
)


model_option = click.option(
    '-m',
    '--model',
    default="dpsk14",
    help="model <dpsk7, dpsk14, dpsk32>"
)


stream_option = click.option(
    '--stream/--no-stream',
    default=True,
    help="print stream or whole message"
)


prompt_argument = click.argument(
    'prompt',
    nargs=-1
)


@cli.command(name='generate', help='generate single text by prompt')
@model_option
@stream_option
@format_option
@prompt_argument
def do_generate(model, stream, format, prompt):
    prompt = ' '.join(prompt)

    if not sys.stdin.isatty():
        prompt += "\n\n"
        for line in sys.stdin:
            prompt += line

    ollama = OllamaApi(DEFAULT_CONFIG_PATH)

    if (stream):
        printer = Printer(format)
        for token, out_loud in ollama.generate_stream(model, prompt):
            printer.token_print(token, out_loud)
    else:
        text = ollama.generate(model, prompt)
        printer.token_print(text)
    printer.finish()


chat_id_option = click.option(
    '-c',
    '--chat-id',
    default="First chat",
    help="chat name"
)


@cli.command(name='chat', help='chat with bot')
@chat_id_option
@model_option
@stream_option
@format_option
@prompt_argument
def do_chat(chat_id, model, stream, format, prompt):
    chat_id = chat_id.strip()
    prompt = ' '.join(prompt)

    if not sys.stdin.isatty():
        prompt += "\n\n"
        for line in sys.stdin:
            prompt += line

    ollama = OllamaApi(DEFAULT_CONFIG_PATH)

    printer = Printer(format)
    if (stream):
        for token in ollama.chat_stream(chat_id, model, prompt):
            printer.token_print(token, out_loud)
    else:
        text = ollama.chat(chat_id, model, prompt)
        printer.token_print(thoughts, out_loud)
    printer.finish()


@cli.command(name='list', help='list of chats')
@format_option
def do_list(format):
    ollama = OllamaApi(DEFAULT_CONFIG_PATH)
    printer = Printer(format)
    printer.print_list(ollama.chat_list())


chat_id_argument = click.argument('chat_id', nargs=1)


@cli.command(name='delete', help='delete chat')
@chat_id_argument
@format_option
def do_delete(chat_id, format):
    ollama = OllamaApi(DEFAULT_CONFIG_PATH)
    printer = Printer(format)
    try:
        ollama.delete_chat(chat_id)
    except Exception as ex:
        printer.print_exception(ex)
    printer.finish()


@cli.command(name='messages', help='get chat messages')
@chat_id_argument
@format_option
def do_messages(chat_id, format):
    ollama = OllamaApi(DEFAULT_CONFIG_PATH)
    printer = Printer(format)
    try:
        chat_data = ollama.get_chat(chat_id)
        printer.print_messages(chat_data['messages'])
    except Exception as ex:
        printer.print_exception(ex)
    printer.finish()


if __name__ == "__main__":
    cli()
