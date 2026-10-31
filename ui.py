"""קטעים משותפים לכל הדפים של האפליקציה."""
import pandas as pd
import streamlit as st

from model import ELECTION_RISK, NAMES, REDLINE_GROUPS, Params, default_hardness, power_indices

BLOC_COLORS = {"נתניהו": "#2b6cb0", "אופוזיציה": "#dd6b20", "ערביות": "#2f855a"}


def K(name):
    """מפתח ווידג'ט עם מספר גרסה. הגדלת הגרסה יוצרת ווידג'טים חדשים בערכי ברירת המחדל."""
    return f"{name}_v{st.session_state.reset_ver}"


def reset_params():
    st.session_state.reset_ver += 1
    st.session_state.pop("risk_saved", None)
    st.session_state.pop("saved_params", None)


def risk_defaults():
    return {n: ELECTION_RISK[n] for n in NAMES}


def _param_keys():
    suffix = f"_v{st.session_state.reset_ver}"
    return [k for k in st.session_state
            if isinstance(k, str) and k.endswith(suffix) and k != K("risk")]


def save_params():
    """Streamlit מוחק את המצב של ווידג'טים שלא הוצגו בדף הנוכחי, גם אם כותבים אותו מחדש
    ל-session_state. לכן בסוף כל ריצה שומרים עותק של כל הערכים במפתח נפרד.
    טבלת ההימור (data_editor) נשמרת בנפרד ב-risk_saved."""
    st.session_state.saved_params = {k: st.session_state[k] for k in _param_keys()}


def restore_params():
    """בתחילת כל ריצה: מחזירים ערכים שנמחקו כשעברנו לדף בלי הווידג'טים שלהם."""
    for k, v in st.session_state.get("saved_params", {}).items():
        if k not in st.session_state:
            st.session_state[k] = v


def sidebar_params() -> Params:
    """סרגל הפרמטרים החופשיים. משותף לכל הדפים שתלויים בפרמטרים."""
    sb = st.sidebar
    sb.header("⚙️ פרמטרים חופשיים")

    sb.button("🔄 אתחול לערכי ברירת המחדל", on_click=reset_params, width="stretch")
    sb.subheader("העדפות כלליות")
    alpha = sb.slider("α: משקל ג'ובים מול אידאולוגיה", 0.0, 1.0, 0.5, 0.05, key=K("alpha"),
                      help="0 = מפלגות אכפת להן רק ממדיניות, 1 = רק מתיקים ותקציבים")
    pm_premium = sb.slider("פרמיית ראשות הממשלה", 0.0, 1.0, 0.4, 0.05, key=K("pm"))
    rotation = sb.checkbox("רוטציה אפשרית בין שתי הגדולות", True, key=K("rot"))
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

    sb.subheader("הגרלת הבחירות החוזרות")
    risk_k = sb.slider("רגישות לתוצאת הבחירות", 0.0, 1.5, 0.5, 0.05, key=K("riskk"),
                       help="כמה ההימור על המנדטים משפיע על ערך הבחירות החוזרות. 0 = מתעלמים מההימור.")
    loss_aversion = sb.slider("שנאת הפסד (λ)", 1.0, 4.0, 2.25, 0.05, key=K("lam"),
                              help="פי כמה הפסד של מנדט מתחת לנקודת הייחוס כואב יותר מרווח של מנדט מעליה. "
                                   "2.25 הוא הערך של כהנמן וטברסקי.")
    threshold = sb.slider("אחוז החסימה (במנדטים)", 0.0, 6.0, 4.0, 0.5, key=K("thr"),
                          help="מפלגה שיורדת מתחת לסף לא נכנסת לכנסת ומאבדת את כל המנדטים.")
    with sb.expander("ההימור של כל מפלגה"):
        st.caption("Δ = שינוי צפוי במנדטים בבחירות חוזרות. σ = אי-ודאות (סטיית תקן). "
                   "ייחוס = המעמד שהמפלגה רואה כ'שלה': מתחתיו היא בתחום ההפסדים ומוכנה להמר.")
        # בסיס הטבלה קבוע כל עוד היא מוצגת. כשחוזרים מדף אחר היא נבנית מחדש מהערכים השמורים.
        if K("risk") not in st.session_state or "risk_base" not in st.session_state:
            st.session_state.risk_base = st.session_state.get("risk_saved", risk_defaults())
        base = st.session_state.risk_base
        risk_df = pd.DataFrame([{"מפלגה": n, "Δ": base[n][0], "σ": base[n][1], "ייחוס": base[n][2]}
                                for n in NAMES])
        risk_df = st.data_editor(risk_df, hide_index=True, disabled=["מפלגה"], key=K("risk"),
                                 column_config={
                                     "מפלגה": st.column_config.TextColumn(width="small"),
                                     "Δ": st.column_config.NumberColumn(step=0.5, min_value=-15, max_value=15,
                                                                        width="small", format="%.1f"),
                                     "σ": st.column_config.NumberColumn(step=0.5, min_value=0, max_value=10,
                                                                        width="small", format="%.1f"),
                                     "ייחוס": st.column_config.NumberColumn(step=1, min_value=1, max_value=60,
                                                                            width="small", format="%d")})
        risk = {r["מפלגה"]: (float(r["Δ"]), float(r["σ"]), float(r["ייחוס"])) for _, r in risk_df.iterrows()}
        st.session_state.risk_saved = risk

    sb.subheader("קווים אדומים (קשיחות)")
    hard_def = default_hardness()
    hardness = {k: sb.slider(desc, 0.0, 3.0, hard_def[k], 0.1, key=K(f"h_{k}"))
                for k, (desc, _) in REDLINE_GROUPS.items()}

    sb.subheader("המפלגות הערביות")
    arab_external = sb.checkbox("תמיכה מבחוץ, בלי תיקים (מודל 'בנט-לפיד' / רע\"מ)", True, key=K("ext"))
    raam_inside = sb.checkbox("רע\"מ בתוך הקואליציה (כמו ב-2021)", True, key=K("raam_in"),
                              help="רע\"מ חברה בקואליציה ומשלמת ומקבלת כמו כל שותפה. "
                                   "רק המשותפת נשארת תומכת מבחוץ.")
    external_discount = sb.slider("עד כמה תמיכה מבחוץ מרככת את החרם", 0.0, 1.0, 0.5, 0.05, key=K("disc"))
    arab_budget = sb.slider("ערך ההישגים התקציביים לתומכת חיצונית", 0.0, 1.0, 0.35, 0.05, key=K("budget"))

    p = Params(alpha=alpha, w_sec=w_sec, w_rel=w_rel, w_bibi=w_bibi, w_jud=w_jud, pm_premium=pm_premium,
               rotation=rotation, election_cost=election_cost, base_outside=base_outside,
               risk=risk, loss_aversion=loss_aversion, threshold=threshold, risk_k=risk_k,
               hardness=hardness, arab_external=arab_external,
               raam_inside=raam_inside, external_discount=external_discount, arab_budget=arab_budget,
               caretaker=caretaker)
    return p


@st.cache_data
def cached_power():
    return power_indices()
