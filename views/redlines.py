import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from model import NAMES, REDLINE_GROUPS, party_distance, penalty_matrix, redline_breakdown
from ui import chart, sidebar_params

st.title("🚫 קווים אדומים")
p = sidebar_params()

st.markdown("#### 1. מטריצת הקנסות: מי מחרים את מי")
st.caption("שורה = המפלגה שמשלמת את הקנס, עמודה = השותפה שבגללה הוא משולם. "
           "המטריצה לא סימטרית: מפלגה יכולה להחרים שותפה שלא מחרימה אותה. "
           "הערכים מתעדכנים עם סליידרי הקשיחות. "
           "הם לא כוללים את ההנחה לתמיכה מבחוץ, שחלה רק בתוך קואליציה מסוימת. "
           "בתוך קואליציה כל קו נחצה פעם אחת: אם כמה שותפות חוצות אותו, נחשב רק הקנס הגבוה מביניהן. "
           "הקו \"ימין קיצוני בלי הליכוד\" מתבטל כשהליכוד בקואליציה.")
M = penalty_matrix(p)
group_desc = {k: d for k, (d, _) in REDLINE_GROUPS.items()}
hover = [[("<br>".join(f"{group_desc[g]}: {v:.2f}" for g, v in redline_breakdown(i, j, p).items())
           or "אין קו אדום") for j in NAMES] for i in NAMES]
Mz = np.where(M > 0, M, np.nan)
fig = go.Figure(go.Heatmap(z=Mz, x=NAMES, y=NAMES, colorscale="Reds", customdata=hover,
                           text=np.where(M > 0, np.round(M, 2).astype(str), ""),
                           texttemplate="%{text}",
                           hovertemplate="<b>%{y}</b> משלמת על ישיבה עם <b>%{x}</b><br>"
                                         "%{customdata}<extra></extra>",
                           colorbar=dict(title="קנס", orientation="h", y=1.02, yanchor="bottom", thickness=12)))
fig.update_layout(height=560, yaxis=dict(autorange="reversed", title="משלמת את הקנס"),
                  xaxis=dict(title="בגלל השותפה"))
chart(fig)

st.markdown("#### 2. קרובים אבל חסומים")
st.caption("כל נקודה היא זוג מפלגות. ציר X: המרחק האידאולוגי (לפי סליידרי חשיבות הצירים). "
           "ציר Y: הקנס החזק מבין שני הכיוונים, כי די בכך שצד אחד מסרב. "
           "הקווים המקווקווים מחלקים את המרחב לארבעה רבעים.")
idx = {n: k for k, n in enumerate(NAMES)}
rows = []
for a_i, i in enumerate(NAMES):
    for j in NAMES[a_i + 1:]:
        d = party_distance(i, j, p)
        pij, pji = M[idx[i], idx[j]], M[idx[j], idx[i]]
        br = dict(redline_breakdown(i, j, p))
        for g, v in redline_breakdown(j, i, p).items():
            br[g] = br.get(g, 0) + v
        main = group_desc[max(br, key=br.get)] if br else "אין קו אדום"
        rows.append({"זוג": f"{i} – {j}", "מרחק": 0.0 if d is None else d,
                     "קנס": max(pij, pji), "סוג": main,
                     "כיוונים": f"קנס ל{i} על ישיבה עם {j}: {pij:.2f}<br>קנס ל{j} על ישיבה עם {i}: {pji:.2f}"})
pairs = pd.DataFrame(rows)
x_cut = float(pairs["מרחק"].median())
y_cut = 0.3
fig = px.scatter(pairs, x="מרחק", y="קנס", color="סוג", height=600,
                 custom_data=["זוג", "כיוונים"])
fig.update_traces(marker=dict(size=11, opacity=0.8),
                  hovertemplate="<b>%{customdata[0]}</b><br>מרחק: %{x:.2f}<br>"
                                "%{customdata[1]}<extra></extra>")
fig.add_vline(x=x_cut, line_dash="dash", line_color="gray")
fig.add_hline(y=y_cut, line_dash="dash", line_color="gray")
ymax = max(float(pairs["קנס"].max()), y_cut) * 1.1
xmax = float(pairs["מרחק"].max()) * 1.05
for x, y, t in [(0, ymax, "קרובים אבל חסומים"), (xmax, ymax, "רחוקים וחסומים"),
                (0, -0.05 * ymax, "שותפות טבעיות"), (xmax, -0.05 * ymax, "רחוקים בלי חרם")]:
    fig.add_annotation(x=x, y=y, text=f"<b>{t}</b>", showarrow=False,
                       xanchor="left" if x == 0 else "right", font=dict(color="gray"))
fig.update_layout(legend=dict(title="קו אדום עיקרי"))
chart(fig)
