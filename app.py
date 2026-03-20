import streamlit as st
import pandas as pd
import os
from datetime import datetime
import streamlit_authenticator as stauth

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Escrutinio Alianza Patria Sol", layout="wide", page_icon="🗳️")

# --- 2. DEFINICIÓN DE FUNCIONES (NIVEL PRINCIPAL) ---

@st.cache_data
def cargar_datos_maestros():
    df_m = pd.read_csv("recintos.csv") if os.path.exists("recintos.csv") else pd.DataFrame(columns=["circunscripcion","NombreDeRecinto","mesa","NroHabilitados"])
    df_p = pd.read_csv("partidos.csv") if os.path.exists("partidos.csv") else pd.DataFrame(columns=["Sigla", "Nombre Candidato", "logo"])
    return df_m, df_p

def esta_bloqueado_optimizado(df, rec, mes, cat):
    if df.empty or 'Categoría' not in df.columns: 
        return False
    filtro = df[(df['Recinto'] == rec) & 
                (df['Mesa'].astype(str) == str(mes)) & 
                (df['Categoría'] == cat)]
    return not filtro.empty

def generar_reporte_votos(df):
    st.subheader("📊 Resumen Ejecutivo de Votación")
    metadatos = ["Timestamp", "Usuario", "Circunscripcion", "Recinto", "Mesa", "Categoría", "Inscritos", "Votos_Validos", "Foto", "Obs"]
    columnas_partidos = [c for c in df.columns if c not in metadatos]
    
    cat_reporte = st.selectbox("Selecciona Categoría para el Reporte", df['Categoría'].unique(), key="sel_reporte")
    df_cat = df[df['Categoría'] == cat_reporte]
    
    if not df_cat.empty:
        totales = df_cat[columnas_partidos].sum().sort_values(ascending=False)
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Mesas Computadas", len(df_cat))
        m2.metric("Ganador Actual", totales.index[0], f"{int(totales.iloc[0])} votos")
        
        # Cálculo de participación con protección de división por cero
        total_inscritos = df_cat['Inscritos'].sum()
        participacion = (df_cat['Votos_Validos'].sum() / total_inscritos * 100) if total_inscritos > 0 else 0
        m3.metric("Participación", f"{participacion:.2f}%")

        st.bar_chart(totales)
    else:
        st.info("Aún no hay datos suficientes para esta categoría.")

# --- 3. SEGURIDAD Y CONFIGURACIÓN ---
config = st.secrets.to_dict()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)
authenticator.login(location='main')

# --- 4. LÓGICA DE LA APLICACIÓN ---
if st.session_state["authentication_status"]:
    username = st.session_state["username"]
    user_role = config['credentials']['usernames'][username]['role']
    DB_FILE = "votos_final.csv"
    FOTOS_DIR = "fotosactas"
    if not os.path.exists(FOTOS_DIR): os.makedirs(FOTOS_DIR)

    df_mapeo, df_partidos = cargar_datos_maestros()
    CATEGORIAS = ["Gobernador", "Asambleísta Departamental", "Asambleísta Regional", "Alcalde", "Concejal"]

    # Carga de datos optimizada (una sola vez por ejecución)
    df_votos_actual = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()

    st.title("🗳️ Captura de Actas - Alianza Patria Sol")
    
    # --- CABECERA DINÁMICA ---
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    with c1:
        circ_list = sorted(df_mapeo['circunscripcion'].unique().tolist())
        circ_sel = st.selectbox("Circunscripción", circ_list)
    with c2:
        df_rec = df_mapeo[df_mapeo['circunscripcion'] == circ_sel]
        rec_list = sorted(df_rec['NombreDeRecinto'].unique().tolist())
        recinto_sel = st.selectbox("Recinto", rec_list)
    with c3:
        df_mes = df_rec[df_rec['NombreDeRecinto'] == recinto_sel]
        mes_list = sorted(df_mes['mesa'].unique().tolist())
        mesa_sel = st.selectbox("Nro Mesa", mes_list)
    with c4:
        hab_val = df_mes[df_mes['mesa'] == mesa_sel]['NroHabilitados'].values[0]
        st.number_input("Habilitados", value=int(hab_val), disabled=True)

    st.divider()

    # --- 5. BUCLE DE CATEGORÍAS ---
    for cat in CATEGORIAS:
        bloqueo = esta_bloqueado_optimizado(df_votos_actual, recinto_sel, mesa_sel, cat)        
        color = "red" if bloqueo else "blue"
        st.markdown(f"### 📍 Elección: :{color}[{cat.upper()}]")
        
        if bloqueo and user_role != 'admin':
            st.warning(f"🔒 Acta de {cat} ya registrada.")
            continue

        with st.form(key=f"form_{cat}_{mesa_sel}"):
            f1, f2 = st.columns([2, 1])
            with f1:
                foto = st.file_uploader(f"📸 Foto Acta {cat}", type=['jpg','png','jpeg'], key=f"img_{cat}")
            with f2:
                v_val = st.number_input(f"Votos Válidos ({cat})", min_value=0, key=f"val_{cat}")

            votos_data = {}
            if not df_partidos.empty:
                lista_candidatos = df_partidos.to_dict('records')
                lista_candidatos.extend([{'Sigla': 'Blancos', 'logo': ''}, {'Sigla': 'Nulos', 'logo': ''}])
                
                columnas_por_fila = 7
                for i in range(0, len(lista_candidatos), columnas_por_fila):
                    cols = st.columns(columnas_por_fila)
                    subgrupo = lista_candidatos[i : i + columnas_por_fila]
                    for j, cand in enumerate(subgrupo):
                        with cols[j]:
                            sigla = cand['Sigla']
                            nombre_archivo = str(cand.get('logo', ''))
                            ruta_logo = os.path.join("logos", nombre_archivo)
                           
                            if nombre_archivo and os.path.exists(ruta_logo):
                                st.image(ruta_logo, width=30)
                            st.caption(f"**{sigla}**")
                            v_input = st.number_input(label=sigla, min_value=0, key=f"v_{cat}_{sigla}_{mesa_sel}", label_visibility="collapsed")
                            votos_data[sigla] = v_input

            obs = st.text_input("Observaciones", key=f"obs_{cat}")
            submit = st.form_submit_button(f"💾 GUARDAR ACTA {cat.upper()}", disabled=(bloqueo and user_role != 'admin'))

            if submit:
                path_foto = os.path.join(FOTOS_DIR, f"{cat}_{recinto_sel}_{mesa_sel}.jpg".replace(" ","_"))
                with open(path_foto, "wb") as f: f.write(foto.getbuffer())
                
                nuevo_reg = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Usuario": username, "Circunscripcion": circ_sel, "Recinto": recinto_sel, 
                    "Mesa": mesa_sel, "Categoría": cat, "Inscritos": hab_val, 
                    "Votos_Validos": v_val, "Foto": path_foto, **votos_data, "Obs": obs
                }
                
                df_nuevo = pd.DataFrame([nuevo_reg])
                if bloqueo and user_role == 'admin':
                    df_db = pd.read_csv(DB_FILE)
                    df_db = df_db[~((df_db['Recinto'] == recinto_sel) & (df_db['Mesa'].astype(str) == str(mesa_sel)) & (df_db['Categoría'] == cat))]
                    pd.concat([df_db, df_nuevo]).to_csv(DB_FILE, index=False)
                else:
                    df_nuevo.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
                
                st.success(f"✅ Acta de {cat} guardada.")
                st.rerun()

    # --- 6. PANEL DE CONTROL ADMIN ---
    if user_role == 'admin' and not df_votos_actual.empty:
        st.divider()
        st.subheader("📊 Consolidado de Datos")
        st.dataframe(df_votos_actual)
        st.download_button("📥 Descargar Base de Datos", df_votos_actual.to_csv(index=False), "votos_patria_sol.csv", "text/csv")
        generar_reporte_votos(df_votos_actual)

elif st.session_state["authentication_status"] is False:
    st.error('Usuario/Contraseña incorrectos')