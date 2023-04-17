import click

from codewars_cli.practice import practice
from codewars_cli.train import train
from codewars_cli.test import test
from codewars_cli.attempt import attempt
from codewars_cli.submit import submit


@click.group()
def cli():
    """An unofficial CLI for CodeWars."""


cli.add_command(practice)
cli.add_command(train)
cli.add_command(test)
cli.add_command(attempt)
cli.add_command(submit)
