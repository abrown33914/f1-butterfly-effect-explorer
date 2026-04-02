TEAM_COLORS = {
    "Red Bull Racing": "#3671C6",
    "Ferrari": "#E8002D",
    "Mercedes": "#27F4D2",
    "McLaren": "#FF8000",
    "Aston Martin": "#229971",
    "Alpine": "#FF87BC",
    "Williams": "#64C4FF",
    "RB": "#6692FF",
    "Kick Sauber": "#52E252",
    "Haas F1 Team": "#B6BABD",
}

DRIVER_COLORS = {
    # Red Bull
    "VER": "#3671C6",
    "PER": "#1B4FA8",
    # Ferrari
    "LEC": "#E8002D",
    "SAI": "#AD0024",
    # Mercedes
    "HAM": "#27F4D2",
    "RUS": "#19B5A0",
    # McLaren
    "NOR": "#FF8000",
    "PIA": "#CC6600",
    # Aston Martin
    "ALO": "#229971",
    "STR": "#167A59",
    # Alpine
    "OCO": "#FF87BC",
    "GAS": "#CC5F90",
    # Williams
    "ALB": "#64C4FF",
    "SAR": "#3A9FE0",
    # RB
    "RIC": "#6692FF",
    "TSU": "#3D6FE0",
    # Kick Sauber
    "BOT": "#52E252",
    "ZHO": "#35C035",
    # Haas
    "MAG": "#B6BABD",
    "HUL": "#888C8F",
    # Legacy drivers you might hit in older seasons
    "VET": "#229971",
    "RAI": "#E8002D",
    "GRO": "#B6BABD",
    "KVY": "#6692FF",
    "LAT": "#64C4FF",
    "MSC": "#B6BABD",
    "MAZ": "#52E252",
    "FIT": "#FF87BC",
    "BUT": "#27F4D2",
    "MAS": "#E8002D",
    "WEH": "#FF87BC",
    "ERI": "#52E252",
    "SIR": "#64C4FF",
    "HAR": "#B6BABD",
    "LEC": "#E8002D",
    "NOR": "#FF8000",
}

def get_driver_color(driver: str) -> str:
    return DRIVER_COLORS.get(driver, "#FFFFFF")

def get_team_color(team: str) -> str:
    return TEAM_COLORS.get(team, "#FFFFFF")