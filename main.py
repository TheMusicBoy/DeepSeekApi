#!/usr/bin/env python

import click
import json
import requests
import sys

from api.ollama import OllamaApi


DEFAULT_CONFIG_PATH = "/home/painfire/.config/dpsk"


class Printer:
    def applyFormat(self, option):
        if ':' not in option:
            self.format = option
            self.chunk_align = 0
        else:
            result = option.split(':')
            self.format = result[0]
            self.chunk_align = int(result[1])

    def __init__(self, print_think, format_option):
        self.print_think = print_think
        self.applyFormat(format_option)
        self.current_mode = 0

    def chunkPrint(self, text):
        print(text)
        if self.chunk_align == 0:
            print(text, end="", flush=True)
        else:
            for i in range(0, len(text), self.chunk_align):
                data_size = min(len(text) - i, self.chunk_align)
                chunk = text[i:len(text) - data_size] + ' ' * (self.chunk_align - data_size)
                print(chunk, end="", flush=True)

    def token_print(self, text, mode):
        if not self.print_think and not mode:
            return

        if self.format == 'text':
            if self.print_think:
                if self.current_mode == 0 and mode == False:
                    self.chunkPrint('--- Thinking... ---\n')
                    self.current_mode = 1
                elif self.current_mode == 1 and mode == True:
                    self.chunkPrint('\n--- Printing result... ---\n')
                    self.current_mode = 2

            self.chunkPrint(text)
        elif self.format == 'json':
            data = {
                'out_loud': mode,
                'content': {
                    'thoughts': '',
                    'out_loud': '',
                },
                'done': False
            }

            if mode:
                data['content']['out_loud'] = text
            else:
                data['content']['thoughts'] = text

            self.chunkPrint(json.dumps(data))

    def print_text(self, thoughts, out_loud):
        if self.format == 'text':
            if self.print_think:
                self.chunkPrint(f"--- Thinking... ---\n{thoughts}\n--- Printing result... ---\n{out_loud}")
            else:
                self.chunkPrint(out_loud)
            self.finish()
        elif self.format == 'json':
            data = {
                'out_loud': True,
                'content': {
                    'thoughts': '',
                    'out_loud': out_loud,
                },
                'done': True
            }
            if self.print_think:
                data['content']['thoughts'] = thoughts

            self.chunkPrint(json.dumps(data))

    def print_list(self, obj):
        if self.format == 'text':
            for element in obj:
                self.chunkPrint(element)
        elif self.format == 'json':
            data = {
                'list': obj,
                'done': True
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


think_option = click.option(
    '--think/--no-think',
    default=True,
    help="Print think"
)


prompt_argument = click.argument(
    'prompt',
    nargs=-1
)


@cli.command(name='generate', help='generate single text by prompt')
@model_option
@stream_option
@think_option
@format_option
@prompt_argument
def do_generate(model, stream, think, format, prompt):
    prompt = ' '.join(prompt)

    if not sys.stdin.isatty():
        prompt += "\n\n"
        for line in sys.stdin:
            prompt += line

    ollama = OllamaApi(DEFAULT_CONFIG_PATH)

    if (stream):
        printer = Printer(think, format)
        for token, out_loud in ollama.generate_stream(model, prompt):
            printer.token_print(token, out_loud)
        printer.finish()
    else:
        think, text = ollama.generate(model, prompt)
        print(f"--- Thinking... ---\n{think}\n--- Printing result... ---\n{text}", flush=True)


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
@think_option
@format_option
@prompt_argument
def do_chat(chat_id, model, stream, think, format, prompt):
    chat_id = chat_id.strip()
    prompt = ' '.join(prompt)

    if not sys.stdin.isatty():
        prompt += "\n\n"
        for line in sys.stdin:
            prompt += line

    ollama = OllamaApi(DEFAULT_CONFIG_PATH)

    printer = Printer(think, format)
    if (stream):
        for token, out_loud in ollama.generate_stream(model, prompt):
            printer.token_print(token, out_loud)
        printer.finish()
    else:
        thoughts, out_loud = ollama.chat(chat_id, model, prompt)
        printer.print_text(thoughts, out_loud)


@cli.command(name='list', help='list of chats')
@format_option
def do_list(format):
    ollama = OllamaApi(DEFAULT_CONFIG_PATH)
    printer = Printer(False, format)
    for chat_name in ollama.chat_list():
        print(chat_name)

chat_id_argument = click.argument('chat_id', nargs=1)


@cli.command(name='delete', help='delete chat')
@chat_id_argument
def do_delete(chat_id):
    ollama = OllamaApi(DEFAULT_CONFIG_PATH)
    ollama.delete_chat(chat_id)


if __name__ == "__main__":
    cli()
