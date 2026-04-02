import plotly.graph_objects as go
import pandas as pd
from assets.team_colors import DRIVER_COLORS

def build_position_timeline(race_state: pd.DataFrame) -> go.Figure:
    """
    Animated lap by lap position chart for all drivers.
    Each driver is a colored line — positions flip as the race unfolds.
    """
    fig = go.Figure()

    if race_state is None or race_state.empty or 'LapNumber' not in race_state.columns:
        fig.add_annotation(
            text='No position data available for this session.',
            x=0.5,
            y=0.5,
            xref='paper',
            yref='paper',
            showarrow=False,
            font=dict(color='white', size=18, family='monospace')
        )
        fig.update_layout(
            title='🏎️ Race Position Timeline',
            plot_bgcolor='#0f0f0f',
            paper_bgcolor='#0f0f0f',
            font=dict(color='white', family='monospace')
        )
        return fig

    drivers = race_state['Driver'].unique()

    for driver in drivers:
        driver_data = race_state[race_state['Driver'] == driver].sort_values('LapNumber')
        color = DRIVER_COLORS.get(driver, '#FFFFFF')

        fig.add_trace(go.Scatter(
            x=driver_data['LapNumber'],
            y=driver_data['Position'],
            mode='lines+markers',
            name=driver,
            line=dict(color=color, width=2),
            marker=dict(size=4),
            hovertemplate=(
                f"<b>{driver}</b><br>"
                "Lap %{x}<br>"
                "Position: %{y}<br>"
                "<extra></extra>"
            )
        ))

    total_laps = int(pd.to_numeric(race_state['LapNumber'], errors='coerce').max())

    # Build animation frames
    frames = []
    for lap in range(1, total_laps + 1):
        frame_data = []
        for driver in drivers:
            d = race_state[
                (race_state['Driver'] == driver) &
                (race_state['LapNumber'] <= lap)
            ].sort_values('LapNumber')
            color = DRIVER_COLORS.get(driver, '#FFFFFF')
            frame_data.append(go.Scatter(
                x=d['LapNumber'],
                y=d['Position'],
                mode='lines+markers',
                line=dict(color=color, width=2),
                marker=dict(size=4),
            ))
        frames.append(go.Frame(data=frame_data, name=str(lap)))

    fig.frames = frames

    fig.update_layout(
        title="🏎️ Race Position Timeline",
        xaxis_title="Lap",
        yaxis_title="Position",
        yaxis=dict(autorange='reversed', tickmode='linear', tick0=1, dtick=1),
        plot_bgcolor='#0f0f0f',
        paper_bgcolor='#0f0f0f',
        font=dict(color='white', family='monospace'),
        legend=dict(
            bgcolor='#1a1a1a',
            bordercolor='#333',
            borderwidth=1,
            font=dict(size=10)
        ),
        updatemenus=[dict(
            type='buttons',
            showactive=False,
            y=1.15,
            x=0.5,
            xanchor='center',
            buttons=[
                dict(
                    label='▶ Play',
                    method='animate',
                    args=[None, dict(
                        frame=dict(duration=120, redraw=True),
                        fromcurrent=True,
                        transition=dict(duration=80)
                    )]
                ),
                dict(
                    label='⏸ Pause',
                    method='animate',
                    args=[[None], dict(
                        frame=dict(duration=0, redraw=False),
                        mode='immediate',
                        transition=dict(duration=0)
                    )]
                )
            ]
        )],
        sliders=[dict(
            steps=[
                dict(
                    method='animate',
                    args=[[str(lap)], dict(
                        mode='immediate',
                        frame=dict(duration=120, redraw=True),
                        transition=dict(duration=80)
                    )],
                    label=str(lap)
                )
                for lap in range(1, total_laps + 1)
            ],
            x=0,
            y=0,
            len=1.0,
            currentvalue=dict(
                prefix='Lap: ',
                font=dict(color='white', size=14),
                visible=True,
                xanchor='center'
            ),
            bgcolor='#1a1a1a',
            bordercolor='#444',
            font=dict(color='white')
        )]
    )

    return fig