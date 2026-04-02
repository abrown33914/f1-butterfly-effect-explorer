import fastf1
import pandas as pd
import os

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

def get_available_years():
    return list(range(2018, 2025))

def get_race_schedule(year: int):
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    races = schedule[schedule['EventFormat'] != 'testing']
    return races[['EventName', 'RoundNumber']].dropna()

def get_session(year: int, race_name: str, session_type: str = 'R'):
    session = fastf1.get_session(year, race_name, session_type)
    session.load(telemetry=False, weather=False, messages=False)
    return session

def get_lap_data(session) -> pd.DataFrame:
    laps = session.laps.copy()

    # Only keep columns that exist in this session
    wanted = [
        'Driver', 'Team', 'LapNumber', 'LapTime',
        'Stint', 'TyreLife', 'Compound',
        'PitInTime', 'PitOutTime', 'Position'
    ]
    available = [c for c in wanted if c in laps.columns]
    laps = laps[available].copy()

    # Add missing columns as NaN so rest of app doesn't break
    for col in wanted:
        if col not in laps.columns:
            laps[col] = pd.NaT if col in ['PitInTime', 'PitOutTime', 'LapTime'] else None

    laps['LapTimeSeconds'] = pd.to_numeric(
        laps['LapTime'].dt.total_seconds(), errors='coerce'
    )

    # Drop rows with no lap time at all
    laps = laps.dropna(subset=['LapTimeSeconds'])
    laps = laps[laps['LapTimeSeconds'] > 0]

    # Safely convert LapNumber to int
    laps['LapNumber'] = pd.to_numeric(laps['LapNumber'], errors='coerce')
    laps = laps.dropna(subset=['LapNumber'])
    laps['LapNumber'] = laps['LapNumber'].astype(int)

    return laps

def get_drivers(session):
    return sorted(session.laps['Driver'].unique().tolist())

def get_circuit_info(session: object, year: int, race_name: str):
    """Extract circuit and race metadata from FastF1 session."""
    try:
        circuit = session.circuit
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        race_info = schedule[schedule['EventName'] == race_name].iloc[0] if len(schedule) > 0 else {}
        
        return {
            'name': race_name,
            'circuit': getattr(circuit, 'name', 'Unknown Circuit') if hasattr(session, 'circuit') else 'Unknown Circuit',
            'location': getattr(circuit, 'Location', 'Unknown') if hasattr(session, 'circuit') else 'Unknown',
            'country': getattr(circuit, 'Country', 'Unknown') if hasattr(session, 'circuit') else 'Unknown',
            'round': int(race_info.get('RoundNumber', 0)) if isinstance(race_info, pd.Series) else 0,
            'date': str(race_info.get('EventDate', 'Unknown')[:10]) if isinstance(race_info, pd.Series) and 'EventDate' in race_info else 'Unknown',
        }
    except Exception as e:
        return {
            'name': race_name,
            'circuit': 'Unknown Circuit',
            'location': 'Unknown',
            'country': 'Unknown',
            'round': 0,
            'date': 'Unknown'
        }