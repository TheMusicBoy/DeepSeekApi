#!/usr/bin/env python

import click
import json
import requests
import sys

from api.ollama import OllamaApi

DEFAULT_ADDRESS = "89.169.145.6"
DEFAULT_PORT = 8080

@click.command()
@click.option('-p', '--port', default=DEFAULT_PORT, help="server port")
@click.option('-a', '--address', default=DEFAULT_ADDRESS, help="server address")
@click.option('-m', '--model', default="dpsk14", help="model <dpsk7, dpsk14, dpsk32>")
@click.option('--stream/--no-stream', default=True, help="print stream or whole message")
@click.argument('prompt')
def cli(port, address, model, stream, prompt):
    if not sys.stdin.isatty():
        prompt += "\n\n"
        for line in sys.stdin:
            prompt += line

    ollama = OllamaApi(address, port)
    if (stream):
        for token in ollama.generate_stream(model, prompt):
            print(token, end="", flush=True)
        print(flush=True)
    else:
        print(ollama.generate(model, prompt), flush=True)

if __name__ == "__main__":
    cli()
