from dataclasses import replace

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from model import (ARAB, NAMES, PARTIES, evaluate, formateur_outcome, label, outside_option,
                   rotation_pair, seats, utility, chicken_coalitions, chicken_game,
                   correlated_equilibrium, SWERVE, STRAIGHT)
from ui import K, sidebar_params

p = sidebar_params()

min_only = st.sidebar.checkbox("רק קואליציות מינימליות (בלי מפלגה מיותרת)", True, key=K("minonly"))

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

tabs = st.tabs(["🎯 תחזית", "🐔 צ'יקן"])

# ---------------- תחזית ----------------
with tabs[0]:
    default_order = sorted([n for n in NAMES if n not in ARAB], key=lambda x: -PARTIES[x]["seats"])
    order = st.multiselect("סדר המרכיבים (הנשיא מטיל את המנדט לפי הסדר)", default_order,
                           default=default_order[:2], key=K("order"))
    f, best = formateur_outcome(p, order, results)
    if best is None:
        st.error("### 🔒 פלונטר: אין קואליציה ישימה, והמדינה הולכת לבחירות חוזרות\n"
                 "אף מרכיב לא מצליח להרכיב קואליציה שבה כל השותפות מעדיפות להצטרף על פני בחירות.")
        near = sorted(results, key=lambda r: -min(r.surplus.values()))[:5]
        st.markdown("**הקואליציות שהכי קרובות להיות ישימות** (חסם = המפלגה שמעדיפה בחירות):")
        st.dataframe(pd.DataFrame([{
            "קואליציה": label(r.members, p), "מנדטים": r.seats, "רוטציה": rot_text(r.members),
            "חוסמות": ", ".join(r.blockers),
            "הפער שצריך לסגור": round(-min(r.surplus.values()), 3)} for r in near]),
            hide_index=True, width="stretch")
    else:
        st.success(f"### ✅ {f} מרכיב/ה: {label(best.members, p)}  ({best.seats} מנדטים)")
        rot = rotation_pair(best.members, p)
        if rot:
            st.info(f"🔁 **צפויה רוטציה בראשות הממשלה:** {rot[0]} ({PARTIES[rot[0]]['seats']} מנדטים) "
                    f"ראשונה, ואחריה {rot[1]} ({PARTIES[rot[1]]['seats']} מנדטים). "
                    f"כל אחת מקבלת מחצית מפרמיית ראשות הממשלה.")
        df = pd.DataFrame({"מפלגה": list(best.members),
                           "תועלת": [best.utilities[m] for m in best.members],
                           "ערך בחירות חוזרות": [outside_option(m, p) for m in best.members]})
        fig = go.Figure([go.Bar(name="תועלת מהקואליציה", x=df["מפלגה"], y=df["תועלת"]),
                         go.Bar(name="ערך בחירות חוזרות", x=df["מפלגה"], y=df["ערך בחירות חוזרות"])])
        fig.update_layout(barmode="group", height=350, title="מדוע כל שותפה מסכימה")
        st.plotly_chart(fig, width="stretch")

    if feasible:
        st.markdown("#### כל הקואליציות הישימות (מדורגות לפי פתרון הבארגיינינג של נאש)")
        st.dataframe(pd.DataFrame([{
            "קואליציה": label(r.members, p), "מנדטים": r.seats, "רוטציה": rot_text(r.members),
            "מכפלת נאש (log ממוצע)": round(r.nash, 3),
            "העודף המינימלי": round(min(r.surplus.values()), 3)}
            for r in sorted(feasible, key=lambda r: -r.nash)]), hide_index=True, width="stretch")

# ---------------- צ'יקן ----------------
with tabs[1]:
    st.markdown("#### משחק הצ'יקן: מי ימצמץ ראשונה מול הסכנה של בחירות חוזרות?")
    st.caption("שתי מפלגות צריכות זו את זו לקואליציה, ונאבקות על פרס (ראשות הממשלה או תיקים בכירים). "
               "כל אחת יכולה לוותר ולהסכים לחלוקה, או להתעקש על הפרס כולו. אם שתיהן מתעקשות, "
               "אין ממשלה והולכים לבחירות. הפחד מבחירות הוא מה שגורם למישהי לסטות מהכביש.")
    playable = [n for n in NAMES if n not in ARAB]
    k1, k2, k3 = st.columns(3)
    ca = k1.selectbox("שחקנית א'", playable, index=playable.index("הליכוד"), key=K("ch_a"))
    cb_opts = [n for n in playable if n != ca and chicken_coalitions(ca, n)]
    cb = k2.selectbox("שחקנית ב'", cb_opts, index=cb_opts.index("ישר") if "ישר" in cb_opts else 0, key=K("ch_b"))
    stake = k3.slider("הפרס שעל הכף", 0.0, 1.0, float(p.pm_premium), 0.05, key=K("ch_stake"),
                      help="ברירת המחדל היא פרמיית ראשות הממשלה. בוויתור הדדי כל אחת מקבלת חצי (רוטציה).")
    auto = chicken_game(ca, cb, p, stake=stake)
    coal_opts = chicken_coalitions(ca, cb)
    coal = st.selectbox("הקואליציה שעליה נאבקים", coal_opts, index=coal_opts.index(auto.coalition),
                        format_func=lambda c: f"{label(c, p)}  ({seats(c)})", key=K(f"ch_c_{ca}_{cb}"),
                        help="ברירת המחדל: הקואליציה שבה השחקנית החלשה יותר מבין השתיים מרוויחה הכי הרבה.")
    g = chicken_game(ca, cb, p, coalition=coal, stake=stake)

    st.markdown("##### מטריצת התשלומים")
    cell = lambda x, y: (("⭐ " if (x, y) in g.pure_eq else "")
                         + f"{ca}: {g.payoffs[(x, y)][0]:.2f} | {cb}: {g.payoffs[(x, y)][1]:.2f}")
    mat = pd.DataFrame({f"{cb} {y}": [cell(x, y) for x in (SWERVE, STRAIGHT)] for y in (SWERVE, STRAIGHT)},
                       index=[f"{ca} {x}" for x in (SWERVE, STRAIGHT)])
    st.table(mat)
    st.caption("⭐ = שיווי משקל נאש טהור. התא הימני-תחתון (שתיהן מתעקשות) הוא בחירות חוזרות: "
               "כל אחת מקבלת את ערך החוץ שלה.")

    m1, m2, m3 = st.columns(3)
    m1.metric(f"הפחד של {ca}", f"{g.fear[ca]:.2f}", help="כמה היא מפסידה מבחירות לעומת כניעה. שלילי = מעדיפה בחירות.")
    m2.metric(f"הפחד של {cb}", f"{g.fear[cb]:.2f}", help="כמה היא מפסידה מבחירות לעומת כניעה. שלילי = מעדיפה בחירות.")
    m3.metric("הסתברות לבחירות", f"{g.p_elections:.0%}")

    if g.kind == "צ'יקן":
        winner = ca if g.risk_dominant == (STRAIGHT, SWERVE) else cb
        st.info(f"**🐔 צ'יקן אמיתי.** שתיהן חוששות מבחירות, ולכן יש שני שיווי משקל: באחד {ca} מנצחת "
                f"ובשני {cb}. מי שתצליח להתחייב ראשונה (\"אנחנו לא נכנסים לרוטציה\") תנצח.\n\n"
                f"בשיווי המשקל המעורב {ca} מתעקשת בהסתברות {g.mixed[ca]:.0%} ו{cb} ב-{g.mixed[cb]:.0%}, "
                f"וההתנגשות (בחירות) קורית ב-{g.p_elections:.0%} מהמקרים.\n\n"
                f"**דומיננטיות בסיכון (הרסאניי-זלטן):** {winner} צפויה לנצח, כי היריבה שלה חוששת יותר מבחירות.")
    elif g.kind == "התנגשות ודאית":
        st.error("**💥 התנגשות ודאית.** אף אחת מהשתיים לא חוששת מבחירות: לכל אחת עדיף ללכת לבחירות "
                 "מאשר להיכנע. להתעקש היא אסטרטגיה דומיננטית לשתיהן, והתוצאה היא פלונטר.")
    elif g.kind == "אין על מה להילחם":
        st.success("**🤝 אין על מה להילחם.** הפרס אפס, ולכן אין סיבה להתעקש.")
    else:
        bold = ca if g.fear[ca] <= 0 else cb
        soft = cb if bold == ca else ca
        st.warning(f"**🚗 {bold} לא חוששת מבחירות.** לה עדיף ללכת לבחירות מאשר להיכנע, ולכן האיום שלה "
                   f"להתעקש אמין. {soft} חוששת, ולכן מוותרת: {bold} לוקחת את כל הפרס. "
                   "זה לא באמת צ'יקן, כי רק צד אחד מפחד מההתנגשות.")
    others = [m for m in coal if m not in (ca, cb)]
    if others:
        st.caption(f"המשחק מתמקד בשתי השחקניות ומניח ששאר השותפות ({', '.join(others)}) מצטרפות. "
                   "בלשונית התחזית בודקים גם אותן, ולכן קואליציה יכולה להיכשל שם גם כשהצ'יקן נגמר בלי בחירות.")

    st.markdown("##### 🎲 המתווך של אומן: שיווי משקל מתואם")
    with st.expander("מה זה שיווי משקל מתואם? (במילים פשוטות)"):
        st.markdown(
            "בשיווי המשקל המעורב כל מפלגה מגרילה לבד אם להתעקש, ולפעמים שתיהן מתעקשות ביחד, וזה נגמר בבחירות. "
            "ישראל אומן (1974) הראה שאפשר לעשות טוב יותר אם יש **מתווך**: מישהו שמגריל תוצאה ולוחש לכל צד "
            "רק את מה שהוא צריך לעשות.\n\n"
            "בצ'יקן המתווך אף פעם לא אומר לשתיהן \"התעקשו\", ולכן אין התנגשות. אבל הוא גם לא יכול להמליץ "
            "על רוטציה בכל פעם. אם שתיהן יודעות שתמיד ימליצו להן לוותר, כל אחת תעדיף לבגוד ולהתעקש. "
            "הטריק הוא שכשמפלגה שומעת \"תוותרי\", היא לא יודעת אם ליריבה אמרו גם \"תוותרי\" (רוטציה) או "
            "\"תתעקשי\". אם היא תתעקש בכל זאת, היא עלולה להתנגש ולהגיע לבחירות. **הפחד הזה גורם לה לציית**, "
            "בלי חוזה ובלי אכיפה.\n\n"
            "בפוליטיקה הישראלית, מתווך כזה יכול להיות הנשיא (סדר הטלת המנדט), סקר מוסכם, הסכם רוטציה "
            "שבו מי ראשון נקבע בהגרלה, או מתווך חיצוני.")
    ce = correlated_equilibrium(g)
    pr = ce.probs
    if g.kind == "צ'יקן":
        e1, e2, e3 = st.columns(3)
        e1.metric("בחירות עם מתווך", f"{ce.p_elections:.0%}",
                  delta=f"{ce.p_elections - g.p_elections:+.0%}", delta_color="inverse",
                  help="השינוי לעומת שיווי המשקל המעורב, בלי מתווך.")
        e2.metric(f"{ca}: רווח מהמתווך", f"{ce.payoffs[0]:.2f}",
                  delta=f"{ce.payoffs[0] - ce.mixed_payoffs[0]:+.2f}")
        e3.metric(f"{cb}: רווח מהמתווך", f"{ce.payoffs[1]:.2f}",
                  delta=f"{ce.payoffs[1] - ce.mixed_payoffs[1]:+.2f}")
        rec = pd.DataFrame({"מה המתווך ממליץ": ["רוטציה (שתיהן מוותרות)", f"{ca} לוקחת הכל",
                                                f"{cb} לוקחת הכל", "שתיהן מתעקשות (בחירות)"],
                            "הסתברות": [pr[(SWERVE, SWERVE)], pr[(STRAIGHT, SWERVE)],
                                        pr[(SWERVE, STRAIGHT)], pr[(STRAIGHT, STRAIGHT)]]})
        rec["הסתברות"] = (rec["הסתברות"] * 100).round(0)
        st.dataframe(rec, hide_index=True, width="stretch",
                     column_config={"הסתברות": st.column_config.ProgressColumn(format="%d%%", min_value=0, max_value=100)})
        st.caption(f"המתווך שנבחר ממקסם את סכום התשלומים, ומבין אלה ממליץ על רוטציה בתדירות הגבוהה ביותר "
                   f"שעדיין גורמת לשתיהן לציית. רוטציה תמיד היא לא שיווי משקל: כל אחת הייתה מתעקשת. "
                   f"שימו לב שגם עם מתווך, המפלגה שחוששת פחות מבחירות מקבלת את הפרס כולו בתדירות גבוהה יותר. "
                   f"על פני כל שיוויי המשקל המתואמים, ההסתברות לבחירות נעה בין "
                   f"{ce.p_el_range[0]:.0%} ל-{ce.p_el_range[1]:.0%}. כלומר, מתווך גרוע יכול גם להזיק.")
    else:
        st.caption("שיווי משקל מתואם משנה את התמונה רק בצ'יקן אמיתי, כשלשתיהן יש מה להפסיד בבחירות. "
                   "כאן יש לכל היותר שיווי משקל אחד שמתאים לכולן, והמתווך לא יכול לשפר אותו.")

    st.markdown("##### כמה הפחד מבחירות מונע אותן?")
    sweeps = {"עלות / עייפות מבחירות חוזרות": ("election_cost", 0.0, 1.0),
              "שנאת הפסד (λ)": ("loss_aversion", 1.0, 4.0),
              "רגישות לתוצאת הבחירות": ("risk_k", 0.0, 1.5),
              "פרמיית ממשלת מעבר לליכוד": ("caretaker", 0.0, 1.0)}
    sw = st.selectbox("פרמטר לסריקה", list(sweeps), key=K("ch_sweep"))
    attr, lo, hi = sweeps[sw]
    xs = np.linspace(lo, hi, 41)
    rows = []
    for x in xs:
        gx = chicken_game(ca, cb, replace(p, **{attr: float(x)}), coalition=coal, stake=stake)
        rows += [{sw: x, "מדד": "הסתברות לבחירות", "ערך": gx.p_elections},
                 {sw: x, "מדד": f"הפחד של {ca}", "ערך": gx.fear[ca]},
                 {sw: x, "מדד": f"הפחד של {cb}", "ערך": gx.fear[cb]},
                 {sw: x, "מדד": "רוטציה עם מתווך", "ערך": correlated_equilibrium(gx).probs[(SWERVE, SWERVE)]}]
    fig = px.line(pd.DataFrame(rows), x=sw, y="ערך", color="מדד", height=420)
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=getattr(p, attr), line_dash="dot", line_color="gray", annotation_text="ערך נוכחי")
    st.plotly_chart(fig, width="stretch")
    st.caption("כשהפחד של מפלגה יורד מתחת לאפס, היא כבר לא חוששת מבחירות והאיום שלה להתעקש נעשה אמין. "
               "כששני הפחדים מתחת לאפס, הבחירות ודאיות. "
               "שימו לב לפרדוקס של שיווי המשקל המעורב: הפחד של מפלגה לא משנה את ההסתברות שהיא מתעקשת, "
               "אלא את ההסתברות שהיריבה שלה מתעקשת.")
