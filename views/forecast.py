import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from model import (ARAB, NAMES, PARTIES, REDLINE_GROUPS, _members_split, evaluate, formateur_outcome,
                   group_penalties, label, outside_option, rotation_pair)
from ui import bloc_header, chart, near_table_html, sidebar_params

bloc_header()
p = sidebar_params()

results = evaluate(p, min_only=p.min_only)


def gap_lines(r):
    """הקווים האדומים שהחוסמות חוצות, מהכבד לקל, כל קו פעם אחת בלבד."""
    pens, bare = {}, False
    for b in r.blockers:
        g = group_penalties(b, r.members, p)
        bare |= not g
        for key, pen in g.items():
            pens[key] = max(pens.get(key, 0.0), pen)
    lines = [REDLINE_GROUPS[key][0] for key in sorted(pens, key=pens.get, reverse=True)]
    if bare:
        lines.append("בלי קו אדום: פשוט מקבלת מעט מדי")
    return lines


def rot_text(c):
    rot = rotation_pair(c, p)
    return f"{rot[0]} ← {rot[1]}" if rot else ""


feasible = [r for r in results if r.feasible]

# הנשיא מטיל את המנדט לפי גודל: קודם המפלגה הגדולה, ואם נכשלה, הבאה בתור.
order = sorted([n for n in NAMES if n not in ARAB], key=lambda x: -PARTIES[x]["seats"])
f, best = formateur_outcome(p, order, results)
if best is None:
    st.error("### 🔒 פלונטר: אין קואליציה ישימה, והמדינה הולכת לבחירות חוזרות\n"
             f"אף אחת מ-{len(results)} הקואליציות שנבדקו אינה ישימה: "
             "אף מרכיב לא מצליח להרכיב קואליציה שבה כל השותפות מעדיפות להצטרף על פני בחירות.")
    near = sorted(results, key=lambda r: -min(r.surplus.values()))[:5]
    st.markdown("**הקואליציות שהכי קרובות להיות ישימות** (חסם = המפלגה שמעדיפה בחירות):")
    st.markdown(near_table_html([{
        "gov": _members_split(r.members, p)[0], "ext": _members_split(r.members, p)[1],
        "seats": r.seats, "rotation": rot_text(r.members), "blockers": r.blockers,
        "gap": -min(r.surplus.values()), "lines": gap_lines(r)} for r in near]), unsafe_allow_html=True)
else:
    msg = (f"### ✅ {f} מרכיב/ה: {label(best.members, p)}  ({best.seats} מנדטים)\n"
           f"🤝 " + ("קואליציה ישימה אחת" if len(feasible) == 1 else f"{len(feasible)} קואליציות ישימות")
           + f" מתוך {len(results)} שנבדקו.")
    rot = rotation_pair(best.members, p)
    if rot:
        msg += (f"\n\n🔁 **צפויה רוטציה בראשות הממשלה:** {rot[0]} ({PARTIES[rot[0]]['seats']} מנדטים) "
                f"ראשונה, ואחריה {rot[1]} ({PARTIES[rot[1]]['seats']} מנדטים). "
                f"כל אחת מקבלת מחצית מפרמיית ראשות הממשלה.")
    st.success(msg)
    df = pd.DataFrame({"מפלגה": list(best.members),
                       "תועלת": [best.utilities[m] for m in best.members],
                       "ערך בחירות חוזרות": [outside_option(m, p) for m in best.members]})
    fig = go.Figure([go.Bar(name="תועלת מהקואליציה", x=df["מפלגה"], y=df["תועלת"]),
                     go.Bar(name="ערך בחירות חוזרות", x=df["מפלגה"], y=df["ערך בחירות חוזרות"])])
    fig.update_layout(barmode="group", height=350, title="מדוע כל שותפה מסכימה")
    chart(fig)

if feasible:
    st.markdown("#### כל הקואליציות הישימות (מדורגות לפי פתרון הבארגיינינג של נאש)")
    st.dataframe(pd.DataFrame([{
        "קואליציה": label(r.members, p), "מנדטים": r.seats, "רוטציה": rot_text(r.members),
        "מכפלת נאש (log ממוצע)": round(r.nash, 3),
        "העודף המינימלי": round(min(r.surplus.values()), 3)}
        for r in sorted(feasible, key=lambda r: -r.nash)]), hide_index=True, width="stretch")
