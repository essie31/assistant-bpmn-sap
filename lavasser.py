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
# 🖨️ CSS POUR IMPRESSION PROPRE (CTRL+P)
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
    table { page-break-inside: auto; width: 100% !important; font-size: 11px; }
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

if check_password():
    
    # ==========================================
    # 🔑 CLÉ API SÉCURISÉE
    # ==========================================
    API_KEY = st.secrets["API_KEY"]
    genai.configure(api_key=API_KEY)

    def parse_bpmn_from_file(file_object):
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
        valid_model_name = 'gemini-pro' 
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'flash' in m.name: return m.name
                    elif 'pro' in m.name: valid_model_name = m.name
        except:
            pass
        return valid_model_name

    # ==========================================
    # 🤖 FONCTIONS DE GÉNÉRATION (LES 3 ÉTAPES)
    # ==========================================

    # --- ÉTAPE 1 : SAP & LOGIQUE ---
    def generate_part1_analysis(tasks_text, flows_text):
        model = genai.GenerativeModel(get_best_model())
        prompt = f"""
        Tu es un assistant expert combinant les rôles d'Analyste BPMN et Consultant SAP B1 10.0.
        Voici les données du processus :
        
        TÂCHES :
        {tasks_text}
        
        SÉQUENCE :
        {flows_text}

        Génère EXACTEMENT ces 3 parties en français :

        ### 1. 📊 Tableau Synthétique des Tâches
        Génère un tableau Markdown avec les colonnes : Étape, Processus, Type de Tâche.

        ### 2. 📝 Description Logique du Processus
        Explication claire et chronologique.

        ### 3. 🔵 Propositions d'Intégration SAP Business One 10.0
        Rédige IMPÉRATIVEMENT sous forme de LISTE. Structure à puces :
        * **Tâche BPMN :** [Nom]
          * **Module SAP B1 :** [Module]
          * **Écran cible :** [Écran]
          * **Chemin de navigation :** [Chemin]
          * **Proposition d'automatisation :** [Détail]
        """
        response = model.generate_content(prompt, generation_config={"temperature": 0.1})
        return response.text

    # --- ÉTAPE 2 : LES 9 TABLEAUX ---
    def generate_part2_evaluation(tasks_text):
        model = genai.GenerativeModel(get_best_model())
        prompt = f"""
        Tu es un Expert Industrie 4.0. Évalue les tâches suivantes :
        {tasks_text}

        Génère EXACTEMENT cette partie en français :

        ### 4. 🏭 Évaluation des Tâches selon les 9 Piliers (Industrie 4.0)
        Génère 9 petits tableaux Markdown, un pour chaque pilier de l'Industrie 4.0 (Big Data, Robots, Simulation, Intégration, IIoT, Cybersécurité, Cloud, Additif, Réalité Augmentée).
        
        RÈGLE ABSOLUE : Tu dois évaluer TOUTES les tâches listées au début du prompt dans CHACUN des 9 tableaux. Ne saute AUCUNE tâche.
        Colonnes du tableau : `Tâche BPMN` | `Score (1-5)` | `Justification`.
        ASTUCE: Rédige des justifications très courtes (3 mots max).
        """
        response = model.generate_content(prompt, generation_config={"temperature": 0.1})
        return response.text

    # --- ÉTAPE 3 : JSON & RADAR ---
    def generate_part3_radar(tasks_text):
        model = genai.GenerativeModel(get_best_model())
        prompt = f"""
        Sur la base de ces tâches :
        {tasks_text}

        Calcule la note globale moyenne de 1 à 5 du processus entier pour les 9 piliers de l'industrie 4.0.
        Génère UNIQUEMENT un bloc JSON valide. Il ne doit y avoir AUCUN texte avant ou après ce bloc.
        
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
        response = model.generate_content(prompt, generation_config={"temperature": 0.1})
        return response.text

    def draw_radar_chart(json_str):
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

    # ==========================================
    # 💾 INITIALISATION DE LA MÉMOIRE (SESSION)
    # ==========================================
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "bpmn_context" not in st.session_state:
        st.session_state.bpmn_context = ""
    if "bpmn_tasks_only" not in st.session_state:
        st.session_state.bpmn_tasks_only = ""
    if "part1_text" not in st.session_state:
        st.session_state.part1_text = ""
    if "part2_text" not in st.session_state:
        st.session_state.part2_text = ""
    if "part3_text" not in st.session_state:
        st.session_state.part3_text = ""

    st.title("💡 Hub d'Intégration : BPMN ➔ SAP Business One 10.0")

    tab1, tab2 = st.tabs(["📊 Évaluation en 3 Étapes", "💬 Assistant SAP"])

    with tab1:
        st.write("Importez votre processus. 🖨️ *Astuce : Faites Ctrl+P pour imprimer un rapport propre.*")
        uploaded_file = st.file_uploader("Importez votre fichier .bpmn ou .xml", type=['bpmn', 'xml'])

        if uploaded_file is not None:
            # Réinitialisation pour un nouveau fichier
            if st.button("🔄 Réinitialiser l'analyse pour un nouveau fichier"):
                st.session_state.part1_text = ""
                st.session_state.part2_text = ""
                st.session_state.part3_text = ""
                st.rerun()

            # Extraction des données si ce n'est pas déjà fait
            if not st.session_state.bpmn_context:
                tasks_text, flows_text = parse_bpmn_from_file(uploaded_file)
                if tasks_text is None:
                    st.error(flows_text)
                else:
                    st.session_state.bpmn_context = f"TÂCHES:\n{tasks_text}\n\nFLUX:\n{flows_text}"
                    st.session_state.bpmn_tasks_only = tasks_text

            st.divider()
            
            # --- AFFICHAGE DES 3 BOUTONS EN COLONNES ---
            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                if st.button("1️⃣ Analyse Métier & SAP", use_container_width=True):
                    with st.spinner("Analyse métier et SAP en cours..."):
                        try:
                            st.session_state.part1_text = generate_part1_analysis(st.session_state.bpmn_tasks_only, st.session_state.bpmn_context)
                        except Exception as e:
                            st.error(f"🔴 Erreur IA (Étape 1) : {e}")

            with col_btn2:
                if st.button("2️⃣ Les 9 Tableaux de Scoring", use_container_width=True):
                    with st.spinner("Création des 9 tableaux d'évaluation..."):
                        try:
                            st.session_state.part2_text = generate_part2_evaluation(st.session_state.bpmn_tasks_only)
                        except Exception as e:
                            st.error(f"🔴 Erreur IA (Étape 2) : {e}")

            with col_btn3:
                if st.button("3️⃣ Résultats Globaux & Radar", use_container_width=True):
                    with st.spinner("Calcul des notes finales et du Radar..."):
                        try:
                            st.session_state.part3_text = generate_part3_radar(st.session_state.bpmn_tasks_only)
                        except Exception as e:
                            st.error(f"🔴 Erreur IA (Étape 3) : {e}")

            st.divider()

            # --- AFFICHAGE DES RÉSULTATS ---
            if st.session_state.part1_text:
                st.markdown(st.session_state.part1_text)
                st.divider()

            if st.session_state.part2_text:
                st.markdown(st.session_state.part2_text)
                st.divider()

            if st.session_state.part3_text:
                st.subheader("📊 Scores Globaux (9 Piliers)")
                report_part3 = st.session_state.part3_text
                json_match = re.search(r'```json\n(.*?)\n```', report_part3, re.DOTALL)
                
                if json_match:
                    json_data = json_match.group(1)
                    
                    col_vide1, col_centre, col_vide2 = st.columns([1, 2, 1])
                    with col_centre:
                        try:
                            scores_dict = json.loads(json_data)
                            df_scores = pd.DataFrame(list(scores_dict.items()), columns=['Pilier 4.0', 'Note globale'])
                            st.dataframe(df_scores, hide_index=True, use_container_width=True)
                        except Exception as e:
                            st.error(f"Erreur d'affichage du tableau : {e}")

                        fig = draw_radar_chart(json_data)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Le graphique radar n'a pas pu être généré. Format JSON introuvable.")

    # ==========================================
    # 💬 ONGLETS 2 : LE CHAT EXPERT SÉCURISÉ
    # ==========================================
    with tab2:
        st.header("Discutez avec votre Consultant SAP B1")
        
        # Affichage de l'historique
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Zone de saisie
        if user_prompt := st.chat_input("Posez votre question sur SAP B1..."):
            if not st.session_state.bpmn_context:
                st.warning("Veuillez d'abord importer un fichier dans le premier onglet.")
            else:
                with st.chat_message("user"):
                    st.markdown(user_prompt)
                
                # Sauvegarde de la question de l'utilisateur
                st.session_state.chat_history.append({"role": "user", "content": user_prompt})

                # Bouclier anti-hallucinations SAP B1
                chat_context = f"""
                Tu es un consultant expert SAP Business One 10.0. L'utilisateur te pose une question sur son processus métier.
                
                RÈGLE N°1 : Tes réponses doivent s'appliquer STRICTEMENT ET UNIQUEMENT à SAP Business One 10.0. Ne donne jamais de chemins de menus provenant de SAP S/4HANA ou SAP ECC.
                RÈGLE N°2 : Si tu n'es pas absolument certain du chemin exact du menu dans SAP B1, ou si la fonctionnalité n'existe pas en standard, TU DOIS dire 'Je ne suis pas certain' ou 'Cette fonction n'existe pas en standard'.
                
                Voici les données de son processus actuel :
                {st.session_state.bpmn_context}
                
                Réponds de manière technique et directement applicable dans SAP B1 10.0.
                Question : {user_prompt}
                """

                with st.chat_message("assistant"):
                    with st.spinner("Réflexion..."):
                        try:
                            model_name = get_best_model()
                            model = genai.GenerativeModel(model_name)
                            # Température basse pour un chat factuel
                            response = model.generate_content(
                                chat_context,
                                generation_config={"temperature": 0.1}
                            )
                            st.markdown(response.text)
                            # Sauvegarde de la réponse de l'IA
                            st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                        except Exception as e:
                            st.error(f"🔴 Erreur de l'API Google : {e}")
