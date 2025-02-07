#!/usr/bin/env python

import click
import json
import requests
import sys

from api.ollama import OllamaApi


DEFAULT_CONFIG_PATH = "/home/painfire/.config/dpsk"


@click.group()
def cli():
    """
    """
    pass


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
@prompt_argument
def do_generate(model, stream, think, prompt):
    prompt = ' '.join(prompt)

    if not sys.stdin.isatty():
        prompt += "\n\n"
        for line in sys.stdin:
            prompt += line

    ollama = OllamaApi(DEFAULT_CONFIG_PATH)

    if (stream):
        text_mode = True
        for token, talking in ollama.generate_stream(model, prompt):
            if text_mode != talking:
                if think:
                    if talking:
                        print('\n--- Printing result... ---')
                    else:
                        print('--- Thinking... ---')
                text_mode = talking

            if think or talking:
                print(token, end="", flush=True)
        print(flush=True)
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
@prompt_argument
def do_chat(chat_id, model, stream, think, prompt):
    chat_id = chat_id.strip()
    prompt = ' '.join(prompt)

    if not sys.stdin.isatty():
        prompt += "\n\n"
        for line in sys.stdin:
            prompt += line

    ollama = OllamaApi(DEFAULT_CONFIG_PATH)

    if (stream):
        text_mode = True
        for token, talking in ollama.chat_stream(chat_id, model, prompt):
            if text_mode != talking:
                if think:
                    if talking:
                        print('\n--- Printing result... ---')
                    else:
                        print('--- Thinking... ---')
                text_mode = talking

            if think or talking:
                print(token, end="", flush=True)
        print(flush=True)
    else:
        think, text = ollama.chat(chat_id, model, prompt)
        print(f"--- Thinking... ---\n{think}\n--- Printing result... ---\n{text}", flush=True)


@cli.command(name='list', help='list of chats')
def do_list():
    ollama = OllamaApi(DEFAULT_CONFIG_PATH)
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
