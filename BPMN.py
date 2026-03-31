import streamlit as st
import xml.etree.ElementTree as ET
from google import genai
import plotly.express as px
import pandas as pd
import json
import re

# ==========================================
# ⚙️ CONFIGURATION STREAMLIT
# ==========================================
st.set_page_config(page_title="Assistant BPMN & SAP B1", page_icon="🏭", layout="wide")

# ==========================================
# 🔐 AUTHENTIFICATION
# ==========================================
CODE_SECRET = st.secrets["APP_PASSWORD"]

def check_password():
    def password_entered():
        st.session_state["password_correct"] = (st.session_state["password"] == CODE_SECRET)
        del st.session_state["password"]

    if "password_correct" not in st.session_state:
        st.title("🔒 Accès Restreint")
        st.text_input("Code d'accès", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.error("Code incorrect")
        return False
    return True

# ==========================================
# 🔑 API GEMINI (NOUVEAU CLIENT 2026)
# ==========================================
API_KEY = st.secrets["API_KEY"]
client = genai.Client(api_key=API_KEY)

# ==========================================
# 📂 BPMN PARSER
# ==========================================
def parse_bpmn(file):
    tree = ET.parse(file)
    root = tree.getroot()
    ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}

    lane_map = {}
    for lane in root.findall('.//bpmn:lane', ns):
        for ref in lane.findall('bpmn:flowNodeRef', ns):
            lane_map[ref.text] = lane.get('name', 'Général')

    tasks, flows = [], []
    elements = {}

    for elem in root.findall('.//bpmn:process/*', ns):
        if 'id' in elem.attrib and 'sequenceFlow' not in elem.tag:
            eid = elem.get('id')
            name = elem.get('name', 'Sans nom')
            etype = elem.tag.split('}')[-1]
            lane = lane_map.get(eid, 'Général')
            elements[eid] = (name, etype, lane)
            if name != 'Sans nom':
                tasks.append(f"- {lane} | {name} | {etype}")

    for flow in root.findall('.//bpmn:sequenceFlow', ns):
        s, t = flow.get('sourceRef'), flow.get('targetRef')
        if s in elements and t in elements:
            flows.append(f"{elements[s][0]} ➜ {elements[t][0]}")

    return "\n".join(tasks), "\n".join(flows)

# ==========================================
# 🧠 ANALYSE GEMINI (AVEC LE BON MODÈLE)
# ==========================================
def generate_analysis(tasks, flows):
    prompt = f"""
Tu es expert BPMN, Industrie 4.0 et SAP Business One 10.0.

TÂCHES :
{tasks}

FLUX :
{flows}

Génère :
1. Tableau synthétique
2. Description logique
3. Intégration SAP B1 (liste structurée)
4. 9 tableaux Industrie 4.0
5. JSON final des scores globaux
"""
    try:
        # ON UTILISE ENFIN UN MODÈLE QUI EXISTE SUR VOTRE COMPTE !
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Erreur critique avec l'API Google : {str(e)}"

# ==========================================
# 📊 RADAR
# ==========================================
def radar(json_str):
    try:
        scores = json.loads(json_str)
        df = pd.DataFrame(dict(r=list(scores.values()), theta=list(scores.keys())))
        fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,5])
        fig.update_traces(fill='toself')
        return fig
    except:
        return None

# ==========================================
# 🚀 APPLICATION
# ==========================================
if check_password():

    st.title("🏭 BPMN ➜ SAP Business One 10.0")

    uploaded = st.file_uploader("Importer BPMN", type=["bpmn", "xml"])

    if uploaded and st.button("Analyser"):
        with st.spinner("Analyse en cours avec Gemini 2.5 Flash..."):
            tasks, flows = parse_bpmn(uploaded)
            report = generate_analysis(tasks, flows)

            if "Erreur critique" in report:
                st.error(report)
            else:
                json_match = re.search(r'```json\n(.*?)\n```', report, re.DOTALL)
                clean = re.sub(r'```json.*', '', report, flags=re.DOTALL)

                st.markdown(clean)

                if json_match:
                    fig = radar(json_match.group(1))
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
