import streamlit as st
import xml.etree.ElementTree as ET
import google.generativeai as genai
import plotly.express as px
import pandas as pd
import json
import re

# --- Configuration de la page (Doit TOUJOURS être la première commande) ---
st.set_page_config(page_title="Assistant BPMN & SAP B1", page_icon="🏭", layout="wide")

# ==========================================
# 🖨️ CSS POUR IMPRESSION PROPRE (CTRL+P) MULTI-PAGES
# ==========================================
st.markdown("""
<style>
@media print {
    body, html, .stApp, .main, section, div.block-container {
        height: auto !important;
        overflow: visible !important;
        display: block !important;
        position: relative !important;
    }
    header, footer, [data-testid="stSidebar"], .stButton, .stFileUploader, .stTextInput {
        display: none !important;
    }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    table { page-break-inside: auto; width: 100% !important; }
    tr { page-break-inside: avoid; page-break-after: auto; }
    h2, h3 { page-break-after: avoid; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SYSTÈME DE SÉCURITÉ (LOGIN)
# ==========================================
CODE_SECRET = st.secrets["APP_PASSWORD"]

def check_password():
    """Retourne True si l'utilisateur a entré le bon code."""
    def password_entered():
        if st.session_state["password"] == CODE_SECRET:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Accès Restreint")
        st.text_input("Veuillez entrer le code d'accès :", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Accès Restreint")
        st.text_input("Veuillez entrer le code d'accès :", type="password", on_change=password_entered, key="password")
        st.error("😕 Code d'accès incorrect.")
        return False
    else:
        return True

# --- SI LE MOT DE PASSE EST BON, ON LANCE L'APPLICATION ---
if check_password():
    
    # ==========================================
    # 🔑 CLÉ API SÉCURISÉE
    # ==========================================
    API_KEY = st.secrets["API_KEY"]

    def parse_bpmn_from_file(file_object):
        """Extrait les éléments et les flux localement."""
        try:
            tree = ET.parse(file_object)
            root = tree.getroot()
        except Exception as e:
            return None, f"Erreur de lecture BPMN : {e}"

        ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        lane_map = {}
        for lane in root.findall('.//bpmn:lane', ns):
            lane_name = lane.get('name', 'Général')
            for node_ref in lane.findall('bpmn:flowNodeRef', ns):
                lane_map[node_ref.text] = lane_name

        elements = {}
        tasks_list = []
        for elem in root.findall('.//bpmn:process/*', ns):
            if 'id' in elem.attrib and 'sequenceFlow' not in elem.tag:
                elem_id = elem.get('id')
                elem_name = elem.get('name', 'Sans nom').strip()
                elem_type = elem.tag.split('}')[-1] 
                lane_name = lane_map.get(elem_id, 'Général')
                elements[elem_id] = {'name': elem_name, 'type': elem_type, 'lane': lane_name}
                if elem_name != 'Sans nom':
                    tasks_list.append(f"- Étape: {lane_name} | Processus: {elem_name} | Type: {elem_type}")

        flows = []
        for flow in root.findall('.//bpmn:sequenceFlow', ns):
            source = flow.get('sourceRef')
            target = flow.get('targetRef')
            condition = flow.get('name', '') 
            if source in elements and target in elements:
                s_elem = elements[source]
                t_elem = elements[target]
                flow_desc = f"De [{s_elem['lane']}] '{s_elem['name']}' ({s_elem['type']}) -> Vers [{t_elem['lane']}] '{t_elem['name']}' ({t_elem['type']})"
                if condition:
                    flow_desc += f" [Condition: {condition}]"
                flows.append(flow_desc)
                
        return "\n".join(tasks_list), "\n".join(flows)

    def generate_full_analysis(tasks_text, flows_text):
        """Génère le rapport ET les scores JSON pour les 9 piliers."""
        genai.configure(api_key=API_KEY)
        
        # UTILISATION DU NOM OFFICIEL ACTUEL POUR ÉVITER L'ERREUR 404
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Tu es un assistant expert combinant trois rôles : Analyste BPMN, Expert Industrie 4.0, et Consultant SAP B1 10.0.
        Voici les données du BPMN :
        
        TÂCHES :
        {tasks_text}
        
        SÉQUENCE :
        {flows_text}

        Génère un rapport structuré en français avec EXACTEMENT ces parties :

        ### 1. 📊 Tableau Synthétique des Tâches
        Génère un tableau Markdown avec les colonnes : Étape, Processus, Type de Tâche.

        ### 2. 📝 Description Logique du Processus
        Explication claire et chronologique.

        ### 3. 🔵 Propositions d'Intégration SAP Business One 10.0
        Rédige IMPÉRATIVEMENT sous forme de LISTE (PAS DE TABLEAU). Structure à puces :
        * **Tâche BPMN :** [Nom]
          * **Module SAP B1 :** [Module]
          * **Écran cible :** [Écran]
          * **Chemin de navigation :** [Chemin]
          * **Proposition d'automatisation :** [Détail]

        ### 4. 🏭 Évaluation des Tâches selon les 9 Piliers (Industrie 4.0)
        Génère 9 petits tableaux Markdown, un pour chaque pilier de l'Industrie 4.0 : 
        (1. Big Data/Analytics, 2. Robots Autonomes, 3. Simulation, 4. Intégration Systèmes, 5. IIoT, 6. Cybersécurité, 7. Cloud, 8. Fabrication Additive, 9. Réalité Augmentée).
        ATTENTION EXTRÊME : Pour CHACUN des 9 tableaux, tu dois IMPÉRATIVEMENT évaluer TOUTES les tâches listées au début du prompt. Interdiction de résumer ou de regrouper.
        Colonnes du tableau : `Tâche BPMN` | `Score (1-5)` | `Justification`.
        ASTUCE: Rédige des justifications très courtes (3-4 mots) pour économiser l'espace.

        ### 5. SCORES_JSON
        À la toute fin, inclut un bloc JSON valide avec la note globale de 1 à 5 du processus entier pour les 9 piliers. Il ne doit y avoir aucun texte après ce bloc.
        ```json
        {{
          "Big Data": 2,
          "Robots Autonomes": 1,
          "Simulation": 1,
          "Intégration Systèmes": 3,
          "IIoT": 2,
          "Cybersécurité": 4,
          "Cloud": 3,
          "Fabrication Additive": 1,
          "Réalité Augmentée": 1
        }}
        ```
        """
        
        # ON LUI OUVRE LA MÉMOIRE AU MAXIMUM POUR QU'IL PUISSE FINIR LES 9 TABLEAUX
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.1
            )
        )
        return response.text

    def draw_radar_chart(json_str):
        """Convertit le JSON en graphique Radar pour les 9 piliers."""
        try:
            scores = json.loads(json_str)
            df = pd.DataFrame(dict(
                r=list(scores.values()),
                theta=list(scores.keys())
            ))
            fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,5], 
                                title="Indice de Maturité I4.0 (9 Piliers)",
                                markers=True)
            fig.update_traces(fill='toself', line_color='#ff7f0e') 
            return fig
        except Exception as e:
            return None

    # --- INITIALISATION DE LA MÉMOIRE DU CHAT ---
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "bpmn_context" not in st.session_state:
        st.session_state.bpmn_context = ""

    st.title("💡 Hub d'Intégration : BPMN ➔ SAP Business One 10.0")

    tab1, tab2 = st.tabs(["📊 Évaluation & Radar", "💬 Assistant Configuration SAP"])

    with tab1:
        st.write("Importez votre processus. 🖨️ *Astuce : Faites Ctrl+P pour imprimer un rapport propre une fois généré.*")
