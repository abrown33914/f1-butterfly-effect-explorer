# The F1 Butterfly Effect Explorer

> *Rewrite any F1 race. See how one decision changed everything.*

This program lets you scrub through any race since 2018, toggle a pit stop or strategy call on or off, and watch the entire finishing order reshape itself in real time based on real telemetry data.

## Features
- 🏎️ Animated lap-by-lap race replay
- 🔀 Counterfactual "what if" strategy engine
- 📊 Regret score per team — who cost themselves the most
- 📸 Shareable result card

## Setup
```bash
git clone https://github.com/abrown33914/f1-butterfly-effect-explorer
cd f1-butterfly-effect-explorer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Data
Powered by [FastF1](https://theoehrly.github.io/Fast-F1/) — real F1 telemetry and timing data.

## Stack
- Python, FastF1, Streamlit, Plotly, Pandas