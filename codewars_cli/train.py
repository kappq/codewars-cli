import json
import os
import re
import urllib

import click
from rich.markdown import Markdown

from codewars_cli.consts import LANGUAGE_EXTS
from codewars_cli.helpers import create_console, create_scraper, get_cookies


@click.command()
@click.option("--language", required=True, help="The language to solve the kata in.")
@click.argument("kata")
def train(language: str, kata: str) -> None:
    """Choose a kata to solve.

    KATA is the ID of the kata you want to train.
    You can grab it from the URL or from the `practice` subcommand."""

    scraper = create_scraper()
    cookies = get_cookies()
    console = create_console()

    data = {}

    # This is the initial request
    kata_url = f"https://www.codewars.com/kata/{kata}/train/{language}"
    response = scraper.get(kata_url, cookies=cookies)

    project_id = re.search(r"projects\/([^\/]+)\/%7Blanguage%7D", response.text).group(
        1
    )
    authorization = re.search(r"\\\"jwt\\\":\\\"([^\"\\]+)", response.text).group(1)

    data["projectId"] = project_id
    data["authorization"] = authorization

    # This is a request to the official API to get some general info about the kata
    api_url = f"https://www.codewars.com/api/v1/code-challenges/{kata}"
    response = scraper.get(api_url).json()

    data["id"] = response["id"]
    data["name"] = response["name"]
    data["slug"] = response["slug"]
    data["description"] = response["description"]

    # Now we need the X-CSRF-Token, we get that from the cookies and we parse it
    x_csrf_token = urllib.parse.unquote_plus(scraper.cookies["CSRF-TOKEN"])
    data["csrfToken"] = x_csrf_token

    # This request allows use to get some information about the session itself
    session_url = (
        f"https://www.codewars.com/kata/projects/{project_id}/{language}/session"
    )
    headers = {"authorization": authorization, "X-CSRF-Token": x_csrf_token}
    response = scraper.post(session_url, cookies=cookies, headers=headers).json()

    data["languageName"] = response["languageName"]
    data["languageVersion"] = response["activeVersion"]
    data["exampleFixture"] = response["exampleFixture"]
    data["fixture"] = response["fixture"]
    data["setup"] = response["setup"]
    data["package"] = response["package"]
    data["testFramework"] = response["testFramework"]
    data["solutionId"] = response["solutionId"]

    # Create the kata directory
    slug = data["slug"]
    try:
        os.makedirs(slug)
    except OSError:
        print(f"Directory for `{slug}` already exists.")

    # Write description
    filename = os.path.join(slug, "description.md")
    with open(filename, "w") as f:
        f.write(data["description"])

    # Write setup code
    filename = os.path.join(slug, "solution" + LANGUAGE_EXTS[data["languageName"]])
    with open(filename, "w") as f:
        f.write(data["setup"])

    # Write kata data
    filename = os.path.join(slug, "kata.json")
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

    # Render description
    with console.pager(styles=True):
        description = Markdown(data["description"])
        console.print(description)
