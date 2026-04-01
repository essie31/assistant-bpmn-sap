import streamlit as st
import xml.etree.ElementTree as ET
from groq import Groq
import plotly.express as px
import pandas as pd
import json
import re

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
    return True

if check_password():
    
    # ==========================================
    # 🔑 INITIALISATION GROQ API
    # ==========================================
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
    
    # Le modèle Llama 3.1 8B : Ultra-rapide et permet de rester sous la limite TPM.
    MODEL_NAME = "llama-3.1-8b-instant"

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
                    # Format compressé pour économiser les tokens envoyés à Groq
                    tasks_list.append(f"- [{lane_name}] {elem_name}")
        
        flows = []
        for flow in root.findall('.//bpmn:sequenceFlow', ns):
            source = flow.get('sourceRef')
            target = flow.get('targetRef')
            condition = flow.get('name', '') 
            if source in elements and target in elements:
                s_elem = elements[source]
                t_elem = elements[target]
                flow_desc = f"De '{s_elem['name']}' -> Vers '{t_elem['name']}'"
                if condition: flow_desc += f" [{condition}]"
                flows.append(flow_desc)
                
        return "\n".join(tasks_list), "\n".join(flows)

    # ==========================================
    # 🤖 FONCTIONS DE GÉNÉRATION GROQ
    # ==========================================

    def generate_part1_analysis(tasks_text, flows_text):
        prompt = f"""
        Voici le processus métier à analyser :
        TÂCHES : {tasks_text}
        FLUX : {flows_text}

        Agis comme un Architecte Senior SAP Business One 10.0. Génère un rapport TRÈS DÉTAILLÉ. Zéro hallucination.

        ### 1. 📊 Tableau Synthétique des Tâches
        Dresse un tableau Markdown propre (Département | Tâche).

        ### 2. 📝 Description Logique du Processus
        Rédige au moins 3 à 4 paragraphes complets décrivant le flux de bout en bout, les conditions métier et les dépendances. Je veux des phrases riches et explicatives.

        ### 3. 🔵 Architecture & Intégration SAP Business One 10.0
        RÈGLES :
        1. UNIQUEMENT SAP B1 10.0 standard.
        2. Ignore les tâches physiques (ex: couper le tissu). 
        3. Si la fonction n'existe pas, écris : "⚠️ Nécessite un Champ Utilisateur (UDF)".

        Pour CHAQUE tâche informatisable, sois très technique et détaillé :
        * **[Nom de la tâche]**
          * **Chemin SAP exact :** [Ex: Menu Principal > Ventes > Commande Client]
          * **Écran cible & Données :** [Données de base nécessaires]
          * **Action système détaillée :** [Champs à remplir et impact système (ex: mouvement stock, compta)]
        """
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Tu es un expert SAP B1 rigoureux et très bavard sur les détails techniques."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=3000 # Strictement contrôlé pour passer la limite Groq
        )
        return response.choices[0].message.content

    def generate_part2_evaluation(tasks_text):
        prompt = f"""
        Génère UN SEUL grand tableau Markdown d'évaluation Industrie 4.0 pour TOUTES les tâches suivantes :
        
        {tasks_text}

        RÈGLES IMPÉRATIVES :
        1. Évalue TOUTES les tâches de la liste.
        2. Le tableau DOIT comporter EXACTEMENT 11 colonnes.
        3. Dans la colonne Justification, tu DOIS écrire une phrase complète, détaillée et explicative (au moins 6 mots) pour justifier les scores.

        Format strict du tableau :
        | Tâche BPMN | Big Data | Robots | Simul. | Intégr. | IIoT | Cyber. | Cloud | Additif | RA | Justification Détaillée |
        |---|---|---|---|---|---|---|---|---|---|---|
        | [Nom de la tâche] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [Une vraie phrase complète et technique expliquant pourquoi ces notes ont été attribuées] |

        Renvoie UNIQUEMENT le code Markdown du tableau. Aucun blabla avant ou après.
        """
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Tu es un Expert Industrie 4.0. Tu crées des tableaux Markdown parfaits et tu fais de longues justifications détaillées."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000 # Permet au tableau de se générer entièrement sans crasher le quota
        )
        return response.choices[0].message.content

    def generate_part3_radar(tasks_text):
        prompt = f"""
        Calcule la note globale moyenne (1 à 5) du processus pour les 9 piliers de l'industrie 4.0.
        TÂCHES : {tasks_text}
        
        Tu DOIS renvoyer UNIQUEMENT un objet JSON pur. AUCUN texte autour, aucune explication.
        Exemple :
        {{ "Big Data / Analytics": 2, "Robots Autonomes": 1, "Simulation": 1, "Intégration Systèmes": 3, "IIoT": 2, "Cybersécurité": 4, "Cloud Computing": 3, "Fabrication Additive": 1, "Réalité Augmentée": 1 }}
        """
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Tu es un calculateur qui ne renvoie STRICTEMENT que du JSON valide."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=500
        )
        return response.choices[0].message.content

    def draw_radar_chart(json_str):
        try:
            json_match = re.search(r'\{[\s\S]*\}', json_str)
            if not json_match:
                return None
            scores = json.loads(json_match.group(0))
            df = pd.DataFrame(dict(r=list(scores.values()), theta=list(scores.keys())))
            fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,5], 
                                title="Indice de Maturité I4.0 Global", markers=True)
            fig.update_traces(fill='toself', line_color='#ff7f0e') 
            return fig
        except Exception as e: 
            return None

    # ==========================================
    # 💾 SESSION STATE
    # ==========================================
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "bpmn_tasks_only" not in st.session_state: st.session_state.bpmn_tasks_only = ""
    if "bpmn_flows_only" not in st.session_state: st.session_state.bpmn_flows_only = ""
    
    if "step1_text" not in st.session_state: st.session_state.step1_text = ""
    if "step2_text" not in st.session_state: st.session_state.step2_text = ""
    if "step3_text" not in st.session_state: st.session_state.step3_text = ""

    st.title("💡 Hub d'Intégration : BPMN ➔ SAP Business One 10.0")

    tab1, tab2 = st.tabs(["📊 Évaluation en 3 Étapes", "💬 Assistant SAP"])

    with tab1:
        st.write("Importez votre processus. Propulsé par **Groq Llama 3.1 8B** ⚡.")
        uploaded_file = st.file_uploader("Fichier .bpmn ou .xml", type=['bpmn', 'xml'])

        if uploaded_file is not None:
            if not st.session_state.bpmn_tasks_only:
                tasks_text, flows_text = parse_bpmn_from_file(uploaded_file)
                if tasks_text is None: st.error("Erreur de lecture.")
                else: 
                    st.session_state.bpmn_tasks_only = tasks_text
                    st.session_state.bpmn_flows_only = flows_text

            if st.button("🔄 Réinitialiser l'analyse", type="secondary"):
                st.session_state.step1_text = ""
                st.session_state.step2_text = ""
                st.session_state.step3_text = ""
                st.rerun()

            st.divider()
            
            # --- BOUTONS ---
            col_b1, col_b2, col_b3 = st.columns(3)

            with col_b1:
                if not st.session_state.step1_text:
                    if st.button("1️⃣ Analyse Métier & SAP Détaillée", use_container_width=True, type="primary"):
                        with st.spinner("Rédaction du rapport SAP (très rapide)..."):
                            try:
                                st.session_state.step1_text = generate_part1_analysis(st.session_state.bpmn_tasks_only, st.session_state.bpmn_flows_only)
                                st.rerun()
                            except Exception as e: st.error(f"Erreur Groq : {e}")
                else: st.success("✅ Étape 1 : Terminée")

            with col_b2:
                if not st.session_state.step2_text:
                    if st.button("2️⃣ Matrice d'Évaluation 4.0", use_container_width=True, type="primary"):
                        with st.spinner("Génération du grand tableau avec détails..."):
                            try:
                                st.session_state.step2_text = generate_part2_evaluation(st.session_state.bpmn_tasks_only)
                                st.rerun()
                            except Exception as e: st.error(f"Erreur Groq : {e}")
                else: st.success("✅ Étape 2 : Terminée")

            with col_b3:
                if not st.session_state.step3_text:
                    if st.button("3️⃣ Graphique Radar Final", use_container_width=True, type="primary"):
                        with st.spinner("Calcul des notes..."):
                            try:
                                st.session_state.step3_text = generate_part3_radar(st.session_state.bpmn_tasks_only)
                                st.rerun()
                            except Exception as e: st.error(f"Erreur Groq : {e}")
                else: st.success("✅ Étape 3 : Terminée")

            st.divider()

            # --- RÉSULTATS ---
            if st.session_state.step1_text:
                st.markdown(st.session_state.step1_text)
                st.divider()

            if st.session_state.step2_text:
                st.markdown("### 🏭 Matrice d'Évaluation Complète (Industrie 4.0)")
                st.markdown(st.session_state.step2_text)
                st.divider()

            if st.session_state.step3_text:
                st.subheader("📊 Résultats Globaux")
                report_part3 = st.session_state.step3_text
                
                json_match = re.search(r'\{[\s\S]*\}', report_part3)
                if json_match:
                    json_data = json_match.group(0)
                    col_vide1, col_centre, col_vide2 = st.columns([1, 2, 1])
                    with col_centre:
                        try:
                            scores_dict = json.loads(json_data)
                            df_scores = pd.DataFrame(list(scores_dict.items()), columns=['Pilier 4.0', 'Note moyenne'])
                            st.dataframe(df_scores, hide_index=True, use_container_width=True)
                        except Exception as e: 
                            st.error(f"Erreur d'interprétation du JSON : {e}")

                        fig = draw_radar_chart(json_data)
                        if fig: st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Erreur : Impossible d'extraire les données du Radar.")
                    st.code(report_part3)

    # ==========================================
    # 💬 ONGLET 2 : CHAT SAP
    # ==========================================
    with tab2:
        st.header("Discutez avec votre Consultant SAP B1")
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if user_prompt := st.chat_input("Posez votre question SAP B1..."):
            if not st.session_state.bpmn_tasks_only:
                st.warning("Importez d'abord un fichier.")
            else:
                with st.chat_message("user"): st.markdown(user_prompt)
                st.session_state.chat_history.append({"role": "user", "content": user_prompt})

                chat_context = f"""
                Tu es un consultant expert SAP Business One 10.0. 
                RÈGLE 1 : Uniquement B1 10.0 standard (pas ECC, pas S/4HANA).
                RÈGLE 2 : Dis 'Je ne sais pas' si la fonction n'existe pas. Zéro hallucination.
                Processus : {st.session_state.bpmn_tasks_only}
                Question : {user_prompt}
                """
                with st.chat_message("assistant"):
                    with st.spinner("Recherche..."):
                        try:
                            response = client.chat.completions.create(
                                model=MODEL_NAME,
                                messages=[
                                    {"role": "system", "content": "Tu es rigoureux et expert sur SAP B1."},
                                    {"role": "user", "content": chat_context}
                                ],
                                temperature=0.0,
                                max_tokens=1000
                            )
                            ans = response.choices[0].message.content
                            st.markdown(ans)
                            st.session_state.chat_history.append({"role": "assistant", "content": ans})
                        except Exception as e:
                            st.error(f"🔴 Erreur API Groq : {e}")
