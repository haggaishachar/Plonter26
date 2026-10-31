"""קטעים משותפים לכל הדפים של האפליקציה."""
from html import escape

import streamlit as st

from model import ELECTION_FEAR, NAMES, PARTIES, REDLINE_GROUPS, Params, default_hardness, power_indices

BLOC_COLORS = {"נתניהו": "#2b6cb0", "אופוזיציה": "#dd6b20", "ערביות": "#2f855a"}


def K(name):
    """מפתח ווידג'ט עם מספר גרסה. הגדלת הגרסה יוצרת ווידג'טים חדשים בערכי ברירת המחדל."""
    return f"{name}_v{st.session_state.reset_ver}"


def reset_params():
    st.session_state.reset_ver += 1
    st.session_state.pop("saved_params", None)


def _param_keys():
    suffix = f"_v{st.session_state.reset_ver}"
    return [k for k in st.session_state
            if isinstance(k, str) and k.endswith(suffix)]


def save_params():
    """Streamlit מוחק את המצב של ווידג'טים שלא הוצגו בדף הנוכחי, גם אם כותבים אותו מחדש
    ל-session_state. לכן בסוף כל ריצה שומרים עותק של כל הערכים במפתח נפרד."""
    st.session_state.saved_params = {k: st.session_state[k] for k in _param_keys()}


def restore_params():
    """בתחילת כל ריצה: מחזירים ערכים שנמחקו כשעברנו לדף בלי הווידג'טים שלהם."""
    for k, v in st.session_state.get("saved_params", {}).items():
        if k not in st.session_state:
            st.session_state[k] = v


def is_mobile():
    """זיהוי טלפון לפי ה-User-Agent. השרת לא יודע את רוחב המסך, וזה הסימן הזמין היחיד."""
    ua = st.context.headers.get("User-Agent", "")
    return any(t in ua for t in ("Mobi", "Android", "iPhone"))


def chart(fig):
    """מציג גרף Plotly עם מקרא אופקי מעל השטח, כדי שלא יגזול רוחב בטלפון.
    הכותרת עוברת לטקסט מעל הגרף, כי בתוך הגרף היא מתנגשת במקרא."""
    if fig.layout.title.text:
        st.markdown(f"**{escape(fig.layout.title.text)}**")
        fig.layout.title = None
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    fig.update_layout(margin=dict(l=10, r=10, t=40),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1))
    st.plotly_chart(fig, width="stretch")


def sidebar_params() -> Params:
    """סרגל הפרמטרים החופשיים. משותף לכל הדפים שתלויים בפרמטרים.
    בטלפון הסרגל מוסתר מאחורי כפתור קטן, אז הפרמטרים מוצגים במקום זה בתוך הדף."""
    if is_mobile():
        sb = st.expander("⚙️ פרמטרים חופשיים: לחצו כדי לשנות")
    else:
        sb = st.sidebar
        sb.header("⚙️ פרמטרים חופשיים")

    sb.button("🔄 אתחול לערכי ברירת המחדל", on_click=reset_params, width="stretch")
    sb.subheader("העדפות כלליות")
    alpha = sb.slider("α: משקל ג'ובים מול אידאולוגיה", 0.0, 1.0, 0.5, 0.05, key=K("alpha"),
                      help="0 = מפלגות אכפת להן רק ממדיניות, 1 = רק מתיקים ותקציבים")
    pm_premium = sb.slider("פרמיית ראשות הממשלה", 0.0, 1.0, 0.4, 0.05, key=K("pm"))
    rotation = sb.checkbox("רוטציה אפשרית בין שתי הגדולות", True, key=K("rot"))
    min_only = sb.checkbox("רק קואליציות מינימליות (בלי מפלגה מיותרת)", True, key=K("minonly"))

    sb.subheader("קווים אדומים (קשיחות)")
    hard_def = default_hardness()
    hardness = {k: sb.slider(desc, 0.0, 3.0, hard_def[k], 0.1, key=K(f"h_{k}"))
                for k, (desc, _) in REDLINE_GROUPS.items()}

    sb.subheader("חשש מבחירות חדשות")
    election_fear = {n: sb.slider(n, -0.5, 1.0, ELECTION_FEAR[n], 0.01, key=K(f"fear_{n}")) for n in NAMES}

    sb.subheader("המפלגות הערביות")
    arab_external = sb.checkbox("תמיכה מבחוץ, בלי תיקים (מודל 'בנט-לפיד' / רע\"מ)", True, key=K("ext"))
    raam_inside = sb.checkbox("רע\"מ בתוך הקואליציה (כמו ב-2021)", True, key=K("raam_in"),
                              help="רע\"מ חברה בקואליציה ומשלמת ומקבלת כמו כל שותפה. "
                                   "רק המשותפת נשארת תומכת מבחוץ.")
    external_discount = sb.slider("עד כמה תמיכה מבחוץ מרככת את החרם", 0.0, 1.0, 0.5, 0.05, key=K("disc"))

    sb.subheader("חשיבות הצירים")
    w_sec = sb.slider("ביטחון / מדיני", 0.0, 3.0, 1.0, 0.1, key=K("wsec"))
    w_rel = sb.slider("דת ומדינה (גיוס, שבת)", 0.0, 3.0, 1.0, 0.1, key=K("wrel"))
    w_bibi = sb.slider("יחס אישי לנתניהו", 0.0, 3.0, 1.0, 0.1, key=K("wbibi"))
    w_jud = sb.slider("רפורמה משפטית", 0.0, 3.0, 1.0, 0.1, key=K("wjud"))

    p = Params(alpha=alpha, w_sec=w_sec, w_rel=w_rel, w_bibi=w_bibi, w_jud=w_jud, pm_premium=pm_premium,
               rotation=rotation, election_fear=election_fear, hardness=hardness, arab_external=arab_external,
               raam_inside=raam_inside, external_discount=external_discount,
               min_only=min_only)
    return p


@st.cache_data
def cached_power():
    return power_indices()


def bloc_header():
    """כותרת משותפת לדפי המודל האינטראקטיבי: המנדטים של כל מפלגה לפי גוש."""
    st.title("🧩 הפלונטר של הכנסת ה-26")

    bloc_order = ["נתניהו", "אופוזיציה", "ערביות"]
    party_order = sorted(NAMES, key=lambda x: (bloc_order.index(PARTIES[x]["bloc"]), -PARTIES[x]["seats"]))
    bloc_titles = {"נתניהו": "גוש נתניהו", "אופוזיציה": "גוש האופוזיציה", "ערביות": "מפלגות ערביות"}
    cols = []
    for b in bloc_order:
        members = [n for n in party_order if PARTIES[n]["bloc"] == b]
        items = "".join(f'<div style="display:flex;justify-content:space-between;font-size:0.9em">'
                        f'<span>{n}</span><b>{PARTIES[n]["seats"]}</b></div>' for n in members)
        total = sum(PARTIES[n]["seats"] for n in members)
        cols.append(f'<div class="bloc" style="border-top:4px solid {BLOC_COLORS[b]};padding-top:4px">'
                    f'<div style="display:flex;justify-content:space-between;gap:6px;color:{BLOC_COLORS[b]};'
                    f'font-weight:700;margin-bottom:2px"><span style="white-space:nowrap">{bloc_titles[b]}</span><span>{total}</span></div>'
                    f'{items}</div>')
    st.markdown('<style>.blocs {display:grid; grid-template-columns:repeat(3,1fr); gap:24px; margin-bottom:16px}'
                '@media (max-width:640px) {.blocs {grid-template-columns:repeat(2,1fr); gap:12px 16px}}</style>'
                f'<div class="blocs">{"".join(cols)}</div>', unsafe_allow_html=True)


NEAR_TABLE_CSS = """<style>
.near-tbl {width:100%; border-collapse:separate; border-spacing:0; direction:rtl; font-size:0.92em;
           border:1px solid rgba(128,128,128,0.25); border-radius:10px; overflow:hidden; margin-bottom:1rem}
.near-tbl th {background:rgba(128,128,128,0.12); font-weight:600; text-align:right; padding:10px 12px;
              white-space:nowrap; font-size:0.85em; opacity:0.85; border:none}
.near-tbl td {padding:10px 12px; vertical-align:top; border:none; border-top:1px solid rgba(128,128,128,0.18);
              text-align:right}
.near-tbl tr:hover td {background:rgba(128,128,128,0.06)}
.near-tbl .rank {width:1%; opacity:0.55; font-weight:700; text-align:center}
.near-tbl .num {width:1%; white-space:nowrap; font-variant-numeric:tabular-nums; text-align:center}
.near-tbl .chips {display:flex; flex-wrap:wrap; gap:4px}
.near-tbl .chip {display:inline-block; padding:1px 8px; border-radius:999px; font-size:0.88em; white-space:nowrap;
                 border:1px solid currentColor; line-height:1.6}
.near-tbl .chip.ext {border-style:dashed; opacity:0.75}
.near-tbl .chip.block {color:#e53e3e; background:rgba(229,62,62,0.12); font-weight:600}
.near-tbl .ext-lbl {font-size:0.8em; opacity:0.6; align-self:center; margin-inline-start:4px}
.near-tbl .gap {min-width:110px}
.near-tbl .gap-val {font-weight:700; font-variant-numeric:tabular-nums}
.near-tbl .gap-bar {height:6px; border-radius:3px; background:rgba(128,128,128,0.18); margin-top:4px}
.near-tbl .gap-bar > div {height:100%; border-radius:3px; background:#e53e3e}
.near-tbl ul {margin:0; padding-inline-start:1.1em}
.near-tbl li {margin:0; line-height:1.5; font-size:0.95em}
.near-tbl .muted {opacity:0.5}
.near-tbl .coal {width:34%}
.near-tbl .lines {width:26%}
.near-wrap {overflow-x:auto}
.near-wrap .near-tbl {min-width:720px}
/* בטלפון: כל שורה הופכת לכרטיס, וכותרת העמודה מוצגת ליד כל ערך */
@media (max-width:640px) {
  .near-wrap .near-tbl {min-width:0; border:none; border-radius:0}
  .near-tbl thead {display:none}
  .near-tbl, .near-tbl tbody, .near-tbl tr, .near-tbl td {display:block; width:auto !important}
  .near-tbl tr {border:1px solid rgba(128,128,128,0.25); border-radius:10px; margin-bottom:10px; padding:6px 0}
  .near-tbl tr:hover td {background:none}
  .near-tbl td {border:none; padding:4px 12px; text-align:right}
  .near-tbl td[data-label]::before {content:attr(data-label); display:block; font-size:0.78em; opacity:0.6}
  .near-tbl .rank {text-align:right; font-size:0.85em}
  .near-tbl .rank::before {content:"#"}
}
</style>"""


def party_chip(name, cls=""):
    color = BLOC_COLORS[PARTIES[name]["bloc"]]
    return f'<span class="chip {cls}" style="color:{color};background:{color}1f">{escape(name)}</span>'


def near_table_html(rows):
    """טבלת "הכי קרובות להיות ישימות". כל שורה: dict עם gov, ext, seats, rotation, blockers, gap, lines."""
    max_gap = max((r["gap"] for r in rows), default=0) or 1
    head = ("<tr><th>#</th><th class=\"coal\">קואליציה</th><th>מנדטים</th><th>רוטציה</th><th>חוסמות</th>"
            "<th>מרחק מאזור ההסכמה</th><th class=\"lines\">הקווים האדומים שנחצים</th></tr>")
    body = []
    for i, r in enumerate(rows, 1):
        coal = "".join(party_chip(n) for n in r["gov"])
        if r["ext"]:
            coal += '<span class="ext-lbl">בתמיכת:</span>' + "".join(party_chip(n, "ext") for n in r["ext"])
        blockers = "".join(f'<span class="chip block">{escape(b)}</span>' for b in r["blockers"])
        lines = "".join(f"<li>{escape(x)}</li>" for x in r["lines"])
        rot = escape(r["rotation"]) if r["rotation"] else '<span class="muted">—</span>'
        pct = 100 * r["gap"] / max_gap
        body.append(
            f'<tr><td class="rank">{i}</td><td data-label="קואליציה"><div class="chips">{coal}</div></td>'
            f'<td class="num" data-label="מנדטים"><b>{r["seats"]}</b></td><td class="num" data-label="רוטציה">{rot}</td>'
            f'<td data-label="חוסמות"><div class="chips">{blockers}</div></td>'
            f'<td class="gap" data-label="מרחק מאזור ההסכמה"><span class="gap-val">{r["gap"]:.3f}</span>'
            f'<div class="gap-bar"><div style="width:{pct:.0f}%"></div></div></td>'
            f'<td data-label="הקווים האדומים שנחצים"><ul>{lines}</ul></td></tr>')
    return (f'{NEAR_TABLE_CSS}<div class="near-wrap"><table class="near-tbl"><thead>{head}</thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')
