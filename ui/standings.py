import plotly.graph_objects as go
import pandas as pd
from assets.team_colors import DRIVER_COLORS

def build_standings_comparison(
    original: pd.DataFrame,
    counterfactual: pd.DataFrame,
    driver: str,
    pit_lap: int
) -> go.Figure:
    """
    Side by side final standings — real vs what if.
    Shows exactly how the order reshuffles.
    """
    last_lap = original['LapNumber'].max()

    orig_final = (
        original[original['LapNumber'] == last_lap]
        .sort_values('Position')[['Driver', 'Position']]
        .reset_index(drop=True)
    )

    cf_final = (
        counterfactual[counterfactual['LapNumber'] == last_lap]
        .sort_values('NewPosition')[['Driver', 'NewPosition']]
        .rename(columns={'NewPosition': 'Position'})
        .reset_index(drop=True)
    )

    fig = go.Figure()

    # Original standings
    fig.add_trace(go.Bar(
        x=orig_final['Driver'],
        y=orig_final['Position'],
        name='Actual Result',
        marker_color=[
            DRIVER_COLORS.get(d, '#555') for d in orig_final['Driver']
        ],
        opacity=0.6,
        text=orig_final['Position'],
        textposition='outside',
    ))

    # Counterfactual standings
    fig.add_trace(go.Bar(
        x=cf_final['Driver'],
        y=cf_final['Position'],
        name=f'If Lap {pit_lap} Pit Skipped',
        marker_color=[
            DRIVER_COLORS.get(d, '#555') for d in cf_final['Driver']
        ],
        opacity=1.0,
        text=cf_final['Position'],
        textposition='outside',
    ))

    fig.update_layout(
        title=f"📊 Final Standings — Real vs What If ({driver}, Lap {pit_lap})",
        xaxis_title="Driver",
        yaxis_title="Finishing Position",
        yaxis=dict(autorange='reversed', tickmode='linear', tick0=1, dtick=1),
        barmode='group',
        plot_bgcolor='#0f0f0f',
        paper_bgcolor='#0f0f0f',
        font=dict(color='white', family='monospace'),
        legend=dict(bgcolor='#1a1a1a', bordercolor='#333', borderwidth=1),
    )

    return fig


def build_gap_evolution(
    original: pd.DataFrame,
    counterfactual: pd.DataFrame,
    driver: str
) -> go.Figure:
    """
    Shows how the gap between the driver and their nearest rival
    changes under the counterfactual scenario vs reality.
    """
    orig_driver = original[original['Driver'] == driver].sort_values('LapNumber')
    cf_driver = counterfactual[counterfactual['Driver'] == driver].sort_values('LapNumber')

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=orig_driver['LapNumber'],
        y=orig_driver['CumulativeTime'] if 'CumulativeTime' in orig_driver.columns else orig_driver['LapTimeSeconds'].cumsum(),
        name='Actual',
        line=dict(color=DRIVER_COLORS.get(driver, '#fff'), width=2, dash='dot'),
    ))

    fig.add_trace(go.Scatter(
        x=cf_driver['LapNumber'],
        y=cf_driver['CumulativeTime'] if 'CumulativeTime' in cf_driver.columns else cf_driver['LapTimeSeconds'].cumsum(),
        name='What If',
        line=dict(color=DRIVER_COLORS.get(driver, '#fff'), width=3),
    ))

    fig.update_layout(
        title=f"⏱️ Cumulative Time — {driver}: Actual vs What If",
        xaxis_title="Lap",
        yaxis_title="Cumulative Race Time (s)",
        plot_bgcolor='#0f0f0f',
        paper_bgcolor='#0f0f0f',
        font=dict(color='white', family='monospace'),
        legend=dict(bgcolor='#1a1a1a', bordercolor='#333', borderwidth=1),
    )

    return fig