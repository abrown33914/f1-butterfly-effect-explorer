import pandas as pd
from core.counterfactual import (
    get_pit_stops,
    simulate_no_pit,
    simulate_earlier_pit,
    recalculate_positions,
    get_regret_score
)

def calculate_team_regret(laps: pd.DataFrame) -> pd.DataFrame:
    """
    For every team, finds their worst strategy call of the race
    and scores how badly it hurt them.
    """
    pit_stops = get_pit_stops(laps)
    results = []

    for _, pit in pit_stops.iterrows():
        driver = pit['Driver']
        pit_lap = pit['PitLap']
        total_laps = laps['LapNumber'].max()

        if pit_lap < 5 or pit_lap > total_laps - 5:
            continue

        try:
            modified = simulate_no_pit(laps, driver, pit_lap)
            result = recalculate_positions(laps, modified, driver)
            regret = get_regret_score(laps, result, driver)

            driver_laps = laps[laps['Driver'] == driver]
            team = driver_laps['Team'].iloc[0] if len(driver_laps) > 0 else 'Unknown'

            results.append({
                'Team': team,
                'Driver': driver,
                'PitLap': pit_lap,
                'OriginalPosition': regret['original_position'],
                'CounterfactualPosition': regret['counterfactual_position'],
                'PositionsGained': regret['positions_gained'],
                'TimeDeltaSeconds': regret['time_delta_seconds'],
                'RegretScore': regret['regret_score'],
            })
        except Exception:
            continue

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.sort_values('RegretScore', ascending=False)
    return df.reset_index(drop=True)


def get_driver_regret_summary(laps: pd.DataFrame, driver: str) -> dict:
    """
    Deep dive regret analysis for a single driver.
    Tries skipping pit, pitting 3 laps earlier, and 3 laps later.
    Returns the scenario that would have helped them most.
    """
    pit_stops = get_pit_stops(laps)
    driver_pits = pit_stops[pit_stops['Driver'] == driver]

    if driver_pits.empty:
        return {'driver': driver, 'message': 'No pit stops found'}

    best_scenario = None
    best_gain = 0

    for _, pit in driver_pits.iterrows():
        pit_lap = int(pit['PitLap'])
        total_laps = int(laps['LapNumber'].max())

        scenarios = {
            'skip_pit': simulate_no_pit(laps, driver, pit_lap),
        }

        if pit_lap - 3 >= 3:
            scenarios['pit_3_earlier'] = simulate_earlier_pit(
                laps, driver, pit_lap, pit_lap - 3
            )
        if pit_lap + 3 <= total_laps - 3:
            scenarios['pit_3_later'] = simulate_earlier_pit(
                laps, driver, pit_lap, pit_lap + 3
            )

        for scenario_name, modified_laps in scenarios.items():
            try:
                result = recalculate_positions(laps, modified_laps, driver)
                regret = get_regret_score(laps, result, driver)

                if regret['positions_gained'] > best_gain:
                    best_gain = regret['positions_gained']
                    best_scenario = {
                        'driver': driver,
                        'pit_lap': pit_lap,
                        'scenario': scenario_name,
                        'positions_gained': regret['positions_gained'],
                        'time_delta': regret['time_delta_seconds'],
                        'regret_score': regret['regret_score'],
                        'original_position': regret['original_position'],
                        'best_possible_position': regret['counterfactual_position'],
                    }
            except Exception:
                continue

    if best_scenario is None:
        return {'driver': driver, 'message': 'No better scenario found'}

    return best_scenario


def rank_teams_by_regret(regret_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates regret scores per team and ranks them.
    The team at the top threw away the most points.
    """
    if regret_df.empty:
        return pd.DataFrame()

    team_summary = regret_df.groupby('Team').agg(
        TotalRegret=('RegretScore', 'sum'),
        WorstCall=('RegretScore', 'max'),
        AvgPositionsLost=('PositionsGained', 'mean'),
        PitStopsAnalyzed=('PitLap', 'count')
    ).reset_index()

    team_summary = team_summary.sort_values('TotalRegret', ascending=False)
    team_summary['RegretRank'] = range(1, len(team_summary) + 1)
    return team_summary.reset_index(drop=True)