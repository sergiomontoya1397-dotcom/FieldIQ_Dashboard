import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import tempfile, zipfile, os
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Field-IQ Dashboard", layout="wide")

st.markdown("""
<style>
.main-title {font-size:42px;font-weight:800;color:#1b263b;}
.card {padding:22px;border-radius:18px;background:white;box-shadow:0 4px 14px rgba(0,0,0,0.08);}
.red {border-left:8px solid #E53935;}
.yellow {border-left:8px solid #FDD835;}
.green {border-left:8px solid #43A047;}
.blue {border-left:8px solid #1E88E5;}
.eval-bad {background:#ffebee;border:2px solid #e53935;border-radius:18px;padding:20px;color:#b71c1c;}
.eval-good {background:#e8f5e9;border:2px solid #43a047;border-radius:18px;padding:20px;color:#1b5e20;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌱 Aplicación Field-IQ</div>', unsafe_allow_html=True)

st.sidebar.header("⚙️ Parámetros")
objetivo = st.sidebar.number_input("Dosis objetivo", value=150)
tolerancia = st.sidebar.slider("Tolerancia %", 1, 20, 5)

uploaded_file = st.file_uploader("Sube tu shapefile en .zip", type=["zip"])

if uploaded_file:
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, uploaded_file.name)

    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    shp_file = None
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.lower().endswith(".shp"):
                shp_file = os.path.join(root, file)

    if not shp_file:
        st.error("No se encontró archivo .shp dentro del ZIP.")
        st.stop()

    gdf_original = gpd.read_file(shp_file, engine="pyogrio")

    if "AppliedRat" not in gdf_original.columns:
        st.error("No se encontró la columna 'AppliedRat'.")
        st.write(list(gdf_original.columns))
        st.stop()

    st.success("Shapefile cargado correctamente")

    gdf_mapa = gdf_original.to_crs(epsg=4326)
    gdf_area = gdf_original.to_crs(epsg=3857)

    gdf_mapa["Area_ha"] = gdf_area.geometry.area / 10000
    gdf_mapa["AppliedRat"] = pd.to_numeric(gdf_mapa["AppliedRat"], errors="coerce")
    gdf_mapa = gdf_mapa.dropna(subset=["AppliedRat"])

    min_ok = objetivo * (1 - tolerancia / 100)
    max_ok = objetivo * (1 + tolerancia / 100)

    def clasificar(valor):
        if valor < min_ok:
            return "Sub-aplicado"
        elif valor <= max_ok:
            return "Óptimo"
        else:
            return "Sobre-aplicado"

    gdf_mapa["Categoria"] = gdf_mapa["AppliedRat"].apply(clasificar)

    resumen = gdf_mapa.groupby("Categoria")["Area_ha"].sum().reset_index()
    total = resumen["Area_ha"].sum()
    resumen["Porcentaje"] = resumen["Area_ha"] / total * 100

    orden = ["Sub-aplicado", "Óptimo", "Sobre-aplicado"]
    resumen["Categoria"] = pd.Categorical(resumen["Categoria"], categories=orden, ordered=True)
    resumen = resumen.sort_values("Categoria")

    def get_val(cat, col):
        fila = resumen[resumen["Categoria"] == cat]
        return 0 if fila.empty else float(fila[col].iloc[0])

    sub_area = get_val("Sub-aplicado", "Area_ha")
    opt_area = get_val("Óptimo", "Area_ha")
    sob_area = get_val("Sobre-aplicado", "Area_ha")

    sub_pct = get_val("Sub-aplicado", "Porcentaje")
    opt_pct = get_val("Óptimo", "Porcentaje")
    sob_pct = get_val("Sobre-aplicado", "Porcentaje")

    sobre_total = sob_pct
    sub_total = sub_pct

    if opt_pct >= 85:
        evaluacion = "EXCELENTE"
        eval_class = "eval-good"
    elif opt_pct >= 70:
        evaluacion = "BUENA"
        eval_class = "eval-good"
    elif opt_pct >= 50:
        evaluacion = "REGULAR"
        eval_class = "eval-bad"
    else:
        evaluacion = "DEFICIENTE"
        eval_class = "eval-bad"

    st.subheader("📊 Resumen de aplicación")

    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(f'<div class="card blue"><h4>Área total</h4><h2>{total:.2f} ha</h2></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="card red"><h4>Sub-aplicado</h4><h2>{sub_area:.2f} ha</h2><b>{sub_pct:.2f}%</b></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="card yellow"><h4>Óptimo</h4><h2>{opt_area:.2f} ha</h2><b>{opt_pct:.2f}%</b></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="card green"><h4>Sobre-aplicado</h4><h2>{sob_area:.2f} ha</h2><b>{sob_pct:.2f}%</b></div>', unsafe_allow_html=True)

    st.subheader("🗺️ Mapa de aplicación")

    colores = {
        "Sub-aplicado": "#E53935",
        "Óptimo": "#FDD835",
        "Sobre-aplicado": "#43A047"
    }

    centro = [
        gdf_mapa.geometry.centroid.y.mean(),
        gdf_mapa.geometry.centroid.x.mean()
    ]

    m = folium.Map(location=centro, zoom_start=17, tiles="Esri.WorldImagery")

    folium.GeoJson(
        gdf_mapa,
        style_function=lambda feature: {
            "fillColor": colores.get(feature["properties"]["Categoria"], "gray"),
            "color": "black",
            "weight": 0.35,
            "fillOpacity": 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["AppliedRat", "Categoria", "Area_ha"],
            aliases=["Dosis:", "Categoría:", "Área ha:"],
            localize=True
        )
    ).add_to(m)

    st_folium(m, width=1200, height=600)

    col_graf, col_tabla = st.columns([1, 1])

    with col_graf:
        st.subheader("🥧 Distribución porcentual")

        fig = px.pie(
            resumen,
            values="Area_ha",
            names="Categoria",
            color="Categoria",
            color_discrete_map={
                "Sub-aplicado": "#E53935",
                "Óptimo": "#FDD835",
                "Sobre-aplicado": "#43A047"
            },
            hole=0.25
        )

        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col_tabla:
        st.subheader("📋 Tabla de porcentajes")

        tabla = resumen.copy()
        tabla["Área (ha)"] = tabla["Area_ha"].round(3)
        tabla["% del total"] = tabla["Porcentaje"].round(2)
        tabla = tabla[["Categoria", "Área (ha)", "% del total"]]

        st.dataframe(tabla, use_container_width=True)

        csv = tabla.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Descargar tabla CSV",
            csv,
            "tabla_porcentajes.csv",
            "text/csv"
        )

    st.subheader("🧾 Evaluación técnica")

    st.markdown(f"""
    <div class="{eval_class}">
        <h2>Evaluación: {evaluacion}</h2>
        <p><b>{opt_pct:.2f}%</b> del área está dentro del rango óptimo.</p>
        <p><b>{sob_pct:.2f}%</b> del área está sobre-aplicada.</p>
        <p><b>{sub_pct:.2f}%</b> del área está sub-aplicada.</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("📌 Recomendaciones")

    if evaluacion == "DEFICIENTE":
        st.warning("""
        La aplicación presenta baja uniformidad.  
        Se recomienda recalibrar el equipo, revisar caudal, velocidad de aplicación y solape entre pasadas.
        """)
    elif evaluacion == "REGULAR":
        st.info("""
        La aplicación es aceptable, pero requiere ajustes para mejorar la uniformidad.
        """)
    else:
        st.success("""
        La aplicación presenta buena uniformidad dentro del rango objetivo.
        """)

else:
    st.info("Carga un shapefile comprimido en .zip para comenzar.")
