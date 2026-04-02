import pandas as pd
import numpy as np
from core.counterfactual import recalculate_positions, get_regret_score

def get_retirements(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Detects drivers who retired mid race — their laps stop
    significantly before the race ends.
    """
    total_laps = laps['LapNumber'].max()
    last_lap_per_driver = laps.groupby('Driver')['LapNumber'].max().reset_index()
    last_lap_per_driver.columns = ['Driver', 'LastLap']

    # Anyone who stopped more than 3 laps before the end
    retirements = last_lap_per_driver[
        last_lap_per_driver['LastLap'] < total_laps - 3
    ].copy()

    retirements['LapsCompleted'] = retirements['LastLap']
    retirements['LapsMissed'] = total_laps - retirements['LastLap']

    # Get team info
    driver_teams = laps.groupby('Driver')['Team'].first().reset_index()
    retirements = retirements.merge(driver_teams, on='Driver', how='left')

    return retirements.sort_values('LastLap').reset_index(drop=True)


def simulate_no_crash(
    laps: pd.DataFrame,
    driver: str,
    retirement_lap: int,
    strategy: str = 'median'
) -> pd.DataFrame:
    """
    Simulates a driver finishing the race as if they never retired.
    Projects lap times from their pre-retirement pace.

    strategy:
        'median' — uses their median lap time before retirement
        'best'   — uses their best lap time (optimistic)
        'last5'  — uses average of last 5 laps before retirement
    """
    total_laps = int(laps['LapNumber'].max())
    driver_laps = laps[laps['Driver'] == driver].copy()
    pre_retirement = driver_laps[driver_laps['LapNumber'] <= retirement_lap]

    if pre_retirement.empty:
        return driver_laps

    # Pick pace estimate
    if strategy == 'best':
        pace = pre_retirement['LapTimeSeconds'].min()
    elif strategy == 'last5':
        pace = pre_retirement.tail(5)['LapTimeSeconds'].mean()
    else:
        pace = pre_retirement['LapTimeSeconds'].median()

    pace = float(pace)

    # Get last known compound and tyre life
    last_row = pre_retirement.sort_values('LapNumber').iloc[-1]
    last_compound = last_row.get('Compound', 'MEDIUM')
    last_tyre_life = last_row.get('TyreLife', 10)
    team = last_row.get('Team', 'Unknown')

    # Build projected laps
    projected = []
    for lap_num in range(retirement_lap + 1, total_laps + 1):
        # Add slight degradation per lap
        deg = (lap_num - retirement_lap) * 0.05
        projected.append({
            'Driver': driver,
            'Team': team,
            'LapNumber': lap_num,
            'LapTimeSeconds': pace + deg,
            'LapTime': pd.NaT,
            'Stint': last_row.get('Stint', 1) + 1,
            'TyreLife': last_tyre_life + (lap_num - retirement_lap),
            'Compound': last_compound,
            'PitInTime': pd.NaT,
            'PitOutTime': pd.NaT,
            'Position': None,
            'CumulativeTime': None,
            'Counterfactual': True
        })

    proj_df = pd.DataFrame(projected)
    combined = pd.concat([driver_laps, proj_df], ignore_index=True)
    combined = combined.sort_values('LapNumber').reset_index(drop=True)

    # Recalculate cumulative time
    combined['CumulativeTime'] = combined['LapTimeSeconds'].cumsum()

    return combined


def what_if_no_retirement(
    laps: pd.DataFrame,
    driver: str,
    strategy: str = 'median'
) -> dict:
    retirements = get_retirements(laps)
    driver_retirement = retirements[retirements['Driver'] == driver]

    if driver_retirement.empty:
        return {
            'driver': driver,
            'message': f"{driver} did not retire in this race"
        }

    retirement_lap = int(driver_retirement.iloc[0]['LastLap'])
    total_laps = int(laps['LapNumber'].max())

    projected_laps = simulate_no_crash(laps, driver, retirement_lap, strategy)
    cf_result = recalculate_positions(laps, projected_laps, driver)

    # Final position in counterfactual — safely handle NaN
    cf_final = cf_result[cf_result['Driver'] == driver].sort_values('LapNumber').iloc[-1]
    raw_cf_pos = cf_final.get('NewPosition', None)
    cf_pos = int(raw_cf_pos) if raw_cf_pos is not None and not pd.isna(raw_cf_pos) else 99

    # Position at retirement — safely handle NaN
    running_pos = laps[
        (laps['Driver'] == driver) &
        (laps['LapNumber'] == retirement_lap)
    ]
    if not running_pos.empty:
        raw_pos = running_pos.iloc[0].get('Position', None)
        running_position = int(raw_pos) if raw_pos is not None and not pd.isna(raw_pos) else 99
    else:
        running_position = 99

    return {
        'driver': driver,
        'retirement_lap': retirement_lap,
        'laps_missed': total_laps - retirement_lap,
        'running_position_at_retirement': running_position,
        'projected_finish': cf_pos,
        'positions_recovered': running_position - cf_pos,
        'pace_strategy': strategy,
        'cf_result': cf_result,
        'projected_laps': projected_laps
    }


def get_all_retirement_what_ifs(laps: pd.DataFrame) -> list:
    """
    Runs what_if_no_retirement for every retired driver in the race.
    Returns sorted list by projected positions gained.
    """
    retirements = get_retirements(laps)

    if retirements.empty:
        return []

    results = []
    for _, row in retirements.iterrows():
        driver = row['Driver']
        try:
            result = what_if_no_retirement(laps, driver)
            if 'projected_finish' in result:
                results.append(result)
        except Exception:
            continue

    results.sort(key=lambda x: x.get('running_position_at_retirement', 99))
    return results