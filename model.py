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

from dataclasses import dataclass, field
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
    momentum: dict = field(default_factory=dict)   # שינוי צפוי בכוח בבחירות חוזרות לכל מפלגה
    hardness: dict = field(default_factory=dict)   # קשיחות כל קבוצת קווים אדומים (0-3)
    arab_external: bool = True         # מפלגות ערביות כתומכות מבחוץ (בלי תיקים)
    external_discount: float = 0.5     # כמה תמיכה מבחוץ מקטינה קווים אדומים כלפיהן
    arab_budget: float = 0.35          # הישגים תקציביים לתומכת חיצונית
    transfer_eff: float = 0.0          # יעילות העברות (תיקים/תקציבים) בין שותפות: 0 = אין, 1 = מלאה
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


INCUMBENT = "הליכוד"   # מפלגת ראש הממשלה, שממשיכה לכהן בממשלת מעבר עד שתקום ממשלה


def outside_option(i, p: Params) -> float:
    e = p.base_outside + p.momentum.get(i, 0.0) - p.election_cost
    if i == INCUMBENT:
        e += p.caretaker
    return e


@dataclass
class CoalitionResult:
    members: tuple
    seats: int
    utilities: dict          # תועלת לפני העברות
    surplus: dict            # תועלת מעל ערך החוץ, לפני העברות
    feasible: bool
    blockers: list           # מפלגות שמעדיפות בחירות לפני העברות
    nash: float
    transfers: dict          # העברה לכל מפלגה: חיובי = מקבלת, שלילי = משלמת
    final_surplus: dict      # עודף אחרי העברות
    gap: float               # הפער שנותר אחרי שמנצלים את כל ההעברות האפשריות (0 = ישימה)


def settle_transfers(sur: dict, eff: float):
    """המרוויחות משלמות למפסידות, באופן יחסי לרווח שלהן.
    כל יחידה שמשולמת מגיעה למקבלת בשיעור eff (השאר הולך לאיבוד בדרך).
    מחזיר (העברות, עודף סופי, פער שנותר)."""
    deficit = sum(-v for v in sur.values() if v < 0)
    gain = sum(v for v in sur.values() if v > 0)
    if deficit == 0:
        return dict.fromkeys(sur, 0.0), dict(sur), 0.0
    capacity = eff * gain
    if capacity + 1e-12 < deficit:
        return dict.fromkeys(sur, 0.0), dict(sur), deficit - capacity
    paid = deficit / eff
    transfers = {i: (-v if v < 0 else -paid * v / gain) for i, v in sur.items()}
    final = {i: sur[i] + transfers[i] for i in sur}
    return transfers, final, 0.0


def evaluate(p: Params, min_only=True):
    M = penalty_matrix(p)
    res = []
    for c in all_winning_coalitions(min_only=min_only):
        us = {i: utility(i, c, p, M) for i in c}
        sur = {i: us[i] - outside_option(i, p) for i in c}
        blockers = [i for i in c if sur[i] < 0]
        transfers, final, gap = settle_transfers(sur, p.transfer_eff)
        feas = gap == 0
        # מפלגה שפוצתה בדיוק עד לערך החוץ מקבלת רצפה קטנה, כדי שהקואליציה תדורג נמוך (שבירה) ולא תיפסל
        nash = float(np.mean(np.log(np.maximum(list(final.values()), 1e-2)))) if feas else -np.inf
        res.append(CoalitionResult(c, seats(c), us, sur, feas, blockers, nash, transfers, final, gap))
    return res


def formateur_outcome(p: Params, order, results=None):
    """כל מרכיב בתורו בוחר את הקואליציה הישימה הטובה לו. מחזיר (מרכיב, תוצאה) או (None, None)."""
    results = evaluate(p) if results is None else results
    for f in order:
        cands = [r for r in results if r.feasible and f in r.members and f not in ARAB]
        if cands:
            best = max(cands, key=lambda r: (r.final_surplus[f], r.nash))
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
