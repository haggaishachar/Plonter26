import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from model import (ARAB, NAMES, PARTIES, QUOTA, REDLINE_GROUPS, Params,
                   default_hardness, evaluate, formateur_outcome, label, outside_option,
                   party_distance, penalty_matrix, power_indices, redline_breakdown,
                   rotation_pair, utility)

st.set_page_config(page_title="הפלונטר של הכנסת ה-26", layout="wide")
st.markdown("""<style>
html, body, [class*="css"], .stMarkdown, .stSlider, .stTabs, section[data-testid="stSidebar"] {direction: rtl; text-align: right;}
.stSlider > div {direction: ltr;}
[data-testid="stHeading"], h1, h2, h3, h4 {direction: rtl; text-align: right;}
</style>""", unsafe_allow_html=True)

BLOC_COLORS = {"נתניהו": "#2b6cb0", "אופוזיציה": "#dd6b20", "ערביות": "#2f855a"}

# ---------------- סרגל צד: פרמטרים חופשיים ----------------
sb = st.sidebar
sb.header("⚙️ פרמטרים חופשיים")
st.session_state.setdefault("reset_ver", 0)


def K(name):
    """מפתח ווידג'ט עם מספר גרסה. הגדלת הגרסה יוצרת ווידג'טים חדשים בערכי ברירת המחדל."""
    return f"{name}_v{st.session_state.reset_ver}"


def reset_params():
    st.session_state.reset_ver += 1


sb.button("🔄 אתחול לערכי ברירת המחדל", on_click=reset_params, width="stretch")
sb.subheader("העדפות כלליות")
alpha = sb.slider("α: משקל ג'ובים מול אידאולוגיה", 0.0, 1.0, 0.5, 0.05, key=K("alpha"),
                  help="0 = מפלגות אכפת להן רק ממדיניות, 1 = רק מתיקים ותקציבים")
pm_premium = sb.slider("פרמיית ראשות הממשלה", 0.0, 1.0, 0.4, 0.05, key=K("pm"))
rotation = sb.checkbox("רוטציה אפשרית בין שתי הגדולות", True, key=K("rot"))
transfer_eff = sb.slider("יעילות העברות בין שותפות", 0.0, 1.0, 0.0, 0.05, key=K("teff"),
                         help="האם המרוויחות מקואליציה יכולות לפצות שותפה מהססת בתיקים, תקציבים או חקיקה. "
                              "0 = אין העברות (כל שותפה צריכה להרוויח בעצמה). "
                              "1 = כל יחידה שמשולמת מגיעה במלואה. 0.5 = חצי הולך לאיבוד בדרך.")
sb.subheader("חשיבות הצירים")
w_sec = sb.slider("ביטחון / מדיני", 0.0, 3.0, 1.0, 0.1, key=K("wsec"))
w_rel = sb.slider("דת ומדינה (גיוס, שבת)", 0.0, 3.0, 1.0, 0.1, key=K("wrel"))
w_bibi = sb.slider("יחס אישי לנתניהו", 0.0, 3.0, 1.0, 0.1, key=K("wbibi"))
w_jud = sb.slider("רפורמה משפטית", 0.0, 3.0, 1.0, 0.1, key=K("wjud"))

sb.subheader("נקודת אי-הסכמה: בחירות חוזרות")
base_outside = sb.slider("ערך בסיס של בחירות חוזרות", 0.0, 1.0, 0.55, 0.05, key=K("base"))
election_cost = sb.slider("עלות / עייפות מבחירות חוזרות", 0.0, 1.0, 0.3, 0.05, key=K("cost"),
                          help="ככל שגבוה יותר, מפלגות מוכנות להתפשר יותר")
caretaker = sb.slider("פרמיית ממשלת מעבר לליכוד", 0.0, 1.0, 0.15, 0.05, key=K("caretaker"),
                      help="כל עוד אין ממשלה, נתניהו ממשיך לכהן כראש ממשלת מעבר. "
                           "הפרמיה מתווספת לערך הבחירות החוזרות של הליכוד בלבד, ולכן הפלונטר נוח לו יותר.")
with sb.expander("מומנטום אלקטורלי לפי מפלגה"):
    st.caption("חיובי = המפלגה צפויה להתחזק בבחירות חוזרות, ולכן תהיה קשוחה יותר")
    momentum = {n: st.slider(n, -0.3, 0.3, 0.0, 0.05, key=K(f"m_{n}")) for n in NAMES}

sb.subheader("קווים אדומים (קשיחות)")
hard_def = default_hardness()
hardness = {k: sb.slider(desc, 0.0, 3.0, hard_def[k], 0.1, key=K(f"h_{k}"))
            for k, (desc, _) in REDLINE_GROUPS.items()}

sb.subheader("המפלגות הערביות")
arab_external = sb.checkbox("תמיכה מבחוץ, בלי תיקים (מודל 'בנט-לפיד' / רע\"מ)", True, key=K("ext"))
external_discount = sb.slider("עד כמה תמיכה מבחוץ מרככת את החרם", 0.0, 1.0, 0.5, 0.05, key=K("disc"))
arab_budget = sb.slider("ערך ההישגים התקציביים לתומכת חיצונית", 0.0, 1.0, 0.35, 0.05, key=K("budget"))

p = Params(alpha=alpha, w_sec=w_sec, w_rel=w_rel, w_bibi=w_bibi, w_jud=w_jud, pm_premium=pm_premium,
           rotation=rotation, election_cost=election_cost, base_outside=base_outside,
           momentum=momentum, hardness=hardness, arab_external=arab_external,
           external_discount=external_discount, arab_budget=arab_budget,
           transfer_eff=transfer_eff, caretaker=caretaker)

min_only = sb.checkbox("רק קואליציות מינימליות (בלי מפלגה מיותרת)", True, key=K("minonly"))


@st.cache_data
def cached_power():
    return power_indices()


results = evaluate(p, min_only=min_only)



def rot_text(c):
    rot = rotation_pair(c, p)
    return f"{rot[0]} ← {rot[1]}" if rot else ""

feasible = [r for r in results if r.feasible]

# ---------------- כותרת ----------------
st.title("🧩 הפלונטר של הכנסת ה-26: מודל של תורת המשחקים")
st.caption("תוצאות הבחירות (27.10.2026): גוש נתניהו 53, גוש האופוזיציה 48, המפלגות הערביות 19. "
           "המיקומים האידאולוגיים ומשקלי הקווים האדומים הם הנחות מודל שאפשר לשנות.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("גוש נתניהו", sum(PARTIES[n]["seats"] for n in NAMES if PARTIES[n]["bloc"] == "נתניהו"))
c2.metric("גוש האופוזיציה", sum(PARTIES[n]["seats"] for n in NAMES if PARTIES[n]["bloc"] == "אופוזיציה"))
c3.metric("המפלגות הערביות", sum(PARTIES[n]["seats"] for n in ARAB))
c4.metric("קואליציות ישימות", f"{len(feasible)} / {len(results)}")

tabs = st.tabs(["🎯 תחזית", "🧭 מרחב המדיניות", "🚫 קווים אדומים", "⚖️ כח המיקוח",
                "📖 המודל"])

# ---------------- תחזית ----------------
with tabs[0]:
    default_order = sorted([n for n in NAMES if n not in ARAB], key=lambda x: -PARTIES[x]["seats"])
    order = st.multiselect("סדר המרכיבים (הנשיא מטיל את המנדט לפי הסדר)", default_order,
                           default=default_order[:2], key=K("order"))
    f, best = formateur_outcome(p, order, results)
    if best is None:
        st.error("### 🔒 פלונטר: אין קואליציה ישימה, והמדינה הולכת לבחירות חוזרות\n"
                 "אף מרכיב לא מצליח להרכיב קואליציה שבה כל השותפות מעדיפות להצטרף על פני בחירות.")
        near = sorted(results, key=lambda r: r.gap)[:5]
        st.markdown("**הקואליציות שהכי קרובות להיות ישימות** (חוסמות = מפלגות שמעדיפות בחירות):")
        st.dataframe(pd.DataFrame([{
            "קואליציה": label(r.members, p), "מנדטים": r.seats, "רוטציה": rot_text(r.members),
            "חוסמות": ", ".join(r.blockers),
            "סך הגירעון של החוסמות": round(sum(-v for v in r.surplus.values() if v < 0), 3),
            "סך הרווח של השאר": round(sum(v for v in r.surplus.values() if v > 0), 3),
            "הפער שנותר אחרי העברות": round(r.gap, 3)} for r in near]),
            hide_index=True, width="stretch")
        st.caption("אם סך הרווח של השאר גדול מהגירעון, הקואליציה יכולה לקום כשמאפשרים העברות. "
                   "נסה להזיז את הסליידר 'יעילות העברות בין שותפות'.")
    else:
        st.success(f"### ✅ {f} מרכיב/ה: {label(best.members, p)}  ({best.seats} מנדטים)")
        rot = rotation_pair(best.members, p)
        if rot:
            st.info(f"🔁 **צפויה רוטציה בראשות הממשלה:** {rot[0]} ({PARTIES[rot[0]]['seats']} מנדטים) "
                    f"ראשונה, ואחריה {rot[1]} ({PARTIES[rot[1]]['seats']} מנדטים). "
                    f"כל אחת מקבלת מחצית מפרמיית ראשות הממשלה.")
        paying = {m: -t for m, t in best.transfers.items() if t < -1e-9}
        getting = {m: t for m, t in best.transfers.items() if t > 1e-9}
        if getting:
            st.warning("💸 **הקואליציה קמה רק בזכות העברות:** "
                       + ", ".join(f"{m} מקבלת {v:.2f}" for m, v in getting.items())
                       + ". משלמות: " + ", ".join(f"{m} ({v:.2f})" for m, v in paying.items())
                       + ". בפועל: תיקים נוספים, תקציבים או חקיקה.")
        mem = list(best.members)
        fig = go.Figure([
            go.Bar(name="עודף לפני העברות", x=mem, y=[best.surplus[m] for m in mem]),
            go.Bar(name="עודף אחרי העברות", x=mem, y=[best.final_surplus[m] for m in mem])])
        fig.add_hline(y=0, line_dash="dash", annotation_text="ערך בחירות חוזרות")
        fig.update_layout(barmode="group", height=350,
                          title="מדוע כל שותפה מסכימה (עודף התועלת מעל בחירות חוזרות)")
        st.plotly_chart(fig, width="stretch")

    if feasible:
        st.markdown("#### כל הקואליציות הישימות (מדורגות לפי פתרון הבארגיינינג של נאש)")
        st.dataframe(pd.DataFrame([{
            "קואליציה": label(r.members, p), "מנדטים": r.seats, "רוטציה": rot_text(r.members),
            "סך ההעברות": round(sum(t for t in r.transfers.values() if t > 0), 3),
            "מכפלת נאש (log ממוצע)": round(r.nash, 3),
            "העודף המינימלי": round(min(r.final_surplus.values()), 3)}
            for r in sorted(feasible, key=lambda r: -r.nash)]), hide_index=True, width="stretch")

# ---------------- מרחב המדיניות ----------------
with tabs[1]:
    st.markdown("#### מרחב המדיניות (הנחות)")
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

# ---------------- כח המיקוח ----------------
with tabs[3]:
    banz, ss, swings = cached_power()
    df = pd.DataFrame({"מפלגה": NAMES, "מנדטים": [PARTIES[n]["seats"] for n in NAMES],
                       "Banzhaf": [banz[n] for n in NAMES], "Shapley-Shubik": [ss[n] for n in NAMES]})
    df["חלק מהמנדטים"] = df["מנדטים"] / 120
    m = df.melt(id_vars=["מפלגה"], value_vars=["חלק מהמנדטים", "Banzhaf", "Shapley-Shubik"])
    fig = px.bar(m, x="מפלגה", y="value", color="variable", barmode="group", height=500,
                 title="כח מיקוח מול גודל (משחק הצבעה משוקלל [61; מנדטים])",
                 labels={"value": "חלק", "variable": "מדד"})
    st.plotly_chart(fig, width="stretch")
    df["Banzhaf ÷ חלק מהמנדטים"] = df["Banzhaf"] / df["חלק מהמנדטים"]
    st.dataframe(df[["מפלגה", "מנדטים", "חלק מהמנדטים", "Banzhaf", "Shapley-Shubik", "Banzhaf ÷ חלק מהמנדטים"]]
                 .sort_values("Banzhaf", ascending=False).round(3), hide_index=True, width="stretch")

    st.markdown("### מה כל מדד אומר")
    n_sub = 2 ** (len(NAMES) - 1)
    tot_sw = sum(swings.values())
    lik, dem, shas = "הליכוד", "הדמוקרטים", 'ש"ס'

    st.markdown(f"""
#### 1. חלק מהמנדטים
המדד הנאיבי: מנדטים חלקי 120. לדוגמה, ל{lik} יש {PARTIES[lik]['seats']} מנדטים, כלומר
{PARTIES[lik]['seats'] / 120:.1%}. זו נקודת ההשוואה של שני המדדים האחרים. אם כח המיקוח היה
פרופורציוני לגודל, שלושת העמודים בגרף היו שווים.

#### 2. מדד Banzhaf
**השאלה:** בכמה מהקואליציות האפשריות המפלגה היא **לשון המאזניים**, כלומר בלעדיה אין רוב ואיתה יש?

**החישוב:** לכל מפלגה עוברים על כל {n_sub:,} הצירופים של עשר המפלגות האחרות. סופרים את הצירופים
שיש להם פחות מ-61 מנדטים, אבל יחד עם המפלגה מגיעים ל-61 ומעלה. אלה **נקודות ההכרעה** (swings).
מחלקים את מספר נקודות ההכרעה של המפלגה בסך נקודות ההכרעה של כל המפלגות ({tot_sw:,}).
כך הסכום של כל המפלגות הוא 1.

**לדוגמה:** {lik} מכריע ב-{swings[lik]:,} צירופים, {dem} ב-{swings[dem]:,} ו{shas} ב-{swings[shas]:,}.
לכן Banzhaf של {lik} הוא {swings[lik]:,} ÷ {tot_sw:,} = {banz[lik]:.3f}.

**ההנחה:** כל הקואליציות סבירות באותה מידה.

#### 3. מדד Shapley-Shubik
**השאלה:** אם הקואליציה נבנית מפלגה אחרי מפלגה בסדר אקראי, באיזה אחוז מהסדרים המפלגה היא
**זו שמצטרפת ומשלימה את ה-61**?

**החישוב:** עוברים על כל הסדרים האפשריים של 11 המפלגות (11! סדרים) ובודקים בכל סדר מי המפלגה
שהביאה את הקואליציה ל-61. החלק מתוך הסדרים שבהם זו המפלגה הוא המדד. גם כאן הסכום של כל המפלגות הוא 1.

**לדוגמה:** {lik} משלים את הרוב ב-{ss[lik]:.1%} מהסדרים, {dem} ב-{ss[dem]:.1%} ו{shas} ב-{ss[shas]:.1%}.

**ההבדל מ-Banzhaf:** כאן נותנים משקל גדול יותר לקואליציות קטנות מאוד ולגדולות מאוד, כי יש יותר
סדרים שמגיעים אליהן. לכן הוא נוטה לתת קצת יותר כח למפלגות הגדולות.

#### 4. היחס Banzhaf ÷ חלק מהמנדטים
**השאלה:** האם למפלגה יש יותר או פחות כח ממה שהגודל שלה מרמז?
- **מעל 1:** כח מיקוח גדול מהגודל. לדוגמה, {dem} ({banz[dem] / (PARTIES[dem]['seats'] / 120):.2f}):
  יש הרבה צירופים של 53 עד 60 מנדטים, ו-8 המנדטים שלהם משלימים כל אחד מהם לרוב.
  מפלגה עם 7 מנדטים לא מצליחה להשלים צירוף של 53.
- **מתחת ל-1:** כח קטן מהגודל. לדוגמה, {shas} ({banz[shas] / (PARTIES[shas]['seats'] / 120):.2f}).

#### מה המדדים לא לוקחים בחשבון
שני המדדים מניחים שכל מפלגה מוכנה לשבת עם כל מפלגה. הם מתעלמים מקווים אדומים, ממדיניות ומג'ובים,
ולכן הם מראים רק את **הכח התאורטי** שנובע מחלוקת המנדטים. לכן הם לא משתנים כשמזיזים את הסליידרים.
בפועל, החרמות מוחקים הרבה מהקואליציות שהמדדים סופרים, וזה מה שמכניס את המשחק לפלונטר.
""")

# ---------------- קווים אדומים ----------------
with tabs[2]:
    st.markdown("#### 1. מטריצת הקנסות: מי מחרים את מי")
    st.caption("שורה = המפלגה שמשלמת את הקנס, עמודה = השותפה שבגללה הוא משולם. "
               "המטריצה לא סימטרית: מפלגה יכולה להחרים שותפה שלא מחרימה אותה. "
               "הערכים מתעדכנים עם סליידרי הקשיחות. "
               "הם לא כוללים את ההנחה לתמיכה מבחוץ, שחלה רק בתוך קואליציה מסוימת.")
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
                               colorbar=dict(title="קנס")))
    fig.update_layout(height=560, yaxis=dict(autorange="reversed", title="משלמת את הקנס"),
                      xaxis=dict(title="בגלל השותפה"))
    st.plotly_chart(fig, width="stretch")

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
    st.plotly_chart(fig, width="stretch")

# ---------------- הסבר ----------------
with tabs[4]:
    st.markdown(r"""
### איך ממדלים את הפלונטר

**1. משחק הצבעה משוקלל.** $[q=61;\ w_1,\dots,w_{11}]$. קואליציה $C$ מנצחת אם $\sum_{i\in C} w_i \ge 61$.
מדדי Banzhaf ו-Shapley-Shubik מראים שכוח מיקוח אינו פרופורציוני למנדטים.

**2. תועלת של מפלגה $i$ מקואליציה $C$:**
$$U_i(C) = \alpha\cdot\underbrace{\tfrac{w_i}{w(C)}}_{\text{גמסון: תיקים}} + (1-\alpha)\cdot\underbrace{\Big(1-\tfrac{d_i(\bar x_C)}{10}\Big)}_{\text{מדיניות}} + \text{פרמיית רה"מ} - \sum_{j\in C} \text{קו אדום}_{ij}$$
- $\bar x_C$ הוא מרכז הכובד (משוקלל במנדטים) של הקואליציה במרחב ארבעה צירים: ביטחון, דת ומדינה, יחס אישי לנתניהו, רפורמה משפטית.
- $d_i$ הוא מרחק אוקלידי משוקלל לפי חשיבות הצירים.
- קווים אדומים הם קנסות על זוגות מפלגות. סרגלי הקשיחות מכפילים אותם.

**3. נקודת אי-הסכמה.** $E_i = \text{בסיס} + \text{מומנטום}_i - \text{עלות בחירות}$.
לליכוד מתווספת **פרמיית ממשלת מעבר**: כל עוד אין ממשלה, נתניהו ממשיך לכהן, ולכן הפלונטר נוח לו יותר.

**4. העברות (תועלת ניתנת להעברה חלקית).** העודף של כל שותפה הוא $s_i = U_i(C) - E_i$.
מפלגות עם $s_i>0$ יכולות לפצות מפלגות עם $s_i<0$ בתיקים, תקציבים או חקיקה, ביעילות $e$.
הקואליציה **ישימה** אם $e\cdot\sum_{s_i>0} s_i \ge \sum_{s_i<0} |s_i|$.
כש-$e=0$ זה חוזר לתנאי הרגיל: כל שותפה צריכה להעדיף את הקואליציה על פני בחירות בעצמה.
המשלמות משלמות באופן יחסי לרווח שלהן.

**5. מנגנון הרכבה (Baron-Ferejohn מפושט).** מרכיב לפי הסדר שבחר הנשיא בוחר מבין הקואליציות הישימות
את הטובה לו אחרי העברות. אם אף מרכיב לא מצליח, זה **הפלונטר**: שיווי המשקל הוא בחירות חוזרות.

**6. פתרון נאש.** בין הקואליציות הישימות, הדירוג לפי $\frac1{|C|}\sum \log(s_i)$ אחרי העברות.

**מגבלות:** המיקומים והקנסות הם הנחות. המודל סטטי, והוא לא כולל עריקות, פיצולי מפלגות
או משחק חוזר בין סבבי בחירות.
""")
