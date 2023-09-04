from typing import Any, Optional
import click
import requests

SLEEPER_API_BASE_URL = "https://api.sleeper.app/v1"


@click.command()
@click.option(
    "--league-id",
    prompt="Enter league ID",
    help="The ID of the Sleeper league.",
)
@click.option(
    "--start-week",
    type=int,
    default=1,
    prompt="Enter start week #",
    help="The # of week to start counting.",
)
@click.option(
    "--end-week",
    type=int,
    default=18,
    prompt="Enter end week #",
    help="The # of week to end counting.",
)
@click.option(
    "--debug-all-weeks",
    is_flag=True,
    default=False,
    help="Whether to display debug info for all weeks during execution.",
)
@click.option(
    "--debug-week",
    type=int,
    required=False,
    default=None,
    help="The week # to debug, if provided.",
)
@click.option(
    "--debug-all-rosters",
    is_flag=True,
    default=False,
    help="Whether to display debug info for all rosters during execution.",
)
@click.option(
    "--debug-roster-id",
    type=int,
    required=False,
    default=None,
    help="The ID of the roster to debug, if provided.",
)
@click.option(
    "--debug-starters",
    is_flag=True,
    default=False,
    help="Whether to display debug info about starting players during execution.",
)
def league_season_totals(
    league_id: str,
    start_week: int,
    end_week: int,
    debug_all_weeks: bool,
    debug_week: Optional[int],
    debug_all_rosters: bool,
    debug_roster_id: Optional[int],
    debug_starters: bool,
) -> None:
    if debug_starters:
        players_response = requests.get(f"{SLEEPER_API_BASE_URL}/players/nfl")
        players: dict[int, dict[str, Any]] = players_response.json()

    league_url_base = f"{SLEEPER_API_BASE_URL}/league/{league_id}"

    users_response = requests.get(f"{league_url_base}/users")
    users_by_id: dict[str, dict[str, Any]] = {
        user["user_id"]: user for user in users_response.json()
    }

    rosters_by_id: dict[int, dict[str, Any]] = {}
    weekly_scores_by_roster_id: dict[int, list[float]] = {}

    rosters_response = requests.get(f"{league_url_base}/rosters")
    for roster in rosters_response.json():
        roster_id = roster["roster_id"]

        rosters_by_id.setdefault(roster_id, roster)
        weekly_scores_by_roster_id.setdefault(roster_id, [])

    for week in range(start_week, end_week + 1):
        week_matchups_response = requests.get(f"{league_url_base}/matchups/{week}")

        week_matchups: list[dict[str, Any]] = week_matchups_response.json()
        for week_matchup_team in week_matchups:
            roster_id = week_matchup_team["roster_id"]

            week_matchup_team_score: float = round(
                week_matchup_team["custom_points"]
                if "custom_points" in week_matchup_team
                and week_matchup_team["custom_points"]
                else week_matchup_team["points"],
                2,
            )

            weekly_scores_by_roster_id[roster_id].append(week_matchup_team_score)

            if (debug_all_weeks or debug_week == week) and (
                debug_all_rosters or roster_id == debug_roster_id
            ):
                click.echo(f"{week=}; {week_matchup_team=}")

                if debug_starters:
                    for starter_id in week_matchup_team["starters"]:
                        player = players[starter_id]
                        click.echo(
                            f"{player['first_name']} {player['last_name']} ({player['team']})"
                        )

    scores_by_roster_id: dict[int, float] = {
        roster_id: round(sum(weekly_scores), 2)
        for roster_id, weekly_scores in weekly_scores_by_roster_id.items()
    }

    for roster_id, total_score in sorted(
        scores_by_roster_id.items(), key=lambda x: x[1], reverse=True
    ):
        roster = rosters_by_id[roster_id]

        user = users_by_id[roster["owner_id"]]
        user_name = user["display_name"]
        team_name = (
            user["metadata"]["team_name"]
            if "metadata" in user
            and user["metadata"]
            and "team_name" in user["metadata"]
            and user["metadata"]["team_name"]
            else f"Team {user_name}"
        )

        output_string_parts: list[str] = [
            team_name,
            f"(@{user_name}):",
            str(total_score),
        ]

        if debug_all_weeks or debug_week:
            output_string_parts.append(str(weekly_scores_by_roster_id[roster_id]))

        if debug_all_rosters or debug_roster_id:
            output_string_parts.append(f"(roster ID: {roster_id})")

        click.echo(" ".join(output_string_parts))


if __name__ == "__main__":
    league_season_totals()
