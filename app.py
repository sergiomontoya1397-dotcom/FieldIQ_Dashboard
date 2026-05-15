import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import tempfile
import zipfile
import os
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Field-IQ Dashboard", layout="wide")

st.markdown("""
<style>
.report-title {
    background:#064d1b;
    color:white;
    text-align:center;
    padding:18px;
    border-radius:10px;
    font-size:36px;
    font-weight:800;
}
.section-title {
    background:#064d1b;
    color:white;
    padding:8px 14px;
    border-radius:8px;
    font-weight:700;
    text-align:center;
}
.card {
    background:white;
    border-radius:12px;
    padding:18px;
    box-shadow:0 3px 12px rgba(0,0,0,0.12);
    border:1px solid #ddd;
    margin-bottom:14px;
}
.legend-row {
    display:flex;
    align-items:center;
    gap:10px;
    margin:10px 0;
    font-size:16px;
}
.color-box {
    width:30px;
    height:24px;
    border:1px solid #555;
}
.eval-good {
    background:#e8f5e9;
    border:2px solid #2e7d32;
    border-radius:14px;
    padding:18px;
    color:#1b5e20;
    text-align:center;
}
.eval-bad {
    background:#ffebee;
    border:2px solid #c62828;
    border-radius:14px;
    padding:18px;
    color:#b71c1c;
    text-align:center;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.header("⚙️ Parámetros")
objetivo = st.sidebar.number_input("Dosis objetivo", value=150)
nombre_lote = st.sidebar.text_input("Nombre del lote", value="Lote 65–66")
unidad = st.sidebar.text_input("Unidad", value="L/ha")

uploaded_file = st.file_uploader("Sube tu shapefile en .zip", type=["zip"])

colores = {
    "Clase 3: < -10%": "#FF0000",
    "Clase 2: -5% a -10%": "#FFFF00",
    "Clase 1: ±5%": "#22C928",
    "Clase 4: +5% a +10%": "#29B6F6",
    "Clase 5: > +10%": "#000080",
}

orden = [
    "Clase 3: < -10%",
    "Clase 2: -5% a -10%",
    "Clase 1: ±5%",
    "Clase 4: +5% a +10%",
    "Clase 5: > +10%",
]

def nombres_rangos(objetivo):
    return {
        "Clase 3: < -10%": f"< {objetivo * 0.90:.1f}",
        "Clase 2: -5% a -10%": f"{objetivo * 0.90:.1f} - {objetivo * 0.95:.1f}",
        "Clase 1: ±5%": f"{objetivo * 0.95:.1f} - {objetivo * 1.05:.1f}",
        "Clase 4: +5% a +10%": f"{objetivo * 1.05:.1f} - {objetivo * 1.10:.1f}",
        "Clase 5: > +10%": f"> {objetivo * 1.10:.1f}",
    }

nombres_cortos = nombres_rangos(objetivo)

def cargar_shapefile(uploaded_file):
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

    if shp_file is None:
        st.error("No se encontró archivo .shp dentro del ZIP.")
        st.stop()

    return gpd.read_file(shp_file, engine="pyogrio")

def clasificar(valor):
    if valor < objetivo * 0.90:
        return "Clase 3: < -10%"
    elif valor < objetivo * 0.95:
        return "Clase 2: -5% a -10%"
    elif valor <= objetivo * 1.05:
        return "Clase 1: ±5%"
    elif valor <= objetivo * 1.10:
        return "Clase 4: +5% a +10%"
    else:
        return "Clase 5: > +10%"

def crear_mapa(gdf_mapa):
    centro = [
        gdf_mapa.geometry.centroid.y.mean(),
        gdf_mapa.geometry.centroid.x.mean()
    ]

    mapa = folium.Map(
        location=centro,
        zoom_start=17,
        tiles="Esri.WorldImagery"
    )

    folium.GeoJson(
        gdf_mapa,
        style_function=lambda feature: {
            "fillColor": colores.get(feature["properties"]["Categoria"], "gray"),
            "color": "black",
            "weight": 0.35,
            "fillOpacity": 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["AppliedRat", "Rango", "Area_ha"],
            aliases=["Dosis:", "Rango:", "Área ha:"],
            localize=True
        )
    ).add_to(mapa)

    return mapa

def mostrar_leyenda():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">LEYENDA</div>', unsafe_allow_html=True)
    st.markdown("### Rango de dosis")

    for cat in orden:
        color = colores[cat]
        rango = nombres_cortos[cat]
        st.markdown(
            f"""
            <div class="legend-row">
                <div class="color-box" style="background:{color};"></div>
                <span>{rango}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file:
    gdf_original = cargar_shapefile(uploaded_file)

    if "AppliedRat" not in gdf_original.columns:
        st.error("No se encontró la columna 'AppliedRat'.")
        st.write("Columnas disponibles:")
        st.write(list(gdf_original.columns))
        st.stop()

    gdf_mapa = gdf_original.to_crs(epsg=4326)
    gdf_area = gdf_original.to_crs(epsg=3857)

    gdf_mapa["Area_ha"] = gdf_area.geometry.area / 10000
    gdf_mapa["AppliedRat"] = pd.to_numeric(gdf_mapa["AppliedRat"], errors="coerce")
    gdf_mapa = gdf_mapa.dropna(subset=["AppliedRat"])

    gdf_mapa["Categoria"] = gdf_mapa["AppliedRat"].apply(clasificar)
    gdf_mapa["Rango"] = gdf_mapa["Categoria"].map(nombres_cortos)

    resumen = gdf_mapa.groupby("Categoria")["Area_ha"].sum().reset_index()
    total = resumen["Area_ha"].sum()
    resumen["Porcentaje"] = resumen["Area_ha"] / total * 100

    resumen["Categoria"] = pd.Categorical(
        resumen["Categoria"],
        categories=orden,
        ordered=True
    )

    resumen = resumen.sort_values("Categoria")
    resumen["Rango"] = resumen["Categoria"].map(nombres_cortos)

    def get_pct(cat):
        fila = resumen[resumen["Categoria"] == cat]
        return 0 if fila.empty else float(fila["Porcentaje"].iloc[0])

    opt_pct = get_pct("Clase 1: ±5%")
    sub_pct = get_pct("Clase 3: < -10%") + get_pct("Clase 2: -5% a -10%")
    sobre_pct = get_pct("Clase 4: +5% a +10%") + get_pct("Clase 5: > +10%")

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

    fig = px.pie(
        resumen,
        values="Area_ha",
        names="Rango",
        color="Categoria",
        color_discrete_map=colores,
        hole=0.25
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent"
    )

    tabla = resumen.copy()
    tabla["Área (ha)"] = tabla["Area_ha"].round(3)
    tabla["% del total"] = tabla["Porcentaje"].round(2)
    tabla = tabla[["Rango", "Área (ha)", "% del total"]]

    tab1, tab2 = st.tabs(["📊 Dashboard interactivo", "📄 Reporte para cliente"])

    with tab1:
        st.title("🌱 Aplicación Field-IQ")
        st.success("Shapefile cargado correctamente")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Área total", f"{total:.2f} ha")
        c2.metric("Dentro de ±5%", f"{opt_pct:.2f}%")
        c3.metric("Sub-aplicado", f"{sub_pct:.2f}%")
        c4.metric("Sobre-aplicado", f"{sobre_pct:.2f}%")

        st.subheader("🗺️ Mapa de aplicación")
        st_folium(
            crear_mapa(gdf_mapa),
            width=1200,
            height=600,
            key="mapa_dashboard"
        )

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🥧 Distribución porcentual")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📋 Tabla de porcentajes")
            st.dataframe(tabla, use_container_width=True)

            csv = tabla.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar tabla CSV",
                csv,
                "tabla_porcentajes.csv",
                "text/csv"
            )

    with tab2:
        st.markdown(
            f'<div class="report-title">{nombre_lote.upper()} — DOSIS {objetivo} {unidad}</div>',
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        left, right = st.columns([1, 3])

        with left:
            mostrar_leyenda()

            st.markdown(
                f"""
                <div class="card">
                    <div class="section-title">INFORMACIÓN</div>
                    <p><b>Lote:</b> {nombre_lote}</p>
                    <p><b>Dosis aplicada:</b> {objetivo} {unidad}</p>
                    <p><b>Unidad:</b> {unidad}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        with right:
            st.markdown(
                '<div class="section-title">MAPA DE DISTRIBUCIÓN DE DOSIS</div>',
                unsafe_allow_html=True
            )

            st_folium(
                crear_mapa(gdf_mapa),
                width=950,
                height=520,
                key="mapa_reporte"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col_g, col_t = st.columns(2)

        with col_g:
            st.markdown(
                '<div class="section-title">DISTRIBUCIÓN PORCENTUAL POR RANGO</div>',
                unsafe_allow_html=True
            )

            st.plotly_chart(fig, use_container_width=True)

        with col_t:
            st.markdown(
                '<div class="section-title">TABLA DE PORCENTAJES DE ÁREA POR RANGO</div>',
                unsafe_allow_html=True
            )

            st.dataframe(tabla, use_container_width=True)
            st.markdown(f"### TOTAL: **{total:.3f} ha**")

        st.markdown("<br>", unsafe_allow_html=True)

        r1, r2 = st.columns([2, 1])

        with r1:
            st.markdown(
                f"""
                <div class="card">
                    <div class="section-title">RESUMEN E INTERPRETACIÓN</div>
                    <ul>
                        <li><b>{opt_pct:.2f}%</b> del área está dentro del rango óptimo ±5%.</li>
                        <li><b>{sub_pct:.2f}%</b> del área está sub-aplicada.</li>
                        <li><b>{sobre_pct:.2f}%</b> del área está sobre-aplicada.</li>
                        <li>La evaluación se basa en el porcentaje dentro del rango óptimo.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True
            )

        with r2:
            st.markdown(
                f"""
                <div class="{eval_class}">
                    <h4>CALIDAD DE APLICACIÓN</h4>
                    <h1>{evaluacion}</h1>
                </div>
                """,
                unsafe_allow_html=True
            )

else:
    st.info("Carga un shapefile comprimido en .zip para comenzar.")
