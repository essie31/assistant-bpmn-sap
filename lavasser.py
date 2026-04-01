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
    table { page-break-inside: auto; width: 100% !important; font-size: 11px; }
    tr { page-break-inside: avoid; page-break-after: auto; }
    h2, h3 { page-break-after: avoid; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SYSTÈME DE SÉCURITÉ (LOGIN)
# ==========================================
# Sécurité : On récupère le mot de passe depuis les secrets
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
    # 🔑 CLÉ API (Sécurisée)
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

    def get_best_model():
        """Trouve le meilleur modèle disponible."""
        genai.configure(api_key=API_KEY)
        valid_model_name
