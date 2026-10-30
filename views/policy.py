import pandas as pd
import plotly.express as px
import streamlit as st

from model import NAMES, PARTIES
from ui import BLOC_COLORS

st.title("🧭 מרחב המדיניות")
st.caption("המיקומים של המפלגות על ארבעת הצירים (0-10) הם הנחות המודל, ולא תלויים בפרמטרים החופשיים.")
pos = pd.DataFrame([{"מפלגה": n, "ביטחון": PARTIES[n]["sec"], "דת": PARTIES[n]["rel"],
                     "נתניהו": PARTIES[n]["bibi"], "רפורמה משפטית": PARTIES[n]["jud"], "מנדטים": PARTIES[n]["seats"],
                     "גוש": PARTIES[n]["bloc"]} for n in NAMES])
axes = ["ביטחון", "דת", "נתניהו", "רפורמה משפטית"]
ax1, ax2 = st.columns(2)
x_ax = ax1.selectbox("ציר X", axes, index=0)
y_ax = ax2.selectbox("ציר Y", [a for a in axes if a != x_ax])
fig = px.scatter(pos, x=x_ax, y=y_ax, size="מנדטים", color="גוש", text="מפלגה",
                 color_discrete_map=BLOC_COLORS, height=600,
                 range_x=[-0.5, 10.5], range_y=[-0.5, 10.5])
fig.update_traces(textposition="top center")
st.plotly_chart(fig, width="stretch")
