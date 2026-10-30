"""מודל תורת-משחקים לפלונטר הקואליציוני אחרי הבחירות לכנסת ה-26 (אוקטובר 2026).

המודל:
1. משחק הצבעה משוקלל [61; מנדטים] -> מדדי כוח (Banzhaf, Shapley-Shubik).
2. לכל מפלגה i ולכל קואליציה C: תועלת =
      α·ג'ובים(i,C) + (1-α)·מדיניות(i,C) + פרמיית_רה"מ − Σ קווים_אדומים(i,j∈C)
   ג'ובים לפי כלל גמסון (חלק יחסי מהמנדטים בקואליציה).
   מדיניות = 1 − מרחק משוקלל ממרכז הכובד של הקואליציה.
3. נקודת אי-הסכמה = בחירות חוזרות (ערך חוץ E_i). מפלגה מצטרפת רק אם U ≥ E_i.
4. מנגנון הרכבה: מרכיב/ת (פורמטור) לפי סדר מנדטים, בוחר את הקואליציה
   הישימה הטובה לו. אם אף מרכיב לא מצליח -> פלונטר -> בחירות.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import combinations
from math import factorial

import numpy as np

QUOTA = 61

# מיקומים על ארבעה צירים (0-10): ביטחון/נצי, דת-ומדינה, יחס אישי לנתניהו,
# רפורמה משפטית (10 = תמיכה ברפורמה, 0 = הגנה על עצמאות בתי המשפט)
PARTIES = {
    "הליכוד": dict(seats=27, bloc="נתניהו", sec=7.5, rel=6.0, bibi=10.0, jud=9.0),
    "ש\"ס": dict(seats=6, bloc="נתניהו", sec=6.5, rel=9.0, bibi=9.0, jud=9.0),
    "יהדות התורה": dict(seats=7, bloc="נתניהו", sec=5.5, rel=10.0, bibi=8.0, jud=9.0),
    "הציונות הדתית": dict(seats=6, bloc="נתניהו", sec=9.5, rel=8.5, bibi=8.0, jud=10.0),
    "עוצמה יהודית": dict(seats=7, bloc="נתניהו", sec=10.0, rel=8.0, bibi=8.0, jud=10.0),
    "ישר": dict(seats=21, bloc="אופוזיציה", sec=6.0, rel=3.5, bibi=1.0, jud=2.0),
    "ביחד": dict(seats=12, bloc="אופוזיציה", sec=8.0, rel=4.5, bibi=2.0, jud=5.0),
    "הדמוקרטים": dict(seats=8, bloc="אופוזיציה", sec=3.0, rel=1.0, bibi=0.0, jud=0.0),
    "ישראל ביתנו": dict(seats=7, bloc="אופוזיציה", sec=8.0, rel=1.5, bibi=1.0, jud=3.0),
    "הרשימה המשותפת": dict(seats=12, bloc="ערביות", sec=1.0, rel=3.0, bibi=0.0, jud=1.0),
    "רע\"מ": dict(seats=7, bloc="ערביות", sec=2.5, rel=6.5, bibi=2.0, jud=4.0),
}
NAMES = list(PARTIES)
ARAB = {"הרשימה המשותפת", "רע\"מ"}
HAREDI = {"ש\"ס", "יהדות התורה"}
FAR_RIGHT = {"הציונות הדתית", "עוצמה יהודית"}
CHANGE = {"ישר", "ביחד", "הדמוקרטים", "ישראל ביתנו"}

# קבוצות של קווים אדומים. כל אחת: (תיאור, מפתח הפרמטר שמכפיל אותה, זוגות (i, j))
# ערך הקנס המוטל על i אם j בקואליציה.
REDLINE_GROUPS = {
    "boycott_bibi": ("גוש השינוי לא יושב עם נתניהו",
                     [(c, "הליכוד") for c in CHANGE]),
    "far_right_vs_arabs": ("הימין הקיצוני ⟷ מפלגות ערביות",
                           [(f, a) for f in FAR_RIGHT for a in ARAB]
                           + [(a, f) for f in FAR_RIGHT for a in ARAB]),
    "far_right_vs_left": ("הימין הקיצוני ⟷ הדמוקרטים",
                          [(f, "הדמוקרטים") for f in FAR_RIGHT]
                          + [("הדמוקרטים", f) for f in FAR_RIGHT]),
    "draft_law": ("חוק הגיוס: חרדים ⟷ ליברמן / ישר / ביחד",
                  [(h, x) for h in HAREDI for x in ("ישראל ביתנו", "ישר", "ביחד")]
                  + [(x, h) for h in HAREDI for x in ("ישראל ביתנו", "ישר", "ביחד")]),
    "zionist_vs_arabs": ("מפלגות ציוניות ⟷ מפלגות ערביות",
                         [(z, a) for z in NAMES if z not in ARAB | FAR_RIGHT
                          for a in ARAB]),
    "arabs_vs_right": ("המפלגות הערביות ⟷ ממשלת ימין",
                       [(a, r) for a in ARAB for r in ("הליכוד",) ]),
}
# משקל בסיסי לכל זוג (לפני הכפלה בפרמטר הקשיחות)
BASE_PENALTY = 0.6


@dataclass
class Params:
    alpha: float = 0.5                 # משקל ג'ובים מול מדיניות
    w_sec: float = 1.0                 # חשיבות ציר הביטחון
    w_rel: float = 1.0                 # חשיבות ציר דת-ומדינה
    w_bibi: float = 1.0                # חשיבות ציר היחס האישי לנתניהו
    w_jud: float = 1.0                 # חשיבות ציר הרפורמה המשפטית
    pm_premium: float = 0.4            # בונוס לראשות הממשלה (למפלגה הגדולה בקואליציה)
    rotation: bool = True              # ברוטציה הפרמיה מתחלקת בין שתי הגדולות
    election_cost: float = 0.3         # עלות כללית של בחירות חוזרות (מוריד את ערך החוץ)
    base_outside: float = 0.55         # ערך בסיס של בחירות חוזרות
    risk: dict = field(default_factory=dict)       # לכל מפלגה: (Δ מנדטים צפוי, σ אי-ודאות, נקודת ייחוס)
    loss_aversion: float = 2.25        # λ: פי כמה הפסד כואב יותר מרווח באותו גודל
    threshold: float = 4.0             # אחוז החסימה במנדטים: מתחתיו המפלגה לא נכנסת
    risk_k: float = 0.5                # רגישות ערך הבחירות לתוצאת ההגרלה
    hardness: dict = field(default_factory=dict)   # קשיחות כל קבוצת קווים אדומים (0-3)
    arab_external: bool = True         # מפלגות ערביות כתומכות מבחוץ (בלי תיקים)
    external_discount: float = 0.5     # כמה תמיכה מבחוץ מקטינה קווים אדומים כלפיהן
    arab_budget: float = 0.35          # הישגים תקציביים לתומכת חיצונית
    caretaker: float = 0.15            # פרמיית ממשלת מעבר: ערך הפלונטר לליכוד, שנשאר בשלטון


def default_hardness():
    return {"boycott_bibi": 1.0, "far_right_vs_arabs": 3.0, "far_right_vs_left": 1.5,
            "draft_law": 1.0, "zionist_vs_arabs": 0.7, "arabs_vs_right": 2.0}


def penalty_matrix(p: Params) -> np.ndarray:
    n = len(NAMES)
    M = np.zeros((n, n))
    idx = {name: k for k, name in enumerate(NAMES)}
    hard = {**default_hardness(), **p.hardness}
    for key, (_, pairs) in REDLINE_GROUPS.items():
        for i, j in pairs:
            M[idx[i], idx[j]] += BASE_PENALTY * hard[key]
    return M


def redline_breakdown(i, j, p: Params) -> dict:
    """הקנס ש-i משלמת על ישיבה עם j, מפורק לפי קבוצת הקו האדום."""
    hard = {**default_hardness(), **p.hardness}
    out = {}
    for key, (_, pairs) in REDLINE_GROUPS.items():
        n = sum(1 for a, b in pairs if a == i and b == j)
        if n:
            out[key] = BASE_PENALTY * hard[key] * n
    return out


def seats(c) -> int:
    return sum(PARTIES[x]["seats"] for x in c)


def all_winning_coalitions(min_only: bool = False):
    out = []
    for r in range(1, len(NAMES) + 1):
        for c in combinations(NAMES, r):
            s = seats(c)
            if s < QUOTA:
                continue
            if min_only and any(s - PARTIES[x]["seats"] >= QUOTA for x in c):
                continue
            out.append(c)
    return out


def power_indices():
    """מחזיר (Banzhaf מנורמל, Shapley-Shubik, מספר הקואליציות שבהן המפלגה מכרעת)."""
    n = len(NAMES)
    banz = dict.fromkeys(NAMES, 0)
    ss = dict.fromkeys(NAMES, 0.0)
    for i in NAMES:
        others = [x for x in NAMES if x != i]
        wi = PARTIES[i]["seats"]
        for r in range(0, n):
            for S in combinations(others, r):
                s = seats(S)
                if s < QUOTA <= s + wi:
                    banz[i] += 1
                    ss[i] += factorial(r) * factorial(n - r - 1) / factorial(n)
    tot = sum(banz.values())
    return {k: v / tot for k, v in banz.items()}, ss, banz


def _members_split(c, p: Params):
    """מחזיר (חברי ממשלה, תומכים מבחוץ)."""
    if p.arab_external:
        gov = [x for x in c if x not in ARAB]
        ext = [x for x in c if x in ARAB]
        if gov:
            return gov, ext
    return list(c), []


def policy_center(c, p: Params):
    w = np.array([PARTIES[x]["seats"] for x in c], float)
    pos = np.array([[PARTIES[x]["sec"], PARTIES[x]["rel"], PARTIES[x]["bibi"], PARTIES[x]["jud"]] for x in c])
    return (w[:, None] * pos).sum(0) / w.sum()


def _position(i):
    return np.array([PARTIES[i]["sec"], PARTIES[i]["rel"], PARTIES[i]["bibi"], PARTIES[i]["jud"]])


def weighted_distance(x, y, p: Params) -> float | None:
    """מרחק אוקלידי משוקלל לפי חשיבות הצירים (0-10). None אם כל המשקלים אפס."""
    wts = np.array([p.w_sec, p.w_rel, p.w_bibi, p.w_jud])
    if wts.sum() == 0:
        return None
    return float(np.sqrt((wts * (x - y) ** 2).sum() / wts.sum()))


def party_distance(i, j, p: Params) -> float | None:
    return weighted_distance(_position(i), _position(j), p)


def policy_utility(i, c, p: Params):
    d = weighted_distance(_position(i), policy_center(c, p), p)
    if d is None:
        return 0.5
    return 1 - d / 10


def pm_parties(gov):
    ranked = sorted(gov, key=lambda x: -PARTIES[x]["seats"])
    return ranked


def rotation_pair(c, p: Params):
    """אם צפויה רוטציה בקואליציה: (ראשונה, שנייה) לפי גודל. אחרת None."""
    gov, _ = _members_split(c, p)
    ranked = pm_parties(gov)
    if p.rotation and len(ranked) > 1 and PARTIES[ranked[1]]["seats"] >= 0.7 * PARTIES[ranked[0]]["seats"]:
        return ranked[0], ranked[1]
    return None


def utility(i, c, p: Params, M=None) -> float:
    """תועלת של מפלגה i מקואליציה c (גם אם i מחוץ לה)."""
    M = penalty_matrix(p) if M is None else M
    idx = {name: k for k, name in enumerate(NAMES)}
    gov, ext = _members_split(c, p)
    pol = policy_utility(i, c, p)
    if i not in c:
        return (1 - p.alpha) * pol * 0.6   # באופוזיציה: רק השפעה חלקית על מדיניות
    if i in ext:
        office = p.arab_budget
    else:
        office = PARTIES[i]["seats"] / seats(gov)
    u = p.alpha * office + (1 - p.alpha) * pol
    # פרמיית ראשות ממשלה
    ranked = pm_parties(gov)
    rot = rotation_pair(c, p)
    if rot:
        if i in rot:
            u += p.pm_premium / 2
    elif i == ranked[0]:
        u += p.pm_premium
    # קווים אדומים
    for j in c:
        if j == i:
            continue
        pen = M[idx[i], idx[j]]
        if (j in ext or i in ext):
            pen *= (1 - p.external_discount)
        u -= pen
    return u


# הגרלת הבחירות החוזרות לכל מפלגה: (Δ מנדטים צפוי, σ אי-ודאות במנדטים, נקודת ייחוס במנדטים).
# נקודת הייחוס היא המעמד שהמפלגה רואה כ"שלה". מתחתיה היא בתחום ההפסדים.
ELECTION_RISK = {
    "הליכוד": (3.0, 3.0, 32),           # איבד את המנדטים של וינטר, ומשווה את עצמו ל-32 של 2022
    "ש\"ס": (2.0, 2.0, 11),             # ירד מ-11 ל-6 ורוצה לחזור למעמדו
    "יהדות התורה": (1.0, 1.5, 7),
    "הציונות הדתית": (0.0, 2.0, 6),
    "עוצמה יהודית": (0.0, 2.0, 7),
    "ישר": (0.0, 3.0, 21),              # השמאל והמרכז התארגנו היטב: אין לאן לעלות
    "ביחד": (0.0, 2.0, 12),
    "הדמוקרטים": (0.0, 1.5, 8),
    "ישראל ביתנו": (0.0, 1.5, 7),
    "הרשימה המשותפת": (-2.0, 3.0, 12),  # שיא היסטורי, וחשש מאובדן כוח ומשוחד בחירות
    "רע\"מ": (-1.0, 2.5, 7),
}

INCUMBENT = "הליכוד"   # מפלגת ראש הממשלה, שממשיכה לכהן בממשלת מעבר עד שתקום ממשלה


def prospect_value(x, lam: float, a: float = 0.88):
    """פונקציית הערך של תורת הערכת הסיכויים (כהנמן-טברסקי): קעורה ברווחים, קמורה ומוכפלת ב-λ בהפסדים."""
    x = np.asarray(x, float)
    return np.where(x >= 0, np.abs(x) ** a, -lam * np.abs(x) ** a)


_GRID = np.linspace(-4, 4, 161)
_W = np.exp(-_GRID ** 2 / 2)
_W /= _W.sum()


def election_gamble(i, p: Params) -> float:
    """כמה המפלגה מרוויחה (חיובי) או מפסידה (שלילי) מהליכה לבחירות, לעומת שמירה על המנדטים הנוכחיים.
    התוצאה נמדדת יחסית לנקודת הייחוס, ומפלגה שיורדת מתחת לאחוז החסימה מקבלת 0 מנדטים."""
    delta, sigma, ref = p.risk.get(i, ELECTION_RISK[i])
    now = PARTIES[i]["seats"]
    ref = max(ref, 1)
    after = np.maximum(now + delta + sigma * _GRID, 0)
    after = np.where(after < p.threshold, 0, after)
    gamble = float((_W * prospect_value((after - ref) / ref, p.loss_aversion)).sum())
    keep = float(prospect_value((now - ref) / ref, p.loss_aversion))
    return gamble - keep


def threshold_risk(i, p: Params) -> float:
    """ההסתברות שהמפלגה תרד מתחת לאחוז החסימה בבחירות חוזרות."""
    delta, sigma, _ = p.risk.get(i, ELECTION_RISK[i])
    after = np.maximum(PARTIES[i]["seats"] + delta + sigma * _GRID, 0)
    return float(_W[after < p.threshold].sum())


def outside_option(i, p: Params) -> float:
    e = p.base_outside - p.election_cost + p.risk_k * election_gamble(i, p)
    if i == INCUMBENT:
        e += p.caretaker
    return e


@dataclass
class CoalitionResult:
    members: tuple
    seats: int
    utilities: dict
    surplus: dict
    feasible: bool
    blockers: list
    nash: float


def evaluate(p: Params, min_only=True):
    M = penalty_matrix(p)
    res = []
    for c in all_winning_coalitions(min_only=min_only):
        us = {i: utility(i, c, p, M) for i in c}
        sur = {i: us[i] - outside_option(i, p) for i in c}
        blockers = [i for i in c if sur[i] < 0]
        feas = not blockers
        nash = float(np.sum(np.log(np.maximum([sur[i] for i in c], 1e-9)))) / len(c) if feas else -np.inf
        res.append(CoalitionResult(c, seats(c), us, sur, feas, blockers, nash))
    return res


def formateur_outcome(p: Params, order, results=None):
    """כל מרכיב בתורו בוחר את הקואליציה הישימה הטובה לו. מחזיר (מרכיב, תוצאה) או (None, None)."""
    results = evaluate(p) if results is None else results
    for f in order:
        cands = [r for r in results if r.feasible and f in r.members and f not in ARAB]
        if cands:
            best = max(cands, key=lambda r: (r.utilities[f], r.nash))
            return f, best
    return None, None


def label(c, p: Params | None = None):
    if p is not None:
        gov, ext = _members_split(c, p)
        s = " + ".join(gov)
        if ext:
            s += "  ‖ בתמיכת: " + ", ".join(ext)
        return s
    return " + ".join(c)


@dataclass
class ChickenGame:
    a: str
    b: str
    coalition: tuple         # הקואליציה שעליה נאבקים (כוללת את שתיהן)
    stake: float             # הפרס שעליו נאבקים (ראשות הממשלה / תיקים בכירים)
    payoffs: dict            # (אסטרטגיה של a, אסטרטגיה של b) -> (תשלום a, תשלום b)
    fear: dict               # לכל שחקנית: כמה היא מפסידה בהתנגשות לעומת כניעה (L - E)
    pure_eq: list            # שיווי משקל טהורים
    mixed: dict | None       # הסתברות להתעקש לכל שחקנית בשיווי המשקל המעורב
    p_elections: float       # הסתברות לבחירות חוזרות (התנגשות)
    kind: str                # סוג המשחק
    risk_dominant: tuple | None   # שיווי המשקל הדומיננטי-בסיכון (הרסאניי-זלטן)


SWERVE, STRAIGHT = "מוותרת", "מתעקשת"


def chicken_coalitions(a, b):
    """כל הקואליציות המנצחות המינימליות שכוללות את שתי השחקניות."""
    return [c for c in all_winning_coalitions(min_only=True) if a in c and b in c]


def chicken_game(a, b, p: Params, coalition=None, stake=None) -> ChickenGame:
    """משחק הצ'יקן בין a ל-b על קואליציה משותפת.
    שתיהן יכולות לוותר (להסכים לחלוקה) או להתעקש (לדרוש את הפרס כולו).
      שתיהן מוותרות -> חלוקה שווה של הפרס (רוטציה).
      אחת מתעקשת     -> המתעקשת לוקחת את כל הפרס.
      שתיהן מתעקשות  -> פלונטר ובחירות חוזרות: כל אחת מקבלת את ערך החוץ שלה.
    התועלת הבסיסית מהקואליציה מחושבת בלי פרמיית ראשות הממשלה, כי הפרמיה היא הפרס."""
    stake = p.pm_premium if stake is None else stake
    q = replace(p, pm_premium=0.0)
    M = penalty_matrix(q)
    E = {i: outside_option(i, p) for i in (a, b)}
    if coalition is None:
        cands = chicken_coalitions(a, b)
        coalition = max(cands, key=lambda c: min(utility(i, c, q, M) - E[i] for i in (a, b)))
    U = {i: utility(i, coalition, q, M) for i in (a, b)}
    W = {i: U[i] + stake for i in (a, b)}
    C = {i: U[i] + stake / 2 for i in (a, b)}
    L = U
    pay = {(SWERVE, SWERVE): (C[a], C[b]), (SWERVE, STRAIGHT): (L[a], W[b]),
           (STRAIGHT, SWERVE): (W[a], L[b]), (STRAIGHT, STRAIGHT): (E[a], E[b])}
    fear = {i: L[i] - E[i] for i in (a, b)}

    strats = (SWERVE, STRAIGHT)
    other = {SWERVE: STRAIGHT, STRAIGHT: SWERVE}
    pure = [(x, y) for x in strats for y in strats
            if pay[(x, y)][0] >= pay[(other[x], y)][0] - 1e-12
            and pay[(x, y)][1] >= pay[(x, other[y])][1] - 1e-12]

    mixed, risk_dom = None, None
    half = stake / 2
    if fear[a] > 0 and fear[b] > 0 and half > 0:
        kind = "צ'יקן"
        # כל שחקנית מתעקשת בהסתברות שמשאירה את היריבה אדישה
        mixed = {a: half / (half + fear[b]), b: half / (half + fear[a])}
        p_el = mixed[a] * mixed[b]
        # הרסאניי-זלטן: שיווי המשקל שבו מכפלת הפסדי הסטייה גדולה יותר
        a_wins = half * fear[b]
        b_wins = half * fear[a]
        risk_dom = (STRAIGHT, SWERVE) if a_wins > b_wins else (SWERVE, STRAIGHT)
    elif fear[a] > 0 and fear[b] > 0:
        kind = "אין על מה להילחם"
        p_el = 0.0
    elif fear[a] <= 0 and fear[b] <= 0:
        kind = "התנגשות ודאית"
        p_el = 1.0
    else:
        bold = a if fear[a] <= 0 else b
        kind = f"{bold} לא חוששת מבחירות"
        p_el = 0.0
    return ChickenGame(a, b, coalition, stake, pay, fear, pure, mixed, p_el, kind, risk_dom)


@dataclass
class CorrelatedEq:
    probs: dict              # (אסטרטגיה של a, אסטרטגיה של b) -> הסתברות שהמתווך ימליץ על התא
    payoffs: tuple           # התשלום הצפוי לכל שחקנית כשהיא מצייתת להמלצה
    p_elections: float       # הסתברות להתנגשות בשיווי המשקל שנבחר
    p_el_range: tuple        # טווח ההסתברות לבחירות על פני כל שיוויי המשקל המתואמים
    mixed_payoffs: tuple | None   # התשלום הצפוי בשיווי המשקל המעורב, להשוואה


def correlated_equilibrium(g: ChickenGame) -> CorrelatedEq:
    """שיווי משקל מתואם (אומן, 1974) במשחק הצ'יקן.
    מתווך מגריל תא (x, y) לפי התפלגות p ולוחש לכל שחקנית רק את ההמלצה שלה.
    p הוא שיווי משקל מתואם אם לאף שחקנית לא כדאי לסטות מההמלצה, בהינתן מה שהיא למדה ממנה:
      Σ_y p(x,y)·[u_a(x,y) − u_a(x',y)] ≥ 0   לכל המלצה x וסטייה x' (וכך גם ל-b).
    הקבוצה היא פוליטופ, ולכן האופטימום של כל מטרה ליניארית מתקבל בקודקוד. בוחרים את שיווי המשקל
    שממקסם את סכום התשלומים, ובשוויון את זה שממליץ הכי הרבה על רוטציה (ויתור הדדי)."""
    strats = (SWERVE, STRAIGHT)
    cells = [(x, y) for x in strats for y in strats]
    other = {SWERVE: STRAIGHT, STRAIGHT: SWERVE}
    rows = []
    for x in strats:   # תנאי ציות של a: הומלץ לה x, שוקלת לסטות ל-x'
        rows.append([(g.payoffs[c][0] - g.payoffs[(other[x], c[1])][0]) if c[0] == x else 0.0 for c in cells])
    for y in strats:   # תנאי ציות של b
        rows.append([(g.payoffs[c][1] - g.payoffs[(c[0], other[y])][1]) if c[1] == y else 0.0 for c in cells])
    rows += np.eye(4).tolist()          # אי-שליליות
    A = np.array(rows)

    verts = []
    for tight in combinations(range(len(A)), 3):
        S = np.vstack([A[list(tight)], np.ones(4)])
        if abs(np.linalg.det(S)) < 1e-12:
            continue
        v = np.linalg.solve(S, np.array([0, 0, 0, 1.0]))
        if (A @ v >= -1e-9).all():
            verts.append(np.clip(v, 0, None))

    pay = np.array([g.payoffs[c] for c in cells])
    welfare = [v @ pay.sum(axis=1) for v in verts]
    top = max(welfare)
    best = max((v for v, w in zip(verts, welfare) if w >= top - 1e-9), key=lambda v: v[0])
    tt = cells.index((STRAIGHT, STRAIGHT))
    p_el = [v[tt] for v in verts]

    mixed_pay = None
    if g.mixed:
        qa, qb = g.mixed[g.a], g.mixed[g.b]
        # בשיווי המשקל המעורב כל שחקנית אדישה, ולכן התשלום שלה שווה לתשלום מוויתור
        mixed_pay = ((1 - qb) * g.payoffs[(SWERVE, SWERVE)][0] + qb * g.payoffs[(SWERVE, STRAIGHT)][0],
                     (1 - qa) * g.payoffs[(SWERVE, SWERVE)][1] + qa * g.payoffs[(STRAIGHT, SWERVE)][1])
    return CorrelatedEq(dict(zip(cells, best)), tuple(best @ pay), float(best[tt]),
                        (float(min(p_el)), float(max(p_el))), mixed_pay)
