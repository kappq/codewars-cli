import click

from codewars_cli.helpers import (
    create_console,
    create_scraper,
    get_cookies,
    load_data,
)


@click.command()
def submit():
    """Submit your solution."""

    scraper = create_scraper()
    cookies = get_cookies()
    console = create_console()

    data = load_data()
    kata_id = data["id"]
    project_id = data["projectId"]
    solution_id = data["solutionId"]
    x_csrf_token = data["csrfToken"]
    authorization = data["authorization"]
    language_name = data["languageName"]

    # Submit the solution
    submit_url = f"https://www.codewars.com/api/v1/code-challenges/projects/{project_id}/solutions/{solution_id}/finalize"
    headers = {"X-CSRF-Token": x_csrf_token, "authorization": authorization}
    response = scraper.post(submit_url, cookies=cookies, headers=headers).json()

    if response["success"]:
        link = f"https://www.codewars.com/kata/{kata_id}/solutions/{language_name}"
        console.print(
            f"Good job! View other people's solutions [blue link={link}]here[/blue link]!"
        )
    else:
        console.print("[red]The solution wasn't submitted correctly...[/red]")
