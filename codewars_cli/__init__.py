import json
import os
import re
import urllib

import bs4
import click
import cloudscraper
from rich.console import Console, group
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.tree import Tree

scraper = cloudscraper.CloudScraper()
console = Console(highlight=False)

LANGUAGE_EXTS = {
    "python": ".py",
    "rust": ".rs",
}

SORT_BY_OPTIONS = [
    "newest",
    "oldest",
    "popularity",
    "positive-feedback",
    "most-completed",
    "least-completed",
    "recently-published",
    "hardest",
    "easiest",
    "name",
    "low-satisfaction",
]

PROGRESS_OPTIONS = ["all", "not-trained", "not-completed", "completed"]

try:
    session_id = os.environ["CW_SESSION_ID"]
    remember_user_token = os.environ["CW_REMEMBER_USER_TOKEN"]
    cookies = {"_session_id": session_id, "remember_user_token": remember_user_token}
except KeyError:
    raise click.UsageError("`CW_SESSION_ID` and `CW_REMEMBER_USER_TOKEN` environment variables must be set.")


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
    payload = {
        "code": code,
        "fixture": fixture,
        "languageVersion": language_version,
        "testFramework": test_framework,
        "token": token,
    }
    notify_url = (
        f"https://www.codewars.com/api/v1/code-challenges/projects/{project_id}/solutions/{solution_id}/notify"
    )
    headers = {"authorization": authorization, "X-CSRF-Token": x_csrf_token}
    scraper.post(notify_url, cookies=cookies, headers=headers, json=payload)


def load_data():
    with open("kata.json") as f:
        return json.load(f)


def load_code(language_name):
    filename = "solution" + LANGUAGE_EXTS[language_name]
    with open(filename) as f:
        return f.read()


def build_output(items: list, tree: Tree):
    for item in items:
        match item["t"]:
            case "describe":
                guide_style = "green" if item["p"] else "red"
                sub_tree = tree.add(f"[{guide_style}]▼ [/{guide_style}]" + item["v"], guide_style=guide_style)
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

        sub_items = item.get("items")
        if sub_items:
            build_output(sub_items, sub_tree)

    return tree


def run(payload, token):
    test_url = "https://runner.codewars.com/run"
    headers = {"Authorization": f"Bearer {token}"}
    response = scraper.post(test_url, headers=headers, json=payload).json()

    # Get the border color based on the exit code
    exit_code = response["exitCode"]
    border_color = "red" if exit_code == 1 else "green"

    # Get the time
    time = "[red]Timed Out[/red]" if response["timedOut"] else f"[white]Time: {response['wallTime']}ms[/white]"

    # Get assertions results
    result = response["result"]
    color_passed = "white" if result["passed"] == 0 else "green"
    passed = f"[{color_passed}]Passed: {result['passed']}[/{color_passed}]"
    color_failed = "white" if result["failed"] == 0 else "red"
    failed = f"[{color_failed}]Failed: {result['failed']}[/{color_failed}]"

    # STDERR
    stderr_output = response["stderr"]
    stderr_panel = Panel.fit(stderr_output, title="STDERR", title_align="left") if stderr_output else None

    # Build test restults tree
    @group()
    def get_renderables():
        for item in result["output"]:
            guide_style = "green" if item["p"] else "red"
            tree = Tree(f"[{guide_style}]⯆ [/{guide_style}]" + item["v"], guide_style=guide_style)
            yield build_output(item["items"], tree)

        if stderr_panel:
            yield Padding(stderr_panel, (1, 0, 0, 0))

    # Create panel
    title = f"{time}   {passed}   {failed}   Exit Code: {exit_code}"
    panel = Panel(get_renderables(), title=title, title_align="left", border_style=border_color, padding=1)

    # Render panel
    console.print(panel)

    return (exit_code, response["token"])


@click.group()
def main():
    """An unofficial CLI for CodeWars."""


@main.command()
@click.option("-q", "--query", default="")
@click.option("-s", "--sort-by", type=click.Choice(SORT_BY_OPTIONS), default="newest", show_default=True)
@click.option("-l", "--language", default="my-languages", show_default=True)
@click.option("--approved/--no-approved", default=True, show_default=True)
@click.option("--beta/--no-beta", default=False, show_default=True)
@click.option("-p", "--progress", type=click.Choice(PROGRESS_OPTIONS), default="all", show_default=True)
@click.option("-d", "--difficulty", multiple=True)
@click.option("-t", "--tags", multiple=True)
def practice(
    query: str,
    sort_by: str,
    language: str,
    approved: bool,
    beta: bool,
    progress: str,
    difficulty: tuple[int],
    tags: tuple[str],
):
    """Search for a kata."""

    match sort_by:
        case "newest":
            sort_by = "sort_date desc"
        case "oldest":
            sort_by = "published_at asc"
        case "popularity":
            sort_by = "popularity desc"
        case "positive-feedback":
            sort_by = "satisfaction_percent desc%2Ctotal_completed desc"
        case "most-completed":
            sort_by = "total_completed desc"
        case "least-completed":
            sort_by = "total_completed asc"
        case "recently-published":
            sort_by = "published_at desc"
        case "hardest":
            sort_by = "rank_id desc"
        case "easiest":
            sort_by = "rank_id asc"
        case "name":
            sort_by = "name asc"
        case "low-satisfaction":
            sort_by = "satisfaction_percent asc"

    if language == "all":
        language = ""

    match (approved, beta):
        case (True, True):
            status = ""
        case (True, False):
            status = "&beta=false"
        case (False, True):
            status = "&beta=true"
        case (False, False):
            raise click.UsageError("You can't set both --approved and --beta to 'False'.")

    match progress:
        case "all":
            progress = ""
        case "not-trained":
            progress = "&xids=played"
        case "not-completed":
            progress = "&xids=completed"
        case "completed":
            progress = "&xids=not_completed"

    difficulty = "".join(map("&r[]=-{}".format, difficulty))
    tags = "" if len(tags) == 0 else "&tags=" + "%2C".join(map(str.title, tags))

    practice_url = f"https://www.codewars.com/kata/search/{language}?q={query}{status}{progress}{difficulty}{tags}&order_by={sort_by}"
    response = scraper.get(practice_url, cookies=cookies)

    soup = bs4.BeautifulSoup(response.text, "html.parser")
    for kata in soup.find_all("div", "list-item-kata"):
        difficulty = kata.find("div", "inner-small-hex").span.text
        match difficulty.split()[0]:
            case "8" | "7":
                color = "white"
            case "6" | "5":
                color = "yellow"
            case "4" | "3":
                color = "blue"
            case "2" | "1":
                color = "purple"
        console.print(f"[u {color}]{difficulty}[/u {color}] {kata['data-title']} [black]{kata['id']}[/black]")


@main.command()
@click.option("--language", required=True, help="The language to solve the kata in.")
@click.argument("kata")
def train(language: str, kata: str):
    """Choose a kata to solve.

    KATA is the ID of the kata you want to train.
    You can grab it from the URL or from the `practice` subcommand."""

    data = {}

    # This is the initial request
    kata_url = f"https://www.codewars.com/kata/{kata}/train/{language}"
    response = scraper.get(kata_url, cookies=cookies)

    project_id = re.search(r"projects\/([^\/]+)\/%7Blanguage%7D", response.text).group(1)
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
    session_url = f"https://www.codewars.com/kata/projects/{project_id}/{language}/session"
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


@main.command()
def test():
    """Test against the sample tests."""

    data = load_data()
    code = load_code(data["languageName"])

    # Get authorization token
    authorize_url = "https://www.codewars.com/api/v1/runner/authorize"
    headers = {"authorization": data["authorization"], "X-CSRF-Token": data["csrfToken"]}
    response = scraper.post(authorize_url, cookies=cookies, headers=headers)
    token = response.json()["token"]

    # Generate request body
    payload = {
        "ciphered": ["setup"],
        "code": code,
        "fixture": data["exampleFixture"],
        "language": data["languageName"],
        "languageVersion": data["languageVersion"],
        "relayId": data["solutionId"],
        "setup": data["package"],
        "successMode": None,
        "testFramework": data["testFramework"],
    }

    # Run sample tests
    exit_code, token = run(payload, token)
    notify(
        code,
        data["exampleFixture"],
        data["languageVersion"],
        data["testFramework"],
        token,
        data["projectId"],
        data["solutionId"],
        data["csrfToken"],
        data["authorization"],
    )
    quit(exit_code)


@main.command()
def attempt():
    """Attempt to pass the full test suite."""

    data = load_data()
    code = load_code(data["languageName"])

    # Get authorization token
    authorize_url = "https://www.codewars.com/api/v1/runner/authorize"
    headers = {"authorization": data["authorization"], "X-CSRF-Token": data["csrfToken"]}
    response = scraper.post(authorize_url, cookies=cookies, headers=headers)
    token = response.json()["token"]

    # Generate request body
    payload = {
        "ciphered": ["setup", "fixture"],
        "code": code,
        "fixture": data["fixture"],
        "language": data["languageName"],
        "languageVersion": data["languageVersion"],
        "relayId": data["solutionId"],
        "setup": data["package"],
        "successMode": None,
        "testFramework": data["testFramework"],
    }

    # Run full test suite
    exit_code, token = run(payload, token)
    notify(
        code,
        data["exampleFixture"],
        data["languageVersion"],
        data["testFramework"],
        token,
        data["projectId"],
        data["solutionId"],
        data["csrfToken"],
        data["authorization"],
    )
    quit(exit_code)


@main.command()
def submit():
    """Submit your solution."""

    data = load_data()
    kata_id = data["id"]
    project_id = data["projectId"]
    solution_id = data["solutionId"]
    x_csrf_token = data["csrfToken"]
    language_name = data["languageName"]

    # Submit the solution
    submit_url = (
        f"https://www.codewars.com/api/v1/code-challenges/projects/{project_id}/solutions/{solution_id}/finalize"
    )
    headers = {"X-CSRF-Token": x_csrf_token}
    response = scraper.post(submit_url, cookies=cookies, headers=headers).json()

    if response["success"]:
        link = f"https://www.codewars.com/kata/{kata_id}/solutions/{language_name}"
        console.print(f"Good job! View other people's solutions [blue link={link}]here[/blue link]!")
    else:
        console.print("[red]The solution wasn't submitted correctly...[/red]")
