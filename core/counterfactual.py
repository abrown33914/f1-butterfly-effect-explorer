import pandas as pd
import numpy as np

PIT_STOP_DELTA = 22.0  # average time lost in a pit stop in seconds

def get_pit_stops(laps: pd.DataFrame) -> pd.DataFrame:
    """Extract all pit stops from lap data."""
    pits = laps[laps['PitInTime'].notna()].copy()
    pits = pits[['Driver', 'LapNumber', 'Compound', 'TyreLife', 'Team']].copy()
    pits = pits.rename(columns={'LapNumber': 'PitLap'})
    return pits.reset_index(drop=True)

def simulate_no_pit(
    laps: pd.DataFrame,
    driver: str,
    pit_lap: int,
    deg_rate: float = 0.08
) -> pd.DataFrame:
    """
    Simulate what happens if a driver DOESN'T pit on a given lap.
    Models tire degradation continuing instead of fresh rubber.
    Returns modified lap times for that driver after the skipped pit.
    """
    driver_laps = laps[laps['Driver'] == driver].copy()
    modified = []

    for _, row in driver_laps.iterrows():
        if row['LapNumber'] > pit_lap:
            extra_deg = (row['LapNumber'] - pit_lap) * deg_rate
            row = row.copy()
            row['LapTimeSeconds'] = row['LapTimeSeconds'] + extra_deg
            row['Counterfactual'] = True
        else:
            row = row.copy()
            row['Counterfactual'] = False
        modified.append(row)

    result = pd.DataFrame(modified)
    # Remove the pit stop time loss on that lap
    result.loc[result['LapNumber'] == pit_lap, 'LapTimeSeconds'] -= PIT_STOP_DELTA
    return result

def simulate_earlier_pit(
    laps: pd.DataFrame,
    driver: str,
    original_pit_lap: int,
    new_pit_lap: int,
    deg_rate: float = 0.08
) -> pd.DataFrame:
    """
    Simulate pitting earlier or later than actual.
    Adjusts tire age and lap times accordingly.
    """
    driver_laps = laps[laps['Driver'] == driver].copy()
    modified = []

    for _, row in driver_laps.iterrows():
        row = row.copy()
        lap = row['LapNumber']

        if new_pit_lap < original_pit_lap:
            # Pitted earlier — fresher tires sooner but more deg later
            if lap == new_pit_lap:
                row['LapTimeSeconds'] += PIT_STOP_DELTA
                row['Counterfactual'] = True
            elif new_pit_lap < lap < original_pit_lap:
                laps_on_new_tire = lap - new_pit_lap
                row['LapTimeSeconds'] -= (laps_on_new_tire * deg_rate * 0.5)
                row['Counterfactual'] = True
            elif lap == original_pit_lap:
                # Cancel the original pit
                row['LapTimeSeconds'] -= PIT_STOP_DELTA
                row['Counterfactual'] = True
            else:
                row['Counterfactual'] = False
        else:
            # Pitted later — more degradation before pit
            if new_pit_lap < lap <= original_pit_lap:
                extra_laps = lap - new_pit_lap
                row['LapTimeSeconds'] += (extra_laps * deg_rate)
                row['Counterfactual'] = True
            elif lap == original_pit_lap:
                row['LapTimeSeconds'] -= PIT_STOP_DELTA
                row['Counterfactual'] = True
            else:
                row['Counterfactual'] = False

        modified.append(row)

    return pd.DataFrame(modified)

def recalculate_positions(
    laps: pd.DataFrame,
    modified_driver_laps: pd.DataFrame,
    driver: str
) -> pd.DataFrame:
    """
    Takes the full race lap data, swaps in the counterfactual laps
    for one driver, recalculates cumulative times, and re-ranks positions.
    Returns full race state with new positions.
    """
    # Swap in modified laps
    other_laps = laps[laps['Driver'] != driver].copy()
    combined = pd.concat([other_laps, modified_driver_laps], ignore_index=True)
    combined = combined.sort_values(['Driver', 'LapNumber'])

    # Cumulative time per driver
    combined['CumulativeTime'] = combined.groupby('Driver')['LapTimeSeconds'].cumsum()

    # Re-rank positions per lap
    combined['NewPosition'] = combined.groupby('LapNumber')['CumulativeTime'].rank(method='first')

    return combined

def get_regret_score(
    original_laps: pd.DataFrame,
    counterfactual_laps: pd.DataFrame,
    driver: str
) -> dict:
    """
    Calculates how much a strategy call hurt or helped a driver.
    Returns a regret score — positive = strategy cost them positions.
    """
    orig = original_laps[original_laps['Driver'] == driver].copy()
    cf = counterfactual_laps[counterfactual_laps['Driver'] == driver].copy()

    orig_final = orig.sort_values('LapNumber').iloc[-1]
    cf_final = cf.sort_values('LapNumber').iloc[-1]

    orig_pos = orig_final.get('Position', 99)
    cf_pos = cf_final.get('NewPosition', 99)

    if pd.isna(orig_pos):
        orig_pos = 99
    if pd.isna(cf_pos):
        cf_pos = 99

    positions_gained = orig_pos - cf_pos
    time_delta = (
        cf['LapTimeSeconds'].sum() - orig['LapTimeSeconds'].sum()
    )

    return {
        'driver': driver,
        'original_position': int(orig_pos),
        'counterfactual_position': int(cf_pos),
        'positions_gained': int(positions_gained),
        'time_delta_seconds': round(time_delta, 3),
        'regret_score': round(abs(time_delta) * abs(positions_gained), 2)
    }

def find_biggest_what_ifs(
    laps: pd.DataFrame,
    top_n: int = 5
) -> list:
    """
    Automatically scans all pit stops in the race and scores each one
    for maximum drama — returns the top N most interesting what-ifs.
    """
    pit_stops = get_pit_stops(laps)
    scenarios = []

    for _, pit in pit_stops.iterrows():
        driver = pit['Driver']
        pit_lap = pit['PitLap']
        total_laps = laps['LapNumber'].max()

        if pit_lap < 5 or pit_lap > total_laps - 5:
            continue

        # Try skipping this pit
        modified = simulate_no_pit(laps, driver, pit_lap)
        result = recalculate_positions(laps, modified, driver)
        regret = get_regret_score(laps, result, driver)

        scenarios.append({
            'driver': driver,
            'pit_lap': pit_lap,
            'type': 'skipped_pit',
            'regret_score': regret['regret_score'],
            'positions_gained': regret['positions_gained'],
            'time_delta': regret['time_delta_seconds']
        })

    scenarios.sort(key=lambda x: x['regret_score'], reverse=True)
    return scenarios[:top_n]