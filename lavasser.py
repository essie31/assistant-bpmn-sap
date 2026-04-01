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
# 🔒 SÉCURITÉ
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
    
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
    # Utilisation du modèle le plus puissant pour éviter les erreurs techniques
    MODEL_NAME = "llama-3.3-70b-versatile"

    def parse_bpmn_from_file(file_object):
        try:
            tree = ET.parse(file_object)
            root = tree.getroot()
            ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
            lane_map = {node_ref.text: lane.get('name', 'Général') 
                        for lane in root.findall('.//bpmn:lane', ns) 
                        for node_ref in lane.findall('bpmn:flowNodeRef', ns)}
            tasks = [f"- [{lane_map.get(elem.get('id'), 'Général')}] {elem.get('name', 'Sans nom').strip()}"
                     for elem in root.findall('.//bpmn:process/*', ns)
                     if 'id' in elem.attrib and 'sequenceFlow' not in elem.tag and elem.get('name')]
            return "\n".join(tasks)
        except: return None

    # ==========================================
    # 🤖 GÉNÉRATION ÉTAPE 1 : ARCHITECTURE SAP RÉELLE
    # ==========================================

    def generate_step1(tasks_text):
        prompt = f"""
        Tu es un Consultant Expert Senior SAP Business One 10.0. 
        Analyse ce processus : {tasks_text}

        RÈGLES TECHNIQUES STRICTES POUR L'INTÉGRATION :
        1. OF UNIQUE : Un processus de fabrication (lavage, ozone, etc.) utilise UN SEUL Ordre de Fabrication (OWOR).
        2. ÉTAPES : Les traitements (1er lavage, permanganate) sont des 'Étapes de Route' ou 'Lignes de Ressources' dans l'OF.
        3. TRANSACTIONS : Pour valider une étape, utilise la 'Déclaration de production' (Table OIGN).
        4. STOCK : L'impact sur OITW se fait via la consommation des composants (IGE) ou l'entrée du produit fini (IGN).
        5. EXPORT : Le transfert vers l'export est une 'Livraison' (ODLN), pas une commande.
        6. QUALITÉ : Le standard SAP B1 n'utilise pas 'OINS'. Utilise des 'Champs Utilisateurs (UDF)' ou 'Plans de contrôle'.

        Produis un rapport détaillé :
        ### 1. 📊 Synthèse des Tâches
        ### 2. 📝 Analyse Métier du Flux (Minimum 3 paragraphes)
        ### 3. 🔵 Architecture SAP Business One 10.0 (Détails techniques corrigés)
        Pour chaque tâche informatisable :
        * **[Nom de la tâche]**
          * **Objet SAP :** [Ex: Étape de route dans OWOR / Déclaration de production OIGN]
          * **Chemin Menu :** [Chemin exact du standard 10.0]
          * **Impact Système :** [Impact réel sur les stocks et les coûts de production]
        """
        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": "Tu es un architecte SAP B1 10.0. Tu ne cites que des menus et objets réels."},
                      {"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=3000
        ).choices[0].message.content

    # ==========================================
    # 🤖 GÉNÉRATION ÉTAPE 2 : MATRICE 4.0
    # ==========================================

    def generate_step2(tasks_text):
        prompt = f"""
        Génère un seul grand tableau Markdown Industrie 4.0 pour ces tâches : {tasks_text}
        Colonnes : | Tâche | Big Data | Robots | Simul. | Intégr. | IIoT | Cyber | Cloud | Additif | RA | Justification Technique |
        Chaque justification doit faire au moins 15 mots et être technique.
        """
        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000
        ).choices[0].message.content

    # --- UI Streamlit ---
    if "s1" not in st.session_state: st.session_state.update({"s1":"", "s2":"", "tasks":""})
    
    file = st.file_uploader("Charger le fichier BPMN", type=['bpmn', 'xml'])
    if file:
        st.session_state.tasks = parse_bpmn_from_file(file)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("1️⃣ Analyse & Architecture SAP"):
                st.session_state.s1 = generate_step1(st.session_state.tasks)
        with col2:
            if st.button("2️⃣ Matrice Industrie 4.0"):
                st.session_state.s2 = generate_step2(st.session_state.tasks)
        with col3:
            if st.button("3️⃣ Graphique Radar"):
                res = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role":"user", "content":f"JSON uniquement : moyennes 1-5 des 9 piliers I4.0 pour : {st.session_state.tasks}"}],
                    temperature=0
                ).choices[0].message.content
                try:
                    data = json.loads(re.search(r'\{.*\}', res, re.S).group())
                    st.plotly_chart(px.line_polar(pd.DataFrame(dict(r=list(data.values()), theta=list(data.keys()))), r='r', theta='theta', line_close=True, range_r=[0,5]))
                except: st.error("Erreur graphique")

        if st.session_state.s1: st.markdown(st.session_state.s1)
        if st.session_state.s2: st.markdown(st.session_state.s2)
