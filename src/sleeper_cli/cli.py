from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed, wait
from typing import Any, Optional

import click

from .api_client import (
    SleeperLeagueApiClient,
    SleeperNflApiClient,
)


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
    sleeper_league_api_client = SleeperLeagueApiClient(league_id)

    with ThreadPoolExecutor() as executor:
        first_wave_futures: list[Future] = [
            executor.submit(sleeper_league_api_client.fetch_users_by_id),
            executor.submit(sleeper_league_api_client.fetch_rosters_by_id),
            executor.submit(
                SleeperNflApiClient().fetch_players if debug_starters else lambda: {}
            ),
        ]

        wait(first_wave_futures)

        users_by_id: dict[str, dict[str, Any]] = first_wave_futures[0].result()
        rosters_by_id: dict[int, dict[str, Any]] = first_wave_futures[1].result()
        players: dict[int, dict[str, Any]] = first_wave_futures[2].result()

    weekly_scores_by_roster_id: dict[int, list[float]] = defaultdict(list)

    with ThreadPoolExecutor() as executor:
        week_matchups_by_number: dict[int, list[dict[str, Any]]] = {}

        for fetch_matchup in as_completed(
            executor.submit(sleeper_league_api_client.fetch_matchups, week)
            for week in range(start_week, end_week + 1)
        ):
            week, matchups = fetch_matchup.result()
            week_matchups_by_number[week] = matchups

        # still ensure we order the weeks properly after parallelizing work
        for week, matchups in sorted(week_matchups_by_number.items()):
            for week_matchup_team in matchups:
                roster_id = week_matchup_team["roster_id"]

                week_matchup_team_initial_score: float = (
                    week_matchup_team["custom_points"]
                    if "custom_points" in week_matchup_team
                    and week_matchup_team["custom_points"]
                    else week_matchup_team["points"]
                )

                week_matchup_team_score = round(week_matchup_team_initial_score, 2)

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
