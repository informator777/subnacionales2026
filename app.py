import streamlit as st
import pandas as pd
import os
from datetime import datetime
import streamlit_authenticator as stauth

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Escrutinio Alianza Patria Sol", layout="wide", page_icon="🗳️")

# --- 2. CONFIGURACIÓN DE SEGURIDAD (Ajusta tus Hashes) ---
# --- 2. CONFIGURACIÓN DE SEGURIDAD DESDE SECRETS ---
# Streamlit cargará automáticamente lo que esté en .streamlit/secrets.toml
config = st.secrets.to_dict()

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])
authenticator.login(location='main')

if st.session_state["authentication_status"]:
    # Variables de Sesión
    username = st.session_state["username"]
    user_role = config['credentials']['usernames'][username]['role']
    DB_FILE = "votos_final.csv"
    FOTOS_DIR = "fotosactas"
    if not os.path.exists(FOTOS_DIR): os.makedirs(FOTOS_DIR)

    # --- 3. CARGA DE RECURSOS ---
    @st.cache_data
    def cargar_datos_maestros():
        df_m = pd.read_csv("recintos.csv") if os.path.exists("recintos.csv") else pd.DataFrame(columns=["circunscripcion","NombreDeRecinto","mesa","NroHabilitados"])
        df_p = pd.read_csv("partidos.csv") if os.path.exists("partidos.csv") else pd.DataFrame(columns=["Sigla", "Nombre Candidato", "logo"])
        return df_m, df_p

    df_mapeo, df_partidos = cargar_datos_maestros()
    CATEGORIAS = ["Gobernador", "Asambleísta Departamental", "Asambleísta Regional", "Alcalde", "Concejal"]

    # Función de Bloqueo con Cast de datos
    def esta_bloqueado(rec, mes, cat):
        if not os.path.exists(DB_FILE): return False
        df = pd.read_csv(DB_FILE)
        if 'Categoría' not in df.columns: return False
        filtro = df[(df['Recinto'] == rec) & (df['Mesa'].astype(str) == str(mes)) & (df['Categoría'] == cat)]
        return not filtro.empty

    st.title("🗳️ Captura de Actas - Alianza Patria Sol")
    
    # --- 4. CABECERA DINÁMICA (FILTROS EN CASCADA) ---
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
        inscritos = st.number_input("Habilitados", value=int(hab_val), disabled=True)

    st.divider()

    # --- 5. BUCLE DE CATEGORÍAS ---
    for cat in CATEGORIAS:
        bloqueo = esta_bloqueado(recinto_sel, mesa_sel, cat)
        color = "red" if bloqueo else "blue"
        
        st.markdown(f"### 📍 Elección: :{color}[{cat.upper()}]")
        
        if bloqueo and user_role != 'admin':
            st.warning(f"🔒 Acta de {cat} ya registrada. Solo un administrador puede modificarla.")
            continue

        with st.form(key=f"form_{cat}_{mesa_sel}"):
            f1, f2 = st.columns([2, 1])
            with f1:
                foto = st.file_uploader(f"📸 Foto Acta {cat}", type=['jpg','png','jpeg'], key=f"img_{cat}")
            with f2:
                v_val = st.number_input(f"Votos Válidos ({cat})", min_value=0, key=f"val_{cat}")

           # --- SECCIÓN DE VOTOS (CUADRÍCULA DE 10 COLUMNAS) ---
            votos_data = {}
            if not df_partidos.empty:
                # 1. Creamos la lista unificada: Partidos + Blancos + Nulos
                lista_candidatos = df_partidos.to_dict('records')
                lista_candidatos.append({'Sigla': 'Blancos', 'logo': ''})
                lista_candidatos.append({'Sigla': 'Nulos', 'logo': ''})

                # 2. Definimos el ancho de la cuadrícula
                columnas_por_fila = 7
                
                # 3. Iteramos para crear filas de 10 columnas cada una
                for i in range(0, len(lista_candidatos), columnas_por_fila):
                    cols = st.columns(columnas_por_fila)
                    
                    # Tomamos el subgrupo de 10 candidatos para esta fila
                    subgrupo = lista_candidatos[i : i + columnas_por_fila]
                    
                    for j, cand in enumerate(subgrupo):
                        with cols[j]:
                            sigla = cand['Sigla']
                            
                            # Mostramos el logo si la ruta existe y no está vacía
                            # Mostramos el logo si la ruta existe
                            # cand.get('logos') debe coincidir con el nombre de la columna en partidos.csv
                            nombre_archivo = str(cand.get('logo', ''))

                            # Construimos la ruta completa uniendo la carpeta con el nombre del archivo
                            ruta_logo = os.path.join("logo", nombre_archivo)

                            if nombre_archivo and os.path.exists(ruta_logo):
                                st.image(ruta_logo, width=30)
                            else:
                                # Esto te ayudará a debuguear: si no lo encuentra, no muestra nada o un icono
                                st.write(" ")
                                                        
                            # Etiqueta pequeña y campo de texto sin label (collapsed)
                            st.caption(f"**{sigla}**")
                            v_input = st.number_input(
                                label=sigla,
                                min_value=0, 
                                step=1, 
                                key=f"v_{cat}_{sigla}_{mesa_sel}", 
                                label_visibility="collapsed",
                                max_value=999
                            )
                            votos_data[sigla] = v_input

            obs = st.text_input("Observaciones", key=f"obs_{cat}")
            submit = st.form_submit_button(f"💾 GUARDAR ACTA {cat.upper()}", disabled=(bloqueo and user_role != 'admin'))

            if submit:
                if not foto:
                    st.error("Es obligatorio subir la foto del acta.")
                else:
                    # Guardar Foto
                    path_foto = os.path.join(FOTOS_DIR, f"{cat}_{recinto_sel}_{mesa_sel}.jpg".replace(" ","_"))
                    with open(path_foto, "wb") as f: f.write(foto.getbuffer())
                    
                    # Preparar Registro
                    nuevo_reg = {
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Usuario": username, "Circunscripcion": circ_sel, "Recinto": recinto_sel, 
                        "Mesa": mesa_sel, "Categoría": cat, "Inscritos": inscritos, 
                        "Votos_Validos": v_val, "Foto": path_foto, **votos_data, "Obs": obs
                    }
                    
                    df_nuevo = pd.DataFrame([nuevo_reg])
                    if bloqueo and user_role == 'admin':
                        df_db = pd.read_csv(DB_FILE)
                        df_db = df_db[~((df_db['Recinto'] == recinto_sel) & (df_db['Mesa'].astype(str) == str(mesa_sel)) & (df_db['Categoría'] == cat))]
                        pd.concat([df_db, df_nuevo]).to_csv(DB_FILE, index=False)
                    else:
                        df_nuevo.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
                    
                    st.success(f"✅ Acta de {cat} guardada correctamente.")
                    st.rerun()

    # --- 6. PANEL DE CONTROL ADMIN ---
    if user_role == 'admin' and os.path.exists(DB_FILE):
        st.divider()
        st.subheader("📊 Consolidado de Datos")
        df_v = pd.read_csv(DB_FILE)
        st.dataframe(df_v)
        st.download_button("📥 Descargar Base de Datos", df_v.to_csv(index=False), "votos_patria_sol.csv", "text/csv")

elif st.session_state["authentication_status"] is False:
    st.error('Usuario/Contraseña incorrectos')