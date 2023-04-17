import click

from codewars_cli.helpers import (
    create_scraper,
    get_cookies,
    load_code,
    load_data,
    run,
    notify,
)


@click.command()
def attempt():
    """Attempt to pass the full test suite."""

    scraper = create_scraper()
    cookies = get_cookies()

    data = load_data()
    code = load_code(data["languageName"])

    # Get authorization token
    authorize_url = "https://www.codewars.com/api/v1/runner/authorize"
    headers = {
        "authorization": data["authorization"],
        "X-CSRF-Token": data["csrfToken"],
    }
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
