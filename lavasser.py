import streamlit as st
import xml.etree.ElementTree as ET
import google.generativeai as genai
import plotly.express as px
import pandas as pd
import json
import re

# --- Configuration de la page ---
st.set_page_config(page_title="Assistant BPMN & SAP B1", page_icon="🏭", layout="wide")

# ==========================================
# 🖨️ CSS POUR IMPRESSION PROPRE (CTRL+P) MULTI-PAGES
# ==========================================
st.markdown("""
<style>
@media print {
    /* Forcer Streamlit à dérouler toute la page pour l'impression (Corrige le bug de la page unique) */
    body, html, .stApp, .main, section, div.block-container {
        height: auto !important;
        overflow: visible !important;
        display: block !important;
        position: relative !important;
    }
    /* Masquer les éléments interactifs */
    header, footer, [data-testid="stSidebar"], .stButton, .stFileUploader, .stTextInput {
        display: none !important;
    }
    /* Garder les couleurs du radar et empêcher les tableaux d'être coupés au milieu */
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
CODE_SECRET = "LAVASSER2026"

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
    # 🔑 CLÉ API GOOGLE GEMINI
    # ==========================================
    # Assurez-vous de stocker ceci de manière sécurisée (st.secrets idéalement)
    API_KEY = "AIzaSyBxMH4QiInZA5srBNmRHkUR_5hcQYwx60M" 
    genai.configure(api_key=API_KEY)

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

    def get_best_model():
        """Trouve le meilleur modèle Flash disponible."""
        valid_model_name = 'gemini-1.5-flash' # Valeur par défaut sécurisée
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if '2.5-flash' in m.name: return m.name
                    elif '1.5-flash' in m.name: valid_model_name = m.name
        except:
            pass
        return valid_model_name

    def generate_full_analysis(tasks_text, flows_text):
        """Génère le rapport ET les scores JSON avec le BOUCLIER ANTI-HALLUCINATION."""
        model_name = get_best_model()
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""
        Tu es un assistant expert combinant trois rôles : Analyste BPMN, Expert Industrie 4.0, et Architecte Senior SAP B1 10.0.
        Voici les données du BPMN :
        TÂCHES : {tasks_text}
        SÉQUENCE : {flows_text}

        🛑 RÈGLES ANTI-HALLUCINATION STRICTES (STANDARD SAP B1 10.0) :
        - PRODUCTION : Un processus entier utilise 1 seul Ordre de Fabrication (OWOR). Les étapes intermédiaires (lavage, traitement) sont des Lignes de type "Ressource" (ORSC).
        - MOUVEMENTS : La validation des étapes se fait via "Déclaration de production" (OIGN) ou "Sortie pour production" (OIGE).
        - QUALITÉ : N'EXISTE PAS en standard. Ne JAMAIS citer l'objet OINS. Propose l'utilisation de Champs Utilisateurs (UDF) sur la ligne de l'OF.
        - EXPORT/LIVRAISON : Utilise le document de Livraison (ODLN).
        - TABLES IMPACTÉES : Précise OITW pour le stock, OJDT pour l'écriture au journal.

        Génère un rapport structuré en français avec EXACTEMENT ces parties :

        ### 1. 📊 Tableau Synthétique des Tâches
        Génère un tableau Markdown avec les colonnes : Étape, Processus, Type de Tâche.

        ### 2. 📝 Description Logique du Processus
        Explication claire et chronologique (Au moins 3 paragraphes).

        ### 3. 🔵 Propositions d'Intégration SAP Business One 10.0
        Applique STRICTEMENT les règles anti-hallucination. Rédige sous forme de LISTE à puces :
        * **Tâche BPMN :** [Nom]
          * **Objet & Module SAP B1 :** [Ex: Déclaration de production (OIGN) / Livraison (ODLN)]
          * **Données Maîtres :** [Fiches Articles OITM, Nomenclatures OITT, etc.]
          * **Impact & Proposition :** [Explique précisément l'action sur les stocks et la compta]

        ### 4. 🏭 Évaluation des Tâches selon les 9 Piliers (Industrie 4.0)
        Génère UN SEUL grand tableau Markdown évaluant TOUTES les tâches listées sans exception.
        Colonnes : `Tâche BPMN` | `Big Data` | `Robots` | `Simul` | `Intégr` | `IIoT` | `Cyber` | `Cloud` | `Additif` | `RA` | `Justification`
        Rédige une phrase complète pour la justification.

        ### 5. SCORES_JSON
        À la toute fin, inclut un bloc JSON valide avec la note globale moyenne (1 à 5) du processus pour les 9 piliers. Aucun texte après.
        ```json
        {{
          "Big Data": 2, "Robots Autonomes": 1, "Simulation": 1, "Intégration Systèmes": 3,
          "IIoT": 2, "Cybersécurité": 4, "Cloud Computing": 3, "Fabrication Additive": 1, "Réalité Augmentée": 1
        }}
        ```
        """
        response = model.generate_content(prompt, generation_config={"temperature": 0.1})
        return response.text

    def draw_radar_chart(json_str):
        """Convertit le JSON en graphique Radar pour les 9 piliers."""
        try:
            scores = json.loads(json_str)
            df = pd.DataFrame(dict(r=list(scores.values()), theta=list(scores.keys())))
            fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,5], 
                                title="Indice de Maturité I4.0 (9 Piliers)", markers=True)
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
        st.write("Importez votre processus. 🖨️ *Astuce : Faites (Ctrl+P) pour imprimer un rapport propre une fois généré.*")
        uploaded_file = st.file_uploader("Importez votre fichier .bpmn ou .xml", type=['bpmn', 'xml'])

        if uploaded_file is not None:
            if st.button("Lancer l'évaluation complète", type="primary"):
                with st.spinner("Analyse et génération du radar en cours avec Google Gemini..."):
                    tasks_text, flows_text = parse_bpmn_from_file(uploaded_file)
                    
                    if tasks_text is None:
                        st.error(flows_text)
                    else:
                        st.session_state.bpmn_context = f"TÂCHES:\n{tasks_text}\n\nFLUX:\n{flows_text}"
                        try:
                            report = generate_full_analysis(tasks_text, flows_text)
                            
                            json_match = re.search(r'```json\n(.*?)\n```', report, re.DOTALL)
                            clean_report = re.sub(r'### 5\. SCORES_JSON.*', '', report, flags=re.DOTALL)
                            
                            st.success("Analyse générée avec l'expertise stricte SAP B1 10.0 !")
                            
                            col_text, col_radar = st.columns([2, 1])
                            
                            with col_text:
                                st.markdown(clean_report)
                                
                            with col_radar:
                                if json_match:
                                    json_data = json_match.group(1)
                                    st.subheader("📊 Scores Globaux")
                                    try:
                                        scores_dict = json.loads(json_data)
                                        df_scores = pd.DataFrame(list(scores_dict.items()), columns=['Pilier 4.0', 'Note globale'])
                                        st.dataframe(df_scores, hide_index=True, use_container_width=True)
                                    except Exception as e:
                                        pass

                                    fig = draw_radar_chart(json_data)
                                    if fig:
                                        st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.warning("Le graphique radar n'a pas pu être extrait.")
                        except Exception as e:
                            st.error(f"Erreur de l'API Google : {e}")

    with tab2:
        st.header("Discutez avec votre Architecte SAP B1")
        
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if user_prompt := st.chat_input("Posez votre question technique sur SAP B1..."):
            if not st.session_state.bpmn_context:
                st.warning("Veuillez d'abord analyser un fichier BPMN dans l'onglet 'Évaluation & Radar'.")
            else:
                with st.chat_message("user"):
                    st.markdown(user_prompt)
                st.session_state.chat_history.append({"role": "user", "content": user_prompt})
