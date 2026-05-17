import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Force & VBT Pro", page_icon="🏋️‍♂️", layout="centered")

# Initialisation des variables de session
if 'historique_seance' not in st.session_state:
    st.session_state.historique_seance = []

# --- BASE DE DONNÉES DES 1RM DE RÉFÉRENCE ---
if 'rm_squat' not in st.session_state: st.session_state.rm_squat = 175.0
if 'rm_bench' not in st.session_state: st.session_state.rm_bench = 107.5
if 'rm_deadlift' not in st.session_state: st.session_state.rm_deadlift = 222.5
if 'rm_autre' not in st.session_state: st.session_state.rm_autre = 100.0

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Bouton de bascule de thème stylisé
    label_theme = "☀️ Passer au Mode Jour" if st.session_state.theme_nuit else "🌙 Passer au Mode Nuit"
    if st.button(label_theme, use_container_width=True):
        st.session_state.theme_nuit = not st.session_state.theme_nuit
        st.rerun()
        
    st.divider()
    st.subheader("🎯 Tes 1RM de Référence")
    st.session_state.rm_squat = st.number_input("Squat (kg)", min_value=1.0, value=st.session_state.rm_squat, step=2.5)
    st.session_state.rm_bench = st.number_input("Développé Couché (kg)", min_value=1.0, value=st.session_state.rm_bench, step=2.5)
    st.session_state.rm_deadlift = st.number_input("Soulevé de Terre (kg)", min_value=1.0, value=st.session_state.rm_deadlift, step=2.5)
    st.session_state.rm_autre = st.number_input("Autre mouvement (kg)", min_value=1.0, value=st.session_state.rm_autre, step=2.5)

# --- INJECTION CSS AVANCÉE POUR LES THÈMES (UI MULTI-PLATEFORME) ---
if st.session_state.theme_nuit:
    st.markdown("""
        <style>
        /* Fond global et textes */
        .stApp { background-color: #0F1219; color: #F3F4F6; }
        
        /* Personnalisation des onglets (Tabs) */
        button[data-baseweb="tab"] { color: #9CA3AF !important; font-weight: 600; }
        button[aria-selected="true"] { color: #00F0FF !important; border-bottom-color: #00F0FF !important; }
        
        /* Boutons Primaires (Boutons d'action) */
        div.stButton > button[kind="primary"] { 
            background-color: #00F0FF !important; color: #0F1219 !important; 
            font-weight: bold; border-none: true; border-radius: 8px;
            box-shadow: 0px 0px 10px rgba(0, 240, 255, 0.3);
        }
        
        /* Conteneurs de métriques / Cartes */
        div[data-testid="stMetricValue"] { color: #00F0FF !important; font-size: 2rem !important; font-weight: bold; }
        div[data-testid="stMetricLabel"] { color: #9CA3AF !important; }
        
        /* Inputs et Sélecteurs */
        div[data-baseweb="select"] { background-color: #1F2937 !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        /* Fond global et textes */
        .stApp { background-color: #F9FAFB; color: #111827; }
        
        /* Personnalisation des onglets (Tabs) */
        button[data-baseweb="tab"] { color: #4B5563 !important; font-weight: 600; }
        button[aria-selected="true"] { color: #2563EB !important; border-bottom-color: #2563EB !important; }
        
        /* Boutons Primaires (Boutons d'action) */
        div.stButton > button[kind="primary"] { 
            background-color: #2563EB !important; color: #FFFFFF !important; 
            font-weight: bold; border-radius: 8px;
        }
        
        /* Conteneurs de métriques / Cartes */
        div[data-testid="stMetricValue"] { color: #2563EB !important; font-size: 2rem !important; font-weight: bold; }
        div[data-testid="stMetricLabel"] { color: #4B5563 !important; }
        </style>
    """, unsafe_allow_html=True)


# --- FONCTIONS DE CALCUL AUTO-RÉGULÉES ---
def estimer_1rm(charge, reps, rpe):
    rir = 10 - rpe
    reps_totales = reps + rir
    if reps_totales <= 1: return charge
    return charge / (1.0278 - (0.0278 * reps_totales))

def calculer_top_set_avec_1rm_et_rpe(rm_ref, charge_w, rpe_w, vitesse_w, reps_cible, rpe_cible, nb_series_top):
    rm_du_jour_estime = estimer_1rm(charge_w, 1, rpe_w)
    rm_ajuste = (rm_ref + rm_du_jour_estime) / 2
    
    reps_totales_cible = reps_cible + (10 - rpe_cible)
    percentage_theorique = 1.0278 - (0.0278 * reps_totales_cible)
    charge_base = rm_ajuste * percentage_theorique
    
    facteur_vitesse = 1.0
    if vitesse_w > 0.52: facteur_vitesse = 1.025
    elif vitesse_w < 0.35: facteur_vitesse = 0.965
        
    facteur_fatigue = 1.0 - ((nb_series_top - 1) * 0.01)
    return round((charge_base * facteur_vitesse * facteur_fatigue) / 2.5) * 2.5

def calculer_back_offs_evolue(rm_ref, charge_last_top, rpe_last_top, vitesse_last_top, reps_bo, rpe_bo, nb_series_bo):
    rm_est_du_jour = estimer_1rm(charge_last_top, 1, rpe_last_top)
    rm_cible = (rm_ref + rm_est_du_jour) / 2
    
    reps_totales_bo = reps_bo + (10 - rpe_bo)
    charge_base_bo = rm_cible * (1.0278 - (0.0278 * reps_totales_bo))
    
    facteur_fatigue_vbt = 1.0
    if vitesse_last_top < 0.28: facteur_fatigue_vbt = 0.96
    elif vitesse_last_top > 0.42: facteur_fatigue_vbt = 1.01
        
    facteur_volume = 1.0 - ((nb_series_bo - 1) * 0.008)
    return round((charge_base_bo * facteur_fatigue_vbt * facteur_volume) / 2.5) * 2.5

def recuperer_rm_associe(nom_mouvement):
    if nom_mouvement == "Squat": return st.session_state.rm_squat
    elif nom_mouvement == "Développé Couché": return st.session_state.rm_bench
    elif nom_mouvement == "Soulevé de Terre": return st.session_state.rm_deadlift
    return st.session_state.rm_autre


# --- INTERFACE PRINCIPALE ---
st.title("🏋️‍♂️ Force & VBT Pro - V5.2")

onglet1, onglet2, onglet3, onglet4 = st.tabs(["🎯 Top Sets", "📉 Back-Offs", "🧮 1RM", "📝 Log"])

# --- ONGLET 1 : TOP SETS ---
with onglet1:
    st.header("Calculateur de Top Sets")
    
    mouvement_ts = st.selectbox("Sélectionne le mouvement", ["Squat", "Développé Couché", "Soulevé de Terre", "Autre"], key="mv_ts")
    rm_actuel_ts = recuperer_rm_associe(mouvement_ts)
    st.caption(f"📢 1RM de référence détecté : **{rm_actuel_ts} kg**")
    
    st.divider()
    st.subheader("Données du dernier échauffement lourd")
    charge_w = st.number_input("Charge (kg)", min_value=0.0, step=2.5, value=rm_actuel_ts*0.8, key="ts_cw")
    rpe_w = st.slider("RPE de l'échauffement", 5.0, 10.0, 7.0, 0.5, key="ts_rw")
    vitesse_w = st.number_input("Vitesse (m/s)", 0.1, 2.0, 0.45, 0.01, key="ts_vw")
    
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        nb_series_t = st.number_input("Nombre de séries", min_value=1, max_value=10, value=1, key="ts_nb")
        reps_c = st.number_input("Reps par série", min_value=1, max_value=12, value=6, key="ts_rep")
    with col_b:
        rpe_c = st.slider("RPE ciblé", 7.0, 10.0, 8.5, 0.5, key="ts_rc")
    
    if st.button("🚀 Suggérer la charge", type="primary", use_container_width=True):
        top_set = calculer_top_set_avec_1rm_et_rpe(rm_actuel_ts, charge_w, rpe_w, vitesse_w, reps_c, rpe_c, nb_series_t)
        st.metric(label="Charge recommandée", value=f"{top_set} kg")

# --- ONGLET 2 : BACK-OFFS ---
with onglet2:
    st.header("Calculateur de Back-Offs")
    
    mouvement_bo = st.selectbox("Sélectionne le mouvement", ["Squat", "Développé Couché", "Soulevé de Terre", "Autre"], key="mv_bo")
    rm_actuel_bo = recuperer_rm_associe(mouvement_bo)
    st.caption(f"📢 1RM de référence détecté : **{rm_actuel_bo} kg**")
    
    st.divider()
    st.caption("ℹ️ Rentre les données de ton **TOUT DERNIER TOP SET** effectué :")
    charge_t = st.number_input("Charge du dernier Top Set (kg)", min_value=0.0, step=2.5, value=rm_actuel_bo*0.85, key="bo_ct")
    rpe_t = st.slider("RPE réel obtenu", 5.0, 10.0, 9.0, 0.5, key="bo_rt")
    vitesse_t = st.number_input("Vitesse mesurée (m/s)", 0.1, 2.0, 0.32, 0.01, key="bo_vt")
    
    st.divider()
    col_c, col_d = st.columns(2)
    with col_c:
        nb_series_b = st.number_input("Nombre de séries Back-off", min_value=1, max_value=10, value=3, key="bo_nb")
        reps_b = st.number_input("Reps par Back-off", min_value=1, max_value=15, value=5, key="bo_rep")
    with col_d:
        rpe_b = st.slider("RPE ciblé", 5.0, 10.0, 7.5, 0.5, key="bo_rb")
    
    if st.button("📉 Suggérer les Back-Offs", type="primary", use_container_width=True):
        back_off_charge = calculer_back_offs_evolue(rm_actuel_bo, charge_t, rpe_t, vitesse_t, reps_b, rpe_b, nb_series_b)
        st.metric(label="Charge pour tes Back-offs", value=f"{back_off_charge} kg")

# --- ONGLET 3 : ESTIMATEUR 1RM ---
with onglet3:
    st.header("Estimation rapide du 1RM")
    charge_ef = st.number_input("Charge soulevée (kg)", min_value=0.0, step=2.5, value=100.0, key="e_c")
    reps_ef = st.number_input("Répétitions", 1, 20, 5, key="e_rep")
    rpe_ef = st.slider("RPE", 5.0, 10.0, 8.0, 0.5, key="e_r")
    
    if st.button("Estimer mon Max", use_container_width=True, type="primary"):
        e1rm = estimer_1rm(charge_ef, reps_ef, rpe_ef)
        st.success(f"Ton 1RM estimé : **{round(e1rm, 1)} kg**")

# --- ONGLET 4 : LOG SÉRIE ---
with onglet4:
    st.header("Enregistrement de la Série")
    
    mouvement_s = st.selectbox("Mouvement", ["Squat", "Développé Couché", "Soulevé de Terre", "Autre"], key="mv_log")
    rm_actuel_s = recuperer_rm_associe(mouvement_s)
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        charge_s = st.number_input("Charge (kg)", min_value=0.0, step=2.5, value=rm_actuel_s*0.75, key="log_c")
        reps_s = st.number_input("Répétitions", min_value=1, value=5, key="log_rep")
    with col2:
        rpe_s = st.slider("RPE", 5.0, 10.0, 8.0, 0.5, key="log_r")
        vitesse_s = st.number_input("Vitesse (m/s)", 0.1, 2.0, 0.45, 0.01, key="log_v")
        
    if st.button("💾 Enregistrer la série", type="primary", use_container_width=True):
        e1rm_serie = estimer_1rm(charge_s, reps_s, rpe_s)
        indice_perf = round((e1rm_serie / rm_actuel_s) * 100 * (vitesse_s + 0.6), 1)
        
        st.session_state.historique_seance.append({
            "Mouvement": mouvement_s,
            "Charge (kg)": charge_s,
            "Reps": reps_s,
            "RPE": rpe_s,
            "Vitesse (m/s)": vitesse_s,
            "1RM Est. (kg)": round(e1rm_serie, 1),
            "Indice": indice_perf
        })
        st.toast("Série enregistrée !")

    if st.session_state.historique_seance:
        st.divider()
        df = pd.DataFrame(st.session_state.historique_seance)
        st.dataframe(df, use_container_width=True)
        
        ind_moyen = round(df["Indice"].mean(), 1)
        st.metric("Indice de Perf Moyen", f"{ind_moyen} pts")
        
        if st.button("🗑️ Réinitialiser la séance", use_container_width=True):
            st.session_state.historique_seance = []
            st.rerun()
