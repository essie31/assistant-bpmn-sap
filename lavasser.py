import streamlit as st
import xml.etree.ElementTree as ET
from groq import Groq
import plotly.express as px
import pandas as pd
import json
import re
import time

# --- Configuration de la page ---
st.set_page_config(page_title="Assistant BPMN & SAP B1", page_icon="🏭", layout="wide")

# ==========================================
# 🖨️ CSS POUR IMPRESSION PROPRE
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
CODE_SECRET = st.secrets["APP_PASSWORD"]

def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Accès Restreint")
        pwd = st.text_input("Veuillez entrer le code d'accès :", type="password")
        if st.button("Valider"):
            if pwd == CODE_SECRET:
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Code incorrect.")
        return False
    return True

if check_password():
    
    # ==========================================
    # 🔑 INITIALISATION GROQ
    # ==========================================
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
    
    # Llama 3.1 70B est le modèle le plus intelligent chez Groq (équivalent GPT-4)
    MODEL_NAME = "llama-3.3-70b-versatile"

    def parse_bpmn_from_file(file_object):
        try:
            tree = ET.parse(file_object)
            root = tree.getroot()
            ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
            
            lane_map = {}
            for lane in root.findall('.//bpmn:lane', ns):
                name = lane.get('name', 'Général')
                for node_ref in lane.findall('bpmn:flowNodeRef', ns):
                    lane_map[node_ref.text] = name
            
            elements = {}
            tasks = []
            for elem in root.findall('.//bpmn:process/*', ns):
                if 'id' in elem.attrib and 'sequenceFlow' not in elem.tag:
                    e_id = elem.get('id')
                    e_name = elem.get('name', 'Sans nom').strip()
                    lane = lane_map.get(e_id, 'Général')
                    elements[e_id] = e_name
                    if e_name != 'Sans nom':
                        tasks.append(f"- [{lane}] {e_name}")
            
            flows = []
            for flow in root.findall('.//bpmn:sequenceFlow', ns):
                src = elements.get(flow.get('sourceRef'), "Début")
                tgt = elements.get(flow.get('targetRef'), "Fin")
                flows.append(f"{src} -> {tgt}")
                
            return "\n".join(tasks), "\n".join(flows)
        except: return None, None

    # ==========================================
    # 🤖 GÉNÉRATION ÉTAPE 1 : ANALYSE MÉTIER & SAP
    # ==========================================

    def generate_step1(tasks, flows):
        prompt = f"""
        Tu es un Consultant Expert Senior SAP Business One 10.0.
        PROCESSUS :
        {tasks}
        FLUX :
        {flows}

        Produis un rapport de haute qualité :
        ### 1. 📊 Tableau des Tâches
        (Département | Tâche | Type)

        ### 2. 📝 Analyse Logique du Processus
        Rédige une analyse métier approfondie (minimum 4 paragraphes). Explique la circulation de l'information, les goulots d'étranglement potentiels et la structure chronologique.

        ### 3. 🔵 Intégration SAP Business One 10.0 (Expertise Senior)
        Pour chaque tâche informatisable, fournis :
        * **[Nom de la tâche]**
          * **Chemin Menu :** [Chemin exact dans SAP B1]
          * **Objet Technique :** [Ex: Commande client (ORDR), Ordre de fabrication (OWOR)]
          * **Données Maîtres :** [Articles, Partenaires, Nomenclature nécessaires]
          * **Impact Système :** [Impact sur les stocks (OITW), les écritures comptables (OJDT) et le flux de production.]
        """
        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": "Tu es un consultant SAP B1 10.0 haut de gamme. Tu es précis, technique et exhaustif."},
                      {"role": "user", "content": prompt}],
            temperature=0.2
        ).choices[0].message.content

    # ==========================================
    # 🤖 GÉNÉRATION ÉTAPE 2 : MATRICE 4.0
    # ==========================================

    def generate_step2(tasks):
        prompt = f"""
        En tant qu'expert Industrie 4.0, évalue chaque tâche suivante :
        {tasks}

        Génère UN SEUL grand tableau Markdown exhaustif.
        Colonnes : | Tâche BPMN | Big Data | Robots | Simulation | Intégration | IIoT | Cyber | Cloud | Additif | RA | Justification Technique Détaillée |
        
        La justification doit être une analyse sérieuse de 15 mots minimum par ligne.
        """
        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        ).choices[0].message.content

    # --- UI Streamlit ---
    if "s1" not in st.session_state: st.session_state.update({"s1":"", "s2":"", "tasks":"", "flows":""})
    
    file = st.file_uploader("Charger le fichier BPMN", type=['bpmn', 'xml'])
    if file:
        t, f = parse_bpmn_from_file(file)
        st.session_state.tasks, st.session_state.flows = t, f
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("1️⃣ Analyse & Architecture SAP"):
                with st.spinner("Analyse Senior en cours..."):
                    st.session_state.s1 = generate_step1(t, f)
        with c2:
            if st.button("2️⃣ Matrice Industrie 4.0"):
                with st.spinner("Évaluation 4.0 en cours..."):
                    st.session_state.s2 = generate_step2(t)
        with c3:
            if st.button("3️⃣ Graphique Radar"):
                # Génération simplifiée pour le radar pour éviter les erreurs JSON
                res = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role":"user", "content":f"Donne les moyennes 1-5 pour les 9 piliers I4.0 de ce processus : {t}. Réponds uniquement en JSON pur."}],
                    temperature=0
                ).choices[0].message.content
                try:
                    data = json.loads(re.search(r'\{.*\}', res, re.S).group())
                    df = pd.DataFrame(dict(r=list(data.values()), theta=list(data.keys())))
                    st.plotly_chart(px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,5], title="Maturité Industrie 4.0"))
                except: st.error("Erreur de génération du graphique.")

        if st.session_state.s1: st.markdown(st.session_state.s1)
        if st.session_state.s2: st.markdown(st.session_state.s2)
