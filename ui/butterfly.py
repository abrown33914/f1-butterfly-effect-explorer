import plotly.graph_objects as go
import pandas as pd
from assets.team_colors import DRIVER_COLORS

def build_ripple_chart(what_ifs: list) -> go.Figure:
    """
    The signature visual.
    Shows all detected what-if moments ranked by drama score.
    Each bar pulses with the regret score — the bigger the bar,
    the more that decision changed the race.
    """
    if not what_ifs:
        return go.Figure()

    df = pd.DataFrame(what_ifs).sort_values('regret_score', ascending=True)

    labels = [
        f"{row['driver']} — Lap {row['pit_lap']}"
        for _, row in df.iterrows()
    ]

    colors = [
        DRIVER_COLORS.get(row['driver'], '#888')
        for _, row in df.iterrows()
    ]

    fig = go.Figure(go.Bar(
        x=df['regret_score'],
        y=labels,
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color='rgba(255,255,255,0.1)', width=1)
        ),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Regret Score: %{x:.1f}<br>"
            "<extra></extra>"
        ),
        text=[
            f"{'+' if r > 0 else ''}{r} pos"
            for r in df['positions_gained']
        ],
        textposition='outside',
        textfont=dict(color='white', size=11)
    ))

    fig.update_layout(
        title="🦋 F1 Butterfly Effect — Biggest What-If Moments This Race",
        xaxis_title="Impact Score (higher = more impact)",
        plot_bgcolor='#0f0f0f',
        paper_bgcolor='#0f0f0f',
        font=dict(color='white', family='monospace'),
        margin=dict(l=180, r=60, t=60, b=40),
        xaxis=dict(gridcolor='#222'),
        yaxis=dict(gridcolor='#222'),
    )

    return fig


def build_moment_card(scenario: dict) -> go.Figure:
    """
    A single dramatic moment card — shown when user clicks a what-if.
    Big bold text showing what happened vs what could have happened.
    """
    driver = scenario.get('driver', '???')
    pit_lap = scenario.get('pit_lap', '?')
    orig_pos = scenario.get('original_position', '?')
    cf_pos = scenario.get('best_possible_position', '?')
    delta = scenario.get('time_delta', 0)
    scenario_type = scenario.get('scenario', 'skip_pit').replace('_', ' ').upper()

    delta_str = f"+{delta:.1f}s" if delta > 0 else f"{delta:.1f}s"

    fig = go.Figure()

    fig.add_annotation(
        text=f"<b>{driver}</b>",
        x=0.5, y=0.85,
        xref='paper', yref='paper',
        showarrow=False,
        font=dict(size=36, color=DRIVER_COLORS.get(driver, '#fff'), family='monospace'),
        align='center'
    )
    fig.add_annotation(
        text=f"Lap {pit_lap} — {scenario_type}",
        x=0.5, y=0.65,
        xref='paper', yref='paper',
        showarrow=False,
        font=dict(size=16, color='#aaa', family='monospace'),
        align='center'
    )
    fig.add_annotation(
        text=f"P{orig_pos} → P{cf_pos}",
        x=0.5, y=0.42,
        xref='paper', yref='paper',
        showarrow=False,
        font=dict(size=48, color='#ff4444' if cf_pos < orig_pos else '#44ff88', family='monospace'),
        align='center'
    )
    fig.add_annotation(
        text=f"{delta_str} difference",
        x=0.5, y=0.22,
        xref='paper', yref='paper',
        showarrow=False,
        font=dict(size=20, color='#888', family='monospace'),
        align='center'
    )

    fig.update_layout(
        plot_bgcolor='#111',
        paper_bgcolor='#111',
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    return fig