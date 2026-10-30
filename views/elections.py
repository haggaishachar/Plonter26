import pandas as pd
import plotly.express as px
import streamlit as st

from model import NAMES, PARTIES, election_gamble, outside_option, threshold_risk
from ui import BLOC_COLORS, sidebar_params

p = sidebar_params()

st.title("🎲 מי חושש מבחירות חוזרות?")
g = pd.DataFrame([{"מפלגה": n, "גוש": PARTIES[n]["bloc"], "מנדטים": PARTIES[n]["seats"],
                   "ערך ההימור": election_gamble(n, p),
                   "סיכון אחוז החסימה": threshold_risk(n, p),
                   "ערך הבחירות": outside_option(n, p)} for n in NAMES])
fig = px.scatter(g, x="ערך ההימור", y="סיכון אחוז החסימה", size="מנדטים", color="גוש",
                 text="מפלגה", color_discrete_map=BLOC_COLORS, height=600, size_max=45,
                 hover_data={"ערך הבחירות": ":.3f", "ערך ההימור": ":.3f",
                             "סיכון אחוז החסימה": ":.1%"},
                 title="ערך ההימור על הבחירות מול הסיכון להימחק")
fig.add_vline(x=0, line_dash="dash", line_color="gray",
              annotation_text="← חוששת | רוצה בחירות →", annotation_position="top")
fig.update_traces(textposition="top center")
fig.update_yaxes(tickformat=".0%", rangemode="tozero")
st.plotly_chart(fig, width="stretch")
st.caption("ציר X: ערך ההימור על הבחירות לעומת שמירה על המנדטים הנוכחיים. "
           "ציר Y: ההסתברות לרדת מתחת לאחוז החסימה ולקבל 0 מנדטים. "
           "מפלגה מתחת לנקודת הייחוס שלה נמצאת בתחום ההפסדים, ולכן מוכנה להמר כדי לחזור למעמדה. "
           "מפלגה בצד שמאל ולמטה חוששת בגלל שנאת הפסד. מפלגה בצד שמאל ולמעלה חוששת גם להימחק. "
           "ככל שמפלגה חוששת יותר מבחירות, כח המיקוח שלה קטן יותר.")
st.dataframe(g.sort_values("ערך ההימור").drop(columns="גוש").round(3),
             hide_index=True, width="stretch")
