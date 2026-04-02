import streamlit as st
import pandas as pd
from core.session import (
    get_available_years, get_race_schedule,
    get_session, get_lap_data, get_drivers, get_circuit_info
)
from core.race_state import build_race_state, get_cumulative_times
from core.counterfactual import (
    get_pit_stops, simulate_no_pit, simulate_earlier_pit,
    recalculate_positions, find_biggest_what_ifs
)
from core.regret import calculate_team_regret, rank_teams_by_regret
from core.crash import get_retirements, what_if_no_retirement, get_all_retirement_what_ifs
from ui.timeline import build_position_timeline
from ui.standings import build_standings_comparison, build_gap_evolution
from ui.butterfly import build_ripple_chart, build_moment_card


def _get_valid_max_lap(laps: pd.DataFrame):
    if laps is None or laps.empty or 'LapNumber' not in laps.columns:
        return None

    max_lap = pd.to_numeric(laps['LapNumber'], errors='coerce').max()
    if pd.isna(max_lap):
        return None

    return int(max_lap)

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="🦋 F1 Butterfly Effect Explorer",
    page_icon="🦋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    body, .main { background-color: #0a0a0a; }
    .block-container { padding-top: 1.5rem; }
    h1, h2, h3, h4 { font-family: monospace; }
    .stSelectbox label, .stSlider label,
    .stRadio label { color: #aaa; font-family: monospace; }
    .stButton > button {
        background: #1a1a1a;
        color: white;
        border: 1px solid #333;
        border-radius: 6px;
        font-family: monospace;
        width: 100%;
    }
    .stButton > button:hover {
        background: #ff4444;
        border-color: #ff4444;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: monospace;
        font-size: 0.85rem;
    }
    .stMetric { background: #111; border-radius: 8px; padding: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────
st.markdown("# 🦋 F1 Butterfly Effect Explorer")
st.markdown("##### *Rewrite any race. See how one decision changed everything.*")

# ── Track Visual (only show when loaded) ────────────────────────
if st.session_state.get('circuit_info') is not None:
    info = st.session_state.circuit_info
    col_track, col_detail = st.columns([2, 1])
    
    with col_track:
        st.markdown(f"### 🏁 **{info['name']}**")
        st.markdown(f"*{info['circuit']}, {info['country']}*")
    
    with col_detail:
        st.markdown(f"**Round {info['round']}** · {info['date']}")
    
    st.divider()
else:
    st.divider()

# ── Session state init ─────────────────────────────────────────
for key in ['laps', 'race_state', 'what_ifs', 'cf_result',
            'active_scenario', 'drivers', 'retirements', 'crash_what_ifs', 'circuit_info']:
    if key not in st.session_state:
        st.session_state[key] = None

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏎️ Select Race")
    st.caption("Choose a year and event to load session data")

    year = st.selectbox("Year", get_available_years(), index=5)

    with st.spinner("Loading schedule..."):
        try:
            schedule = get_race_schedule(year)
            race_names = schedule['EventName'].tolist()
        except Exception as e:
            st.error(f"Could not load schedule: {e}")
            st.stop()

    race = st.selectbox("Race", race_names)
    session_type = st.selectbox(
        "Session",
        ["R", "Q", "FP1", "FP2", "FP3"],
        format_func=lambda x: {
            "R": "🏁 Race", "Q": "⏱️ Qualifying",
            "FP1": "FP1", "FP2": "FP2", "FP3": "FP3"
        }[x]
    )

    if st.button("🔄 Load Session", use_container_width=True):
        with st.spinner(f"Loading {race} {year}..."):
            try:
                session = get_session(year, race, session_type)
                laps = get_lap_data(session)
                valid_max_lap = _get_valid_max_lap(laps)
                if valid_max_lap is None:
                    raise ValueError("FastF1 returned no valid lap data for this session.")

                laps = get_cumulative_times(laps)
                race_state = build_race_state(laps)
                what_ifs = find_biggest_what_ifs(laps)
                retirements = get_retirements(laps)
                crash_what_ifs = get_all_retirement_what_ifs(laps)
                circuit_info = get_circuit_info(session, year, race)

                st.session_state.laps = laps
                st.session_state.race_state = race_state
                st.session_state.what_ifs = what_ifs
                st.session_state.drivers = get_drivers(session)
                st.session_state.retirements = retirements
                st.session_state.crash_what_ifs = crash_what_ifs
                st.session_state.circuit_info = circuit_info
                st.session_state.cf_result = None
                st.session_state.active_scenario = None
                st.success(f"✅ Loaded {race} {year}")
            except Exception as e:
                st.error(f"Failed to load session: {e}")

    # ── What-If controls (only show after load) ────────────────
    if st.session_state.laps is not None:
        max_lap = _get_valid_max_lap(st.session_state.laps)
        if max_lap is None:
            st.error("This session loaded without valid lap numbers, so the replay and what-if tools cannot run.")
            st.stop()

        st.divider()
        st.markdown("### 🔀 Pit Stop What-If")
        st.caption("Simulate alternative pit stop strategies")

        driver_select = st.selectbox(
            "Driver",
            st.session_state.drivers,
            key="driver_pit"
        )
        pit_lap_select = st.slider(
            "Pit Lap to Challenge",
            1,
            max_lap,
            20,
            key="pit_lap"
        )
        scenario = st.selectbox(
            "Scenario",
            ["skip_pit", "pit_3_earlier", "pit_3_later"],
            format_func=lambda x: {
                "skip_pit": "🚫 Skip This Pit Stop",
                "pit_3_earlier": "⬆️ Pit 3 Laps Earlier",
                "pit_3_later": "⬇️ Pit 3 Laps Later"
            }[x],
            key="scenario_pit"
        )

        if st.button("⚡ Run Pit What-If", use_container_width=True):
            with st.spinner("Calculating butterfly effect..."):
                try:
                    laps = st.session_state.laps
                    if scenario == "skip_pit":
                        modified = simulate_no_pit(laps, driver_select, pit_lap_select)
                    elif scenario == "pit_3_earlier":
                        modified = simulate_earlier_pit(
                            laps, driver_select, pit_lap_select, pit_lap_select - 3
                        )
                    else:
                        modified = simulate_earlier_pit(
                            laps, driver_select, pit_lap_select, pit_lap_select + 3
                        )

                    cf_result = recalculate_positions(laps, modified, driver_select)
                    orig_last = laps[laps['Driver'] == driver_select].sort_values('LapNumber').iloc[-1]
                    cf_last = cf_result[cf_result['Driver'] == driver_select].sort_values('LapNumber').iloc[-1]

                    st.session_state.cf_result = cf_result
                    original_position = orig_last.get('Position', 99)
                    if pd.isna(original_position):
                        original_position = 99

                    best_possible_position = cf_last.get('NewPosition', 99)
                    if pd.isna(best_possible_position):
                        best_possible_position = 99

                    st.session_state.active_scenario = {
                        'driver': driver_select,
                        'pit_lap': pit_lap_select,
                        'scenario': scenario,
                        'original_position': int(original_position),
                        'best_possible_position': int(best_possible_position),
                        'time_delta': round(
                            cf_result[cf_result['Driver'] == driver_select]['LapTimeSeconds'].sum() -
                            laps[laps['Driver'] == driver_select]['LapTimeSeconds'].sum(), 2
                        )
                    }
                    st.success("Done!")
                except Exception as e:
                    st.error(f"What-if failed: {e}")

        # ── Crash what-if controls ─────────────────────────────
        st.divider()
        st.markdown("### 💥 Crash What-If")
        st.caption("Project retirements to race completion")

        retirements = st.session_state.retirements
        if retirements is not None and not retirements.empty:
            retired_drivers = retirements['Driver'].tolist()
            crash_driver = st.selectbox(
                "Retired Driver",
                retired_drivers,
                key="driver_crash"
            )
            pace_strategy = st.selectbox(
                "Projected Pace",
                ["median", "best", "last5"],
                format_func=lambda x: {
                    "median": "📊 Median Pre-Retirement Pace",
                    "best": "🚀 Best Lap Pace (Optimistic)",
                    "last5": "📉 Last 5 Laps Pace (Conservative)"
                }[x],
                key="pace_strat"
            )

            if st.button("💥 Run Crash What-If", use_container_width=True):
                with st.spinner(f"Simulating {crash_driver} finishing..."):
                    try:
                        result = what_if_no_retirement(
                            st.session_state.laps,
                            crash_driver,
                            pace_strategy
                        )
                        st.session_state.crash_result = result
                        st.success("Done!")
                    except Exception as e:
                        st.error(f"Crash what-if failed: {e}")
        else:
            st.info("No retirements detected in this session.")

# ── Main dashboard ─────────────────────────────────────────────
if st.session_state.laps is not None:
    laps = st.session_state.laps
    race_state = st.session_state.race_state
    what_ifs = st.session_state.what_ifs or []
    retirements = st.session_state.retirements
    crash_what_ifs = st.session_state.crash_what_ifs or []

    # ── Top metrics ───────────────────────────────────────────
    total_laps = _get_valid_max_lap(laps)
    total_drivers = laps['Driver'].nunique()
    total_pits = laps['PitInTime'].notna().sum()
    total_retirements = len(retirements) if retirements is not None else 0

    st.markdown("### 📊 Session Stats")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏁 Total Laps", total_laps)
    c2.metric("🏎️ Drivers", total_drivers)
    c3.metric("🛞 Pit Stops", int(total_pits))
    c4.metric("❌ Retirements", total_retirements)

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏎️ Race Replay",
        "🦋 Pit Stop What-Ifs",
        "💥 Crash What-Ifs",
        "📊 Standings Shift",
        "😬 Team Regret"
    ])

    # ── Tab 1: Race Replay ────────────────────────────────────
    with tab1:
        st.plotly_chart(
            build_position_timeline(race_state),
            use_container_width=True
        )

    # ── Tab 2: Pit Stop What-Ifs ──────────────────────────────
    with tab2:
        if what_ifs:
            st.plotly_chart(
                build_ripple_chart(what_ifs),
                use_container_width=True
            )
            st.markdown("#### 🔍 Top Moments")
            for i, w in enumerate(what_ifs[:5]):
                ca, cb, cc, cd = st.columns([2, 1, 1, 1])
                ca.write(f"**{w['driver']}** — Lap {w['pit_lap']}")
                cb.write(f"Impact: `{w['regret_score']:.1f}`")
                pos = w['positions_gained']
                cc.write(f"{'🟢' if pos > 0 else '🔴'} {'+' if pos > 0 else ''}{pos} pos")
                if cd.button("Explore →", key=f"pit_explore_{i}"):
                    st.session_state.active_scenario = w
        else:
            st.info("Load a race to see pit stop what-ifs.")

    # ── Tab 3: Crash What-Ifs ─────────────────────────────────
    with tab3:
        if retirements is not None and not retirements.empty:
            st.markdown("#### 💥 Drivers Who Retired This Race")
            display_ret = retirements[['Driver', 'Team', 'LastLap', 'LapsMissed']].copy()
            display_ret.columns = ['Driver', 'Team', 'Retired On Lap', 'Laps Missed']
            st.dataframe(display_ret, use_container_width=True)

            st.divider()

            if crash_what_ifs:
                st.markdown("#### 🔮 If Nobody Retired — Projected Finishes")
                for result in crash_what_ifs:
                    col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
                    col_a.metric(
                        "Driver",
                        result['driver']
                    )
                    col_b.metric(
                        "Retired P",
                        f"P{result['running_position_at_retirement']}"
                    )
                    col_c.metric(
                        "Would've Finished",
                        f"P{result['projected_finish']}",
                        delta=f"{result['running_position_at_retirement'] - result['projected_finish']:+d} pos"
                    )
                    col_d.progress(
                        min(result['laps_missed'] / max(total_laps, 1), 1.0),
                        text=f"{result['laps_missed']} laps missed"
                    )
                    st.divider()

            # ── Deep dive on selected crash driver ────────────
            if 'crash_result' in st.session_state and st.session_state.crash_result:
                result = st.session_state.crash_result
                if 'projected_finish' in result:
                    st.markdown(f"#### 🔬 Deep Dive — {result['driver']}")

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Retired On", f"Lap {result['retirement_lap']}")
                    m2.metric("Running Position", f"P{result['running_position_at_retirement']}")
                    m3.metric("Projected Finish", f"P{result['projected_finish']}")
                    m4.metric("Laps Missed", result['laps_missed'])

                    if result.get('cf_result') is not None:
                        st.plotly_chart(
                            build_gap_evolution(
                                laps,
                                result['cf_result'],
                                result['driver']
                            ),
                            use_container_width=True
                        )
        else:
            st.info("No retirements detected in this race.")

    # ── Tab 4: Standings Shift ────────────────────────────────
    with tab4:
        if st.session_state.cf_result is not None and st.session_state.active_scenario is not None:
            scenario_data = st.session_state.active_scenario
            st.plotly_chart(
                build_moment_card(scenario_data),
                use_container_width=True
            )
            col_l, col_r = st.columns(2)
            with col_l:
                st.plotly_chart(
                    build_standings_comparison(
                        laps,
                        st.session_state.cf_result,
                        scenario_data['driver'],
                        scenario_data['pit_lap']
                    ),
                    use_container_width=True
                )
            with col_r:
                st.plotly_chart(
                    build_gap_evolution(
                        laps,
                        st.session_state.cf_result,
                        scenario_data['driver']
                    ),
                    use_container_width=True
                )
        else:
            st.info("Run a pit stop what-if from the sidebar to see the standings shift.")

    # ── Tab 5: Team Regret ────────────────────────────────────
    with tab5:
        with st.spinner("Calculating team regret..."):
            regret_df = calculate_team_regret(laps)
            if not regret_df.empty:
                team_regret = rank_teams_by_regret(regret_df)
                st.markdown("#### 😬 Which team hurt themselves most?")
                st.dataframe(
                    team_regret.style.background_gradient(
                        subset=['TotalRegret'], cmap='Reds'
                    ),
                    use_container_width=True
                )
                st.divider()
                st.markdown("#### 🔬 Full Pit Stop Analysis")
                st.dataframe(regret_df, use_container_width=True)
            else:
                st.info("No regret data available for this session.")

# ── Empty state ────────────────────────────────────────────────
else:
    st.markdown("""
    <div style='text-align:center; padding: 4rem; color: #444;'>
        <div style='font-size: 4rem;'>🦋</div>
        <h3 style='font-family:monospace;'>Select a race and hit Load Session</h3>
        <p style='font-family:monospace;'>
            Every pit stop. Every crash. Every call.<br>
            One toggle away from rewriting history.
        </p>
    </div>
    """, unsafe_allow_html=True)