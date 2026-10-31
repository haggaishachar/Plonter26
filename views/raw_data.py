import pandas as pd
import streamlit as st

from model import NAMES, PARTIES, REDLINE_GROUPS, election_fear, outside_option, party_distance, penalty_matrix, \
    redline_breakdown
from ui import K, cached_power, sidebar_params

st.title("🗂️ מידע גולמי")
p = sidebar_params()

st.markdown("#### 1. המפלגות")
st.caption("נתוני הקלט של כל מפלגה: מנדטים, גוש, מיקום על ארבעת הצירים (0-10) והחשש מבחירות חדשות "
           "(כולל עריכות בסרגל הצד), ולצידם מדדי הכוח וערך הבחירות המחושבים.")
banz, ss, _ = cached_power()
raw = pd.DataFrame([{"מפלגה": n, "גוש": PARTIES[n]["bloc"], "מנדטים": PARTIES[n]["seats"],
                     "ביטחון": PARTIES[n]["sec"], "דת ומדינה": PARTIES[n]["rel"],
                     "יחס לנתניהו": PARTIES[n]["bibi"], "רפורמה משפטית": PARTIES[n]["jud"],
                     "חשש מבחירות": election_fear(n, p), "Banzhaf": banz[n], "Shapley-Shubik": ss[n],
                     "ערך הבחירות": outside_option(n, p)} for n in NAMES])
st.dataframe(raw, hide_index=True, width="stretch", height=(len(raw) + 1) * 35 + 3,
             column_config={c: st.column_config.NumberColumn(format="%.3f")
                            for c in ("Banzhaf", "Shapley-Shubik", "חשש מבחירות", "ערך הבחירות")})

st.markdown("#### 2. הקשרים בין המפלגות")
st.caption("כל שורה היא זוג מפלגות. מרחק = המרחק האידאולוגי המשוקלל (לפי חשיבות הצירים). "
           "קנס א←ב = מה שמפלגה א' משלמת על ישיבה עם ב'. הקנסות לפני ההנחה לתמיכה מבחוץ.")
M = penalty_matrix(p)
idx = {n: k for k, n in enumerate(NAMES)}
group_desc = {k: d for k, (d, _) in REDLINE_GROUPS.items()}
rel_rows = []
for a_i, i in enumerate(NAMES):
    for j in NAMES[a_i + 1:]:
        groups = [g for g in REDLINE_GROUPS
                  if g in redline_breakdown(i, j, p) or g in redline_breakdown(j, i, p)]
        rel_rows.append({"מפלגה א'": i, "מפלגה ב'": j,
                         "אותו גוש": PARTIES[i]["bloc"] == PARTIES[j]["bloc"],
                         "מנדטים יחד": PARTIES[i]["seats"] + PARTIES[j]["seats"],
                         "מרחק": party_distance(i, j, p),
                         "קנס א←ב": M[idx[i], idx[j]], "קנס ב←א": M[idx[j], idx[i]],
                         "קווים אדומים": " | ".join(group_desc[g] for g in groups)})
rel = pd.DataFrame(rel_rows)
focus = st.multiselect("סינון לפי מפלגה", NAMES, key=K("raw_focus"))
if focus:
    rel = rel[rel["מפלגה א'"].isin(focus) | rel["מפלגה ב'"].isin(focus)]
st.dataframe(rel, hide_index=True, width="stretch",
             column_config={c: st.column_config.NumberColumn(format="%.2f")
                            for c in ("מרחק", "קנס א←ב", "קנס ב←א")})

st.markdown("#### 3. מטריצת המרחקים")
dist = pd.DataFrame([[0.0 if i == j else party_distance(i, j, p) for j in NAMES] for i in NAMES],
                    index=NAMES, columns=NAMES)
st.dataframe(dist.round(2), width="stretch")

st.markdown("#### 4. מטריצת הקנסות")
st.caption("שורה = המפלגה שמשלמת, עמודה = השותפה שבגללה.")
st.dataframe(pd.DataFrame(M, index=NAMES, columns=NAMES).round(2), width="stretch")
