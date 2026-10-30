import streamlit as st

from ui import restore_params, save_params

st.set_page_config(page_title="הפלונטר של הכנסת ה-26", layout="wide")
st.markdown("""<style>
html, body, [class*="css"], .stMarkdown, .stSlider, .stTabs, section[data-testid="stSidebar"] {direction: rtl; text-align: right;}
.stSlider > div {direction: ltr;}
[data-testid="stHeading"], h1, h2, h3, h4 {direction: rtl; text-align: right;}
section[data-testid="stSidebar"] {min-width: 380px;}
</style>""", unsafe_allow_html=True)
st.session_state.setdefault("reset_ver", 0)

page = st.navigation([
    st.Page("views/dashboard.py", title="המודל האינטראקטיבי", icon="🧩", default=True),
    st.Page("views/policy.py", title="מרחב המדיניות", icon="🧭"),
    st.Page("views/redlines.py", title="קווים אדומים", icon="🚫"),
    st.Page("views/elections.py", title="מי חושש מבחירות", icon="🎲"),
    st.Page("views/raw_data.py", title="מידע גולמי", icon="🗂️"),
    st.Page("views/model_doc.py", title="המודל", icon="📖"),
])
restore_params()
page.run()
save_params()
