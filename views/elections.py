import pandas as pd
import plotly.express as px
import streamlit as st

from model import ELECTION_FEAR, ELECTION_RISK, NAMES, PARTIES, election_fear, election_gamble, threshold_risk
from ui import BLOC_COLORS, chart, sidebar_params

st.title("🎲 מי חושש מבחירות חדשות?")
p = sidebar_params()

g = pd.DataFrame([{"מפלגה": n, "גוש": PARTIES[n]["bloc"], "מנדטים": PARTIES[n]["seats"],
                   "חשש": election_fear(n, p), "ברירת מחדל": ELECTION_FEAR[n]} for n in NAMES])
fig = px.bar(g.sort_values("חשש"), x="חשש", y="מפלגה", color="גוש", orientation="h",
             color_discrete_map=BLOC_COLORS, height=450, title="החשש של כל מפלגה מבחירות חדשות")
fig.add_vline(x=0, line_dash="dash", line_color="gray")
chart(fig)
st.caption("ככל שמפלגה חוששת יותר מבחירות, כח המיקוח שלה קטן יותר. "
           "מפלגה עם חשש שלילי מעדיפה בחירות על פני כל קואליציה שלא נותנת לה מספיק. "
           "את החשש של כל מפלגה מכוונים בסרגל הצד.")

st.markdown("#### מאיפה באות ברירות המחדל")
st.caption("ברירת המחדל של החשש נגזרת מהגרלה: מספר המנדטים אחרי בחירות מתפלג נורמלית סביב Δ עם סטיית תקן σ, "
           "וכל מפלגה מעריכה את התוצאה יחסית לנקודת הייחוס שלה, עם שנאת הפסד. "
           "מפלגה מתחת לנקודת הייחוס שלה נמצאת בתחום ההפסדים, ולכן מוכנה להמר כדי לחזור למעמדה. "
           "מפלגה שהגיעה לשיא חוששת לאבד אותו, ומפלגה קרובה לאחוז החסימה חוששת גם להימחק. "
           "החשש = עלות כללית של בחירות − ערך ההגרלה, ולליכוד גם פחות פרמיית ממשלת מעבר.")
src = pd.DataFrame([{"מפלגה": n, "גוש": PARTIES[n]["bloc"], "מנדטים": PARTIES[n]["seats"],
                     "Δ": ELECTION_RISK[n][0], "σ": ELECTION_RISK[n][1], "ייחוס": ELECTION_RISK[n][2],
                     "ערך ההימור": election_gamble(n), "סיכון אחוז החסימה": threshold_risk(n),
                     "חשש (ברירת מחדל)": ELECTION_FEAR[n]} for n in NAMES])
fig = px.scatter(src, x="ערך ההימור", y="סיכון אחוז החסימה", size="מנדטים", color="גוש",
                 text="מפלגה", color_discrete_map=BLOC_COLORS, height=500, size_max=45,
                 hover_data={"ערך ההימור": ":.3f", "סיכון אחוז החסימה": ":.1%"},
                 title="ערך ההימור על הבחירות מול הסיכון להימחק")
fig.add_vline(x=0, line_dash="dash", line_color="gray",
              annotation_text="← חוששת | רוצה בחירות →", annotation_position="top")
fig.update_traces(textposition="top center")
fig.update_yaxes(tickformat=".0%", rangemode="tozero")
chart(fig)
st.dataframe(src.sort_values("חשש (ברירת מחדל)").drop(columns="גוש").round(3),
             hide_index=True, width="stretch",
             column_config={"סיכון אחוז החסימה": st.column_config.NumberColumn(format="percent")})
