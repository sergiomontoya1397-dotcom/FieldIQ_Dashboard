import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import tempfile
import zipfile
import os
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

st.title("🌱 Dashboard de Fertilización")

# Parámetros
st.sidebar.header("⚙️ Parámetros")

objetivo = st.sidebar.number_input(
    "Dosis objetivo",
    value=150
)

tolerancia = st.sidebar.slider(
    "Tolerancia %",
    1,
    20,
    5
)

uploaded_file = st.file_uploader(
    "Sube tu shapefile en .zip",
    type=["zip"]
)

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

    if shp_file:

        gdf_original = gpd.read_file(shp_file, engine="pyogrio")

        if "AppliedRat" not in gdf_original.columns:
            st.error("No se encontró la columna 'AppliedRat' en el shapefile.")
            st.write("Columnas disponibles:")
            st.write(list(gdf_original.columns))
            st.stop()

        st.success("Shapefile cargado correctamente")

        # Guardar CRS original para mapa
        gdf_mapa = gdf_original.to_crs(epsg=4326)

        # Reproyectar para cálculo de área
        gdf_area = gdf_original.to_crs(epsg=3857)
        gdf_area["Area_ha"] = gdf_area.geometry.area / 10000

        # Pasar área al mapa
        gdf_mapa["Area_ha"] = gdf_area["Area_ha"]
        gdf_mapa["AppliedRat"] = pd.to_numeric(
            gdf_mapa["AppliedRat"],
            errors="coerce"
        )

        gdf_mapa = gdf_mapa.dropna(subset=["AppliedRat"])

        # Límites
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

        # Resumen
        resumen = (
            gdf_mapa.groupby("Categoria")["Area_ha"]
            .sum()
            .reset_index()
        )

        total = resumen["Area_ha"].sum()
        resumen["Porcentaje"] = resumen["Area_ha"] / total * 100

        # Asegurar orden
        orden = ["Sub-aplicado", "Óptimo", "Sobre-aplicado"]
        resumen["Categoria"] = pd.Categorical(
            resumen["Categoria"],
            categories=orden,
            ordered=True
        )
        resumen = resumen.sort_values("Categoria")

        # KPIs
        st.subheader("📊 Resumen de aplicación")

        col1, col2, col3, col4 = st.columns(4)

        def valor_categoria(cat, campo):
            fila = resumen[resumen["Categoria"] == cat]
            if fila.empty:
                return 0
            return float(fila[campo].iloc[0])

        sub_area = valor_categoria("Sub-aplicado", "Area_ha")
        opt_area = valor_categoria("Óptimo", "Area_ha")
        sob_area = valor_categoria("Sobre-aplicado", "Area_ha")

        sub_pct = valor_categoria("Sub-aplicado", "Porcentaje")
        opt_pct = valor_categoria("Óptimo", "Porcentaje")
        sob_pct = valor_categoria("Sobre-aplicado", "Porcentaje")

        col1.metric("Área total", f"{total:.2f} ha")
        col2.metric("Sub-aplicado", f"{sub_area:.2f} ha", f"{sub_pct:.2f}%")
        col3.metric("Óptimo", f"{opt_area:.2f} ha", f"{opt_pct:.2f}%")
        col4.metric("Sobre-aplicado", f"{sob_area:.2f} ha", f"{sob_pct:.2f}%")

        # Mapa
        st.subheader("🗺️ Mapa de aplicación")

        colores = {
            "Sub-aplicado": "red",
            "Óptimo": "yellow",
            "Sobre-aplicado": "green"
        }

        centro = [
            gdf_mapa.geometry.centroid.y.mean(),
            gdf_mapa.geometry.centroid.x.mean()
        ]

        m = folium.Map(
            location=centro,
            zoom_start=17,
            tiles="Esri.WorldImagery"
        )

        folium.GeoJson(
            gdf_mapa,
            style_function=lambda feature: {
                "fillColor": colores.get(
                    feature["properties"]["Categoria"],
                    "gray"
                ),
                "color": "black",
                "weight": 0.4,
                "fillOpacity": 0.75,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["AppliedRat", "Categoria", "Area_ha"],
                aliases=["Dosis:", "Categoría:", "Área ha:"],
                localize=True
            )
        ).add_to(m)

        st_folium(m, width=1200, height=600)

        # Gráfico y tabla
        col_graf, col_tabla = st.columns([1, 1])

        with col_graf:
            st.subheader("🥧 Distribución porcentual")

            fig = px.pie(
                resumen,
                values="Area_ha",
                names="Categoria",
                color="Categoria",
                color_discrete_map={
                    "Sub-aplicado": "red",
                    "Óptimo": "yellow",
                    "Sobre-aplicado": "green"
                }
            )

            st.plotly_chart(fig, use_container_width=True)

        with col_tabla:
            st.subheader("📋 Tabla de porcentajes")

            tabla = resumen.copy()
            tabla["Área (ha)"] = tabla["Area_ha"].round(3)
            tabla["% del total"] = tabla["Porcentaje"].round(2)

            tabla = tabla[["Categoria", "Área (ha)", "% del total"]]
            st.dataframe(tabla, use_container_width=True)

    else:
        st.error("No se encontró archivo .shp dentro del ZIP.")
else:
    st.info("Carga un shapefile comprimido en .zip para comenzar.")
