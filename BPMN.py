import streamlit as st
import xml.etree.ElementTree as ET
import google.generativeai as genai
import plotly.express as px
import pandas as pd
import json
import re

# ==========================================
# ⚙️ CONFIGURATION STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Assistant BPMN & SAP B1",
    page_icon="🏭",
    layout="wide"
)

# ==========================================
# 🔐 AUTHENTIFICATION
# ==========================================
CODE_SECRET = st.secrets["APP_PASSWORD"]

def check_password():
    def password_entered():
        st.session_state["password_correct"] = (
            st.session_state["password"] == CODE_SECRET
        )
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
# 🔑 API GEMINI
# ==========================================
API_KEY = st.secrets["API_KEY"]
genai.configure(api_key=API_KEY)

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
# 🧠 ANALYSE GEMINI (AVEC BOUCLE DE SÉCURITÉ)
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
    
    # La liste des modèles du plus récent au plus ancien (le plus stable)
    modeles_a_tester = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-pro"]
    erreur_log = ""

    # On essaie de se connecter à chaque modèle un par un
    for nom_modele in modeles_a_tester:
        try:
            model = genai.GenerativeModel(nom_modele)
            # C'est l'appel réseau qui plante d'habitude, il est maintenant protégé
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            erreur_log += f"\n- {nom_modele} a échoué: {str(e)}"
            continue # Si ça plante, on passe automatiquement au modèle suivant !

    # Si VRAIMENT aucun des 4 modèles ne marche (très rare) :
    return f"Erreur critique : Impossible de se connecter à l'intelligence artificielle de Google. Détails techniques : {erreur_log}"

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
        with st.spinner("Analyse en cours... (Recherche du meilleur modèle Google disponible)"):
            tasks, flows = parse_bpmn(uploaded)
            report = generate_analysis(tasks, flows)

            # Si le code a retourné l'erreur critique de connexion
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