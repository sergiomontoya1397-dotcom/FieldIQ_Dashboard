import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import tempfile
import zipfile
import os

st.set_page_config(layout="wide")

st.title("🌱 Dashboard de Fertilización")

# Upload ZIP
uploaded_file = st.file_uploader(
    "Sube tu shapefile en .zip",
    type=["zip"]
)

if uploaded_file:

    # carpeta temporal
    temp_dir = tempfile.mkdtemp()

    zip_path = os.path.join(temp_dir, uploaded_file.name)

    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # extraer zip
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # buscar .shp
    shp_file = None

    for file in os.listdir(temp_dir):
        if file.endswith(".shp"):
            shp_file = os.path.join(temp_dir, file)

    if shp_file:

        gdf = gpd.read_file(shp_file)

        st.success("Shapefile cargado correctamente")

        # mostrar columnas
        st.write("Columnas detectadas:")
        st.write(gdf.columns)

        # mostrar tabla
        st.dataframe(gdf.head())

    else:
        st.error("No se encontró archivo .shp")
