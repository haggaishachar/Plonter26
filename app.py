import streamlit as st

from ui import restore_params, save_params

st.set_page_config(page_title="הפלונטר של הכנסת ה-26", layout="wide")
st.markdown("""<style>
html, body, [class*="css"], .stMarkdown, .stSlider, .stTabs, section[data-testid="stSidebar"] {direction: rtl; text-align: right;}
/* Plotly מודד טקסט באלמנט נסתר תחת body. ב-RTL המדידה שגויה והתוויות נחתכות */
.stSlider > div, .js-plotly-plot, #js-plotly-tester {direction: ltr;}
[data-testid="stHeading"], h1, h2, h3, h4 {direction: rtl; text-align: right;}
.block-container {padding-top: 2rem;}
/* ה-RTL מוציא את תוכן הסרגל המקופל מחוץ לקופסה שלו, ופס ממנו נשאר מעל התוכן */
/* גרסאות שונות של Streamlit מסמנות סרגל מקופל באחת משתי התכונות */
section[data-testid="stSidebar"]:is([aria-expanded="false"], [data-collapsed="true"]),
section[data-testid="stSidebar"]:is([aria-expanded="false"], [data-collapsed="true"]) * {visibility: hidden !important;}
/* הרוחב המוגדל רק במסך רחב: בטלפון הוא שובר את ההסתרה של הסרגל ומשאיר רצועה מעל התוכן */
@media (min-width: 768px) {section[data-testid="stSidebar"] {min-width: 380px;}}
@media (max-width: 640px) {
  .block-container {padding-top: 1rem;}
  h1 {font-size: 1.75rem !important;}
  .stAlert h3 {font-size: 1.15rem !important;}
  .modebar-container {display: none;}
}
</style>""", unsafe_allow_html=True)
st.session_state.setdefault("reset_ver", 0)

page = st.navigation({
    "": [st.Page("views/forecast.py", title="המודל האינטראקטיבי", icon="🧩", default=True),
         st.Page("views/model_doc.py", title="המודל", icon="📖")],
    "ניתוחים": [
        st.Page("views/policy.py", title="מרחב המדיניות", icon="🧭"),
        st.Page("views/redlines.py", title="קווים אדומים", icon="🚫"),
        st.Page("views/elections.py", title="מי חושש מבחירות", icon="🎲"),
        st.Page("views/raw_data.py", title="מידע גולמי", icon="🗂️"),
    ],
})
restore_params()
page.run()
save_params()
