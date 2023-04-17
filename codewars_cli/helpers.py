import json
import os

import click
import cloudscraper
from rich.console import Console
from rich import box
from rich.console import Console, group
from rich.padding import Padding
from rich.panel import Panel
from rich.tree import Tree

from codewars_cli.consts import LANGUAGE_EXTS


def create_scraper() -> cloudscraper.CloudScraper:
    return cloudscraper.CloudScraper()


def get_cookies():
    try:
        session_id = os.environ["CW_SESSION_ID"]
        remember_user_token = os.environ["CW_REMEMBER_USER_TOKEN"]
        cookies = {
            "_session_id": session_id,
            "remember_user_token": remember_user_token,
        }
        return cookies
    except KeyError:
        raise click.UsageError(
            "`CW_SESSION_ID` and `CW_REMEMBER_USER_TOKEN` environment variables must be set."
        )


def create_console() -> Console:
    return Console()


def load_code(language_name):
    filename = "solution" + LANGUAGE_EXTS[language_name]
    with open(filename) as f:
        return f.read()


def load_data():
    with open("kata.json") as f:
        return json.load(f)


def run(payload, token):
    scraper = create_scraper()
    console = create_console()

    test_url = "https://runner.codewars.com/run"
    headers = {"Authorization": f"Bearer {token}"}
    response = scraper.post(test_url, headers=headers, json=payload).json()

    # Get the border color based on the exit code
    exit_code = response["exitCode"]
    border_color = "red" if exit_code == 1 else "green"

    # Get the time
    time = (
        "[red]Timed Out[/red]"
        if response["timedOut"]
        else f"[white]Time: {response['wallTime']}ms[/white]"
    )

    # Get assertions results
    result = response["result"]
    color_passed = "white" if result["passed"] == 0 else "green"
    passed = f"[{color_passed}]Passed: {result['passed']}[/{color_passed}]"
    color_failed = "white" if result["failed"] == 0 else "red"
    failed = f"[{color_failed}]Failed: {result['failed']}[/{color_failed}]"

    # STDERR
    stderr_output = response["stderr"]
    stderr_panel = (
        Panel.fit(stderr_output, title="STDERR", title_align="left")
        if stderr_output
        else None
    )

    # Build test restults tree
    @group()
    def get_renderables():
        for item in result["output"]:
            guide_style = "green" if item["p"] else "red"
            tree = Tree(
                f"[{guide_style}]⯆ [/{guide_style}]" + item["v"],
                guide_style=guide_style,
            )
            yield build_output(item["items"], tree)

        if stderr_panel:
            yield Padding(stderr_panel, (1, 0, 0, 0))

        if exit_code == 0:
            yield Padding(
                Panel(
                    "[green]You passed all the tests![/green]",
                    box=box.ASCII,
                    border_style="green",
                ),
                (1, 0, 0, 0),
            )

    # Create panel
    title = f"{time}   {passed}   {failed}   Exit Code: {exit_code}"
    panel = Panel(
        get_renderables(),
        title=title,
        title_align="left",
        border_style=border_color,
        padding=1,
    )

    # Render panel
    console.print(panel)

    return (exit_code, response["token"])


def build_output(items: list, tree: Tree):
    for item in items:
        match item["t"]:
            case "describe":
                guide_style = "green" if item["p"] else "red"
                sub_tree = tree.add(
                    f"[{guide_style}]▼ [/{guide_style}]" + item["v"],
                    guide_style=guide_style,
                )
            case "it":
                guide_style = "green" if item["p"] else "red"
                prefix = "⯈ " if item["p"] else "▼ "
                sub_tree = tree.add(
                    f"[{guide_style}]{prefix}[/{guide_style}]" + item["v"],
                    guide_style=guide_style,
                    expanded=not item["p"],
                )
            case "completedin":
                tree.add(f"[black]Completed in {item['v']}ms[/black]")
            case "passed":
                tree.add(f"[green]{item['v']}[/green]")
            case "failed":
                tree.add(f"[red]{item['v']}[/red]")
            case "error":
                tree.add(Panel.fit(item["v"], border_style="red"))
            case "log":
                tree.add(Panel.fit(item["v"], title="Log", title_align="left"))

        sub_items = item.get("items")
        if sub_items:
            build_output(sub_items, sub_tree)

    return tree


def notify(
    code: str,
    fixture: str,
    language_version: str,
    test_framework: str,
    token: str,
    project_id: str,
    solution_id: str,
    x_csrf_token: str,
    authorization: str,
):
    scraper = create_scraper()
    cookies = get_cookies()

    payload = {
        "code": code,
        "fixture": fixture,
        "languageVersion": language_version,
        "testFramework": test_framework,
        "token": token,
    }
    notify_url = f"https://www.codewars.com/api/v1/code-challenges/projects/{project_id}/solutions/{solution_id}/notify"
    headers = {"authorization": authorization, "X-CSRF-Token": x_csrf_token}
    scraper.post(notify_url, cookies=cookies, headers=headers, json=payload)
