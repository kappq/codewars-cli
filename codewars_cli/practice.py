import bs4
import click

from codewars_cli.consts import PROGRESS_OPTIONS, SORT_BY_OPTIONS


@click.command()
@click.option("-q", "--query", default="")
@click.option(
    "-s",
    "--sort-by",
    type=click.Choice(SORT_BY_OPTIONS),
    default="newest",
    show_default=True,
)
@click.option("-l", "--language", default="my-languages", show_default=True)
@click.option("--approved/--no-approved", default=True, show_default=True)
@click.option("--beta/--no-beta", default=False, show_default=True)
@click.option(
    "-p",
    "--progress",
    type=click.Choice(PROGRESS_OPTIONS),
    default="all",
    show_default=True,
)
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
            raise click.UsageError(
                "You can't set both --approved and --beta to 'False'."
            )

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
        console.print(
            f"[u {color}]{difficulty}[/u {color}] {kata['data-title']} [black]{kata['id']}[/black]"
        )
