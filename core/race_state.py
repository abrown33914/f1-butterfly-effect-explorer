import pandas as pd
import numpy as np

def build_race_state(laps: pd.DataFrame) -> pd.DataFrame:
    state_frames = []

    for lap_num in sorted(laps['LapNumber'].unique()):
        lap_slice = laps[laps['LapNumber'] == lap_num].copy()
        lap_slice = lap_slice.dropna(subset=['LapTimeSeconds'])
        lap_slice = lap_slice[lap_slice['LapTimeSeconds'] > 0]

        if lap_slice.empty:
            continue

        # Safely handle Position column. Some sessions, especially qualifying,
        # do not expose official positions, so fall back to lap-time order.
        if 'Position' in lap_slice.columns:
            lap_slice['Position'] = pd.to_numeric(
                lap_slice['Position'], errors='coerce'
            )
            lap_slice = lap_slice.dropna(subset=['Position'])
            if lap_slice.empty:
                lap_slice = laps[laps['LapNumber'] == lap_num].copy()
                lap_slice = lap_slice.dropna(subset=['LapTimeSeconds'])
                lap_slice = lap_slice[lap_slice['LapTimeSeconds'] > 0]
                lap_slice = lap_slice.sort_values(['LapTimeSeconds', 'Driver'])
                lap_slice['Position'] = range(1, len(lap_slice) + 1)
            else:
                lap_slice['Position'] = lap_slice['Position'].astype(int)
        else:
            lap_slice = lap_slice.sort_values(['LapTimeSeconds', 'Driver'])
            lap_slice['Position'] = range(1, len(lap_slice) + 1)

        lap_slice['LapNumber'] = lap_num
        state_frames.append(lap_slice[[
            'LapNumber', 'Driver', 'Team',
            'Position', 'LapTimeSeconds',
            'Compound', 'TyreLife'
        ]])

    if not state_frames:
        return pd.DataFrame()

    state = pd.concat(state_frames, ignore_index=True)
    return state


def get_cumulative_times(laps: pd.DataFrame) -> pd.DataFrame:
    laps = laps.copy().sort_values(['Driver', 'LapNumber'])

    # Clean LapTimeSeconds before cumsum
    laps['LapTimeSeconds'] = pd.to_numeric(
        laps['LapTimeSeconds'], errors='coerce'
    )
    laps['LapTimeSeconds'] = laps['LapTimeSeconds'].fillna(0)

    laps['CumulativeTime'] = laps.groupby('Driver')['LapTimeSeconds'].cumsum()
    return laps


def get_position_changes(state: pd.DataFrame) -> pd.DataFrame:
    if state.empty:
        return pd.DataFrame()

    state = state.sort_values(['Driver', 'LapNumber'])
    state['PrevPosition'] = state.groupby('Driver')['Position'].shift(1)
    state['PositionDelta'] = state['PrevPosition'] - state['Position']
    changes = state[state['PositionDelta'] != 0].dropna(subset=['PositionDelta'])
    return changes