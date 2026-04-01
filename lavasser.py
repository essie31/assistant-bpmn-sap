import streamlit as st
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types 
import plotly.express as px
import pandas as pd
import json
import re

# --- Configuration de la page ---
st.set_page_config(page_title="App 1 : Analyse & Architecture SAP", page_icon="📊", layout="wide")

# ==========================================
# 🖨️ CSS POUR IMPRESSION (CTRL+P)
# ==========================================
st.markdown("""
<style>
@media print {
    body, html, .stApp, .main, section, div.block-container { height: auto !important; overflow: visible !important; display: block !important; position: relative !important; }
    header, footer, [data-testid="stSidebar"], .stButton, .stFileUploader, .stTextInput { display: none !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    table { page-break-inside: auto; width: 100% !important; font-size: 11px; }
    tr { page-break-inside: avoid; page-break-after: auto; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SYSTÈME DE SÉCURITÉ
# ==========================================
if "password_correct" not in st.session_state:
    st.title("🔒 Accès Restreint")
    pwd = st.text_input("Veuillez entrer le code d'accès :", type="password")
    if st.button("Valider"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Code d'accès incorrect.")
    st.stop()

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.title("🚀 Navigation")
    st.info("Ceci est l'Application 1 (Architecture & Maturité)")
    st.link_button("💬 Aller vers l'App 2 (Assistant Chat)", "https://votre-app-chat.streamlit.app")

# ==========================================
# 🔑 CONFIGURATION GOOGLE (RETOUR AU 2.5 FLASH)
# ==========================================
API_KEY = st.secrets["API_KEY"] 
client = genai.Client(api_key=API_KEY)

# VOTRE modèle qui fonctionnait depuis le début
MODEL_NAME = 'gemini-2.5-flash'

def parse_bpmn_from_file(file_object):
    try:
        tree = ET.parse(file_object)
        root = tree.getroot()
        ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        lane_map = {node_ref.text: lane.get('name', 'Général') 
                    for lane in root.findall('.//bpmn:lane', ns) 
                    for node_ref in lane.findall('bpmn:flowNodeRef', ns)}
        
        tasks, flows, elements = [], [], {}
        for elem in root.findall('.//bpmn:process/*', ns):
            if 'id' in elem.attrib and 'sequenceFlow' not in elem.tag:
                e_id, e_name = elem.get('id'), elem.get('name', 'Sans nom').strip()
                lane = lane_map.get(e_id, 'Général')
                elements[e_id] = {'name': e_name}
                if e_name != 'Sans nom':
                    tasks.append(f"- [{lane}] {e_name}")

        for flow in root.findall('.//bpmn:sequenceFlow', ns):
            src, tgt = flow.get('sourceRef'), flow.get('targetRef')
            if src in elements and tgt in elements:
                flows.append(f"'{elements[src]['name']}' ➔ '{elements[tgt]['name']}'")
        return "\n".join(tasks), "\n".join(flows)
    except Exception as e: 
        return None, None

def generate_full_report(tasks, flows):
    prompt = f"""
    Tu es un Architecte Senior SAP Business One 10.0 et Expert Industrie 4.0.
    TÂCHES : {tasks}
    FLUX : {flows}

    Génère un rapport EXHAUSTIF avec exactement ces 4 sections :

    ### 1. 📊 Tableau Synthétique
    Département | Tâche BPMN

    ### 2. 📝 Analyse Logique & Métier
    Rédige au moins 3 paragraphes détaillés sur le flux de ce processus industriel.

    ### 3. 🔵 Architecture SAP Business One 10.0 (Détails Experts)
    Pour chaque tâche informatisable, fournis :
    * **Tâche :** [Nom]
    * **Objet SAP & Menu :** [Ex: Étape de route OWOR, Déclaration OIGN, Livraison ODLN]
    * **Impact Transactionnel :** [Action exacte à mener, et impact sur les tables OITW/OJDT]

    ### 4. 🏭 Matrice Industrie 4.0
    Génère UN SEUL grand tableau Markdown évaluant TOUTES les tâches.
    Colonnes : Tâche | Big Data | Robots | Simul | Intégr | IIoT | Cyber | Cloud | Additif | RA | Justification Détaillée

    ### 5. SCORES_JSON
    Termine par un bloc JSON pur contenant les moyennes (1 à 5) des 9 piliers. NE METS QUE LES PILIERS EN CLÉS.
    ```json
    {{
      "Big Data": 0, "Robots": 0, "Simulation": 0, "Intégration": 0, 
      "IIoT": 0, "Cyber": 0, "Cloud": 0, "Additive": 0, "Réalité Augmentée": 0
    }}
    ```
    """
    response = client.models.generate_content(
        model=MODEL_NAME, 
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=8192)
    )
    return response.text

# ==========================================
# 🏁 UI PRINCIPALE
# ==========================================
st.title("🏭 Hub 1 : Analyse Métier ➔ Architecture SAP B1")
uploaded_file = st.file_uploader("Importer le fichier .bpmn ou .xml", type=['bpmn', 'xml'])

if uploaded_file:
    if st.button("🚀 Lancer l'Analyse Complète", type="primary"):
        with st.spinner("Génération du rapport et du Radar avec Gemini 2.5 Flash..."):
            tasks_txt, flows_txt = parse_bpmn_from_file(uploaded_file)
            
            if tasks_txt:
                try:
                    report = generate_full_report(tasks_txt, flows_txt)
                    
                    # Extraction JSON pour le Radar
                    json_match = re.search(r'```json\n(.*?)\n```', report, re.DOTALL)
                    clean_report = re.sub(r'### 5\. SCORES_JSON.*', '', report, flags=re.DOTALL)
                    
                    col_text, col_radar = st.columns([2, 1])
                    
                    with col_text:
                        st.success("Analyse terminée ! Utilisez Ctrl+P pour imprimer.")
                        st.markdown(clean_report)
                    
                    with col_radar:
                        if json_match:
                            st.subheader("📈 Maturité Globale I4.0")
                            try:
                                scores = json.loads(json_match.group(1))
                                df = pd.DataFrame(dict(r=list(scores.values()), theta=list(scores.keys())))
                                fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,5])
                                fig.update_traces(fill='toself', line_color='#ff7f0e')
                                st.plotly_chart(fig, use_container_width=True)
                                st.dataframe(pd.DataFrame(list(scores.items()), columns=['Pilier', 'Note']), hide_index=True)
                            except Exception as e:
                                st.error("Erreur de formatage du radar.")
                except Exception as e:
                    st.error(f
