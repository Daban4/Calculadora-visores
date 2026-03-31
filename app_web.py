import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
import os
from PIL import Image, ImageDraw, ImageFont
import io
import uuid

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Calculadora de Visores", layout="wide", page_icon="🎯")

# --- ESTILOS PERSONALIZADOS (MODO OSCURO PREMIUM LIMPIO) ---
st.markdown("""
    <head>
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-title" content="Calculadora de Visores">
        <meta name="application-name" content="Calculadora de Visores">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="mobile-web-app-capable" content="yes">
    </head>
    <style>
    .main { background-color: #04040c; color: #ffffff; }
    /* Botones Azules por defecto */
    .stButton>button { 
        background-color: #1280e0 !important; 
        color: white !important; 
        width: 100%; 
        border-radius: 8px; 
        border: none; 
    }
    .stButton>button:hover { background-color: #1a95ff; border: none; }

    /* El ÚLTIMO botón en el lateral (Borrar) siempre en ROJO */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stButton"]:last-of-type button {
        background-color: #ff4b4b !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADO ---
if 'profiles' not in st.session_state:
    st.session_state.profiles = {
        "Principal": {
            "datos": [
                {"id": uuid.uuid4().hex, "dist": 20.0, "alt": 1.0},
                {"id": uuid.uuid4().hex, "dist": 40.0, "alt": 3.5},
                {"id": uuid.uuid4().hex, "dist": 70.0, "alt": 8.0}
            ],
            "metodo": "Interpolación"
        },
        "Perfil 2": {
            "datos": [
                {"id": uuid.uuid4().hex, "dist": 10.0, "alt": -1.0},
                {"id": uuid.uuid4().hex, "dist": 50.0, "alt": 4.0}
            ],
            "metodo": "Regresión"
        }
    }
if 'current_profile' not in st.session_state:
    st.session_state.current_profile = "Principal"

# --- FUNCIONES DE APOYO ---
def sort_profile_data(p_name):
    """Ordena los datos del perfil por distancia real (ignorando ceros temporales)."""
    if p_name in st.session_state.profiles:
        data = st.session_state.profiles[p_name]["datos"]
        st.session_state.profiles[p_name]["datos"] = sorted(data, key=lambda x: x["dist"] if x["dist"] > 0 else 999999)

def calculate_ballistics(dist_arr, alt_arr, method, start, end, step):
    """Motor de cálculo Numpy."""
    dist_pred = np.arange(start, end + step/100, step)
    
    if method == 'Regresión':
        coeffs = np.polyfit(dist_arr, alt_arr, 2)
        p = np.poly1d(coeffs)
        alt_pred = p(dist_pred)
    else:
        alt_pred = np.interp(dist_pred, dist_arr, alt_arr)
        if len(dist_arr) >= 2:
            if dist_pred[0] < dist_arr[0]:
                slope_l = (alt_arr[1] - alt_arr[0]) / (dist_arr[1] - dist_arr[0])
                alt_pred[dist_pred < dist_arr[0]] = alt_arr[0] + (dist_pred[dist_pred < dist_arr[0]] - dist_arr[0]) * slope_l
            if dist_pred[-1] > dist_arr[-1]:
                slope_r = (alt_arr[-1] - alt_arr[-2]) / (dist_arr[-1] - dist_arr[-2])
                alt_pred[dist_pred > dist_arr[-1]] = alt_arr[-1] + (dist_pred[dist_pred > dist_arr[-1]] - dist_arr[-1]) * slope_r
    
    return dist_pred, alt_pred

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🎯 Ajustes")
    
    prof_list = list(st.session_state.profiles.keys())
    selected_prof = st.selectbox("Selecciona tu Perfil:", prof_list, index=prof_list.index(st.session_state.current_profile))
    st.session_state.current_profile = selected_prof
    
    st.divider()
    st.subheader("Rango de Tabla")
    c1, c2 = st.columns(2)
    start_d = c1.number_input("Inic (m)", value=10, step=5)
    end_d = c2.number_input("Fin (m)", value=70, step=10)
    step_d = st.slider("Pasos (m)", 1, 20, 5)
    
    method = st.radio("Cálculo:", ["Interpolación", "Regresión"], 
                      index=0 if st.session_state.profiles[selected_prof]["metodo"] == "Interpolación" else 1)
    
    st.divider()
    if st.button("+ Nuevo Perfil"):
        n_name = f"Perfil {len(st.session_state.profiles) + 1}"
        # Creamos el perfil nuevo con los valores predeterminados cargados
        st.session_state.profiles[n_name] = {
            "datos": [
                {"id": uuid.uuid4().hex, "dist": 20.0, "alt": 1.0},
                {"id": uuid.uuid4().hex, "dist": 40.0, "alt": 3.5},
                {"id": uuid.uuid4().hex, "dist": 70.0, "alt": 8.0}
            ], 
            "metodo": "Interpolación"
        }
        # AUTO-SALTO: Cambiamos al nuevo perfil de inmediato
        st.session_state.current_profile = n_name
        st.rerun()
    
    if st.button("🗑️ Borrar Perfil"):
        if len(st.session_state.profiles) > 1:
            del st.session_state.profiles[selected_prof]
            # Cambiamos al primer perfil disponible
            st.session_state.current_profile = list(st.session_state.profiles.keys())[0]
            st.rerun()
        else:
            st.warning("No puedes borrar el último perfil.")

# --- ÁREA DE TRABAJO ---
st.title(f"Perfil: {st.session_state.current_profile}")
st.caption(f"Motor: {method}")

# --- ENTRADA DE DATOS (RESTAURADA A 3 COLUMNAS LIMPIAS) ---
st.subheader("1. Datos de Tiro")

# Cabecera de Tabla Original
h1, h2, h3 = st.columns([1.5, 1.5, 0.5])
h1.markdown("**Distancia (m)**")
h2.markdown("**Altura (Visor)**")
h3.write("")

current_data = st.session_state.profiles[st.session_state.current_profile]["datos"]
to_delete = None

# LOOP DE FILAS CON ID ÚNICO (Fiabilidad total en el ordenado)
for i, item in enumerate(current_data):
    rid = item["id"]
    c1, c2, c3 = st.columns([1.5, 1.5, 0.5])
    
    nd = c1.number_input(f"D_{rid}", value=float(item["dist"]), key=f"dist_{rid}", label_visibility="collapsed", step=1.0)
    nh = c2.number_input(f"A_{rid}", value=float(item["alt"]), key=f"alt_{rid}", label_visibility="collapsed", step=0.1)
    
    item["dist"] = nd
    item["alt"] = nh
    
    if c3.button("🗑️", key=f"btn_{rid}"):
        to_delete = i

# Botones de Acción
ca, co = st.columns(2)
if ca.button("➕ Añadir Nueva Fila"):
    sort_profile_data(st.session_state.current_profile)
    st.session_state.profiles[st.session_state.current_profile]["datos"].append({"id": uuid.uuid4().hex, "dist": 0.0, "alt": 0.0})
    st.rerun()

if co.button("🔄 Ordenar Datos"):
    sort_profile_data(st.session_state.current_profile)
    st.rerun()

# Procesar Borrado
if to_delete is not None:
    current_data.pop(to_delete)
    st.rerun()

# --- RESULTADOS Y EXPORTACIÓN ---
clean_dict = {float(d["dist"]): float(d["alt"]) for d in current_data if float(d["dist"]) > 0}
dist_arr = np.array(sorted(clean_dict.keys()))
alt_arr = np.array([clean_dict[d] for d in dist_arr])

if len(dist_arr) >= 2:
    d_res, a_res = calculate_ballistics(dist_arr, alt_arr, method, start_d, end_d, step_d)
    
    st.divider()
    st.subheader("2. Tabla de Cálculo")
    res_df = pd.DataFrame({
        "Distancia (m)": [f"{d:.0f}" for d in d_res],
        "Altura (Clics)": [f"{h:.2f}" for h in a_res]
    })
    # Calculamos la altura justa para que no salgan celdas vacías (35px por fila + cabecera)
    calc_height = (len(res_df) + 1) * 35 + 3
    st.dataframe(res_df, use_container_width=True, hide_index=True, height=min(calc_height, 800))
    
    # --- GENERADOR DE PNG ---
    def make_png(p_name, p_method, dr, ar):
        W, CH, M, HH = 800, 60, 60, 140
        IMG_H = HH + (len(dr) + 1) * CH + 40
        img = Image.new('RGB', (W, IMG_H), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        f_large = ImageFont.load_default(size=30)
        f_small = ImageFont.load_default(size=22)
        
        draw.text((M, 40), f"PERFIL: {p_name.upper()}", fill=(0,0,0), font=f_large)
        draw.text((M, 85), f"MODO: {p_method} | FECHA: {datetime.now().strftime('%d/%m/%Y %H:%M')}", fill=(0,0,0), font=f_small)
        
        curr_y = HH
        draw.rectangle([M, curr_y, W-M, curr_y+CH], fill=(230, 230, 230))
        draw.text((M+30, curr_y+15), "DISTANCIA (m)", fill=(0,0,0), font=f_large)
        draw.text((W//2+30, curr_y+15), "ALTURA", fill=(0,0,0), font=f_large)
        curr_y += CH
        
        for d, a in zip(dr, ar):
            draw.line([(M, curr_y), (W-M, curr_y)], fill=(0,0,0))
            draw.text((M+30, curr_y+15), f"{d:.0f} m", fill=(0,0,0), font=f_large)
            draw.text((W//2+30, curr_y+15), f"{a:.2f}", fill=(0,0,0), font=f_large)
            curr_y += CH
            
        draw.rectangle([M, HH, W-M, curr_y], outline=(0,0,0), width=2)
        draw.line([(W//2, HH), (W//2, curr_y)], fill=(0,0,0), width=2)
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    png_data = make_png(st.session_state.current_profile, method, d_res, a_res)
    st.download_button(
        label="📥 Descargar PNG",
        data=png_data,
        file_name=f"Calculo_{st.session_state.current_profile}.png",
        mime="image/png"
    )
    
    st.session_state.profiles[st.session_state.current_profile]["metodo"] = method
else:
    st.warning("⚠️ Introduce al menos 2 distancias para ver los resultados.")
