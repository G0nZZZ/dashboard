import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder

# Configuración de la página
st.set_page_config(
    page_title="Real Estate Analytics",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .metric-card {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 10px;
        text-align: center;
    }
    .big-number {
        font-size: 24px;
        font-weight: bold;
        color: #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# Función para la conexión a la base de datos
@st.cache_resource
def get_database_connection():
    try:
        credentials = st.secrets["postgres"]
        connection_string = (
            f"postgresql://{credentials['user']}:{credentials['password']}@"
            f"{credentials['host']}:{credentials['port']}/{credentials['database']}"
        )
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {str(e)}")
        return None

# Función para cargar datos
@st.cache_data
def load_data():
    engine = get_database_connection()
    if engine is None:
        return pd.DataFrame()
    try:
        df = pd.read_sql('SELECT * FROM properties', engine)
        # Convertir coordenadas a lat/lon si existen
        if 'Coordinates' in df.columns:
            df[['lat', 'lon']] = df['Coordinates'].str.split(',', expand=True).astype(float, errors='ignore')
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
        return pd.DataFrame()

# Cargar datos
df = load_data()

# Validar datos cargados
if df.empty:
    st.error("No se pudieron cargar datos. Verifique la conexión a la base de datos.")
    st.stop()

# Manejo de valores nulos
df['Occupancy'] = df['Occupancy'].fillna('Unknown').fillna('Sin especificar')
df['Price'] = df['Price'].fillna(0)
df['Rentability Index'] = df['Rentability Index'].fillna(0)
df['Payback Period'] = df['Payback Period'].fillna(0)

# Sidebar con filtros
st.sidebar.title("Filtros")

# Filtros dinámicos
comarca = st.sidebar.selectbox(
    "Comarca",
    options=["Todas"] + sorted(df['Comarca'].dropna().unique().tolist())
)

# Crear un expander para los barrios
with st.sidebar.expander("Seleccionar Barrios"):
    # Checkbox para seleccionar/deseleccionar todos
    select_all_barrios = st.checkbox("Seleccionar todos los barrios")

    # Lista de barrios disponibles
    barrios_disponibles = sorted(df['Barrio'].dropna().unique().tolist())
    
    # Crear un checkbox para cada barrio
    barrios_seleccionados = []
    for barrio in barrios_disponibles:
        # Si es Shinjuku, marcarlo por defecto
        default_value = True if barrio == "Shinjuku" else select_all_barrios
        if st.checkbox(barrio, value=default_value, key=f"barrio_{barrio}"):
            barrios_seleccionados.append(barrio)

    # Asegurarse de que al menos un barrio está seleccionado
    if not barrios_seleccionados:
        st.warning("Por favor selecciona al menos un barrio")
        if "Shinjuku" in barrios_disponibles:
            barrios_seleccionados = ["Shinjuku"]
        else:
            barrios_seleccionados = [barrios_disponibles[0]]

ocupacion = st.sidebar.multiselect(
    "Estado de Ocupación",
    options=sorted(df['Occupancy'].unique().tolist()),
    default=sorted(df['Occupancy'].unique().tolist())
)

# Convertir los valores mínimos y máximos en enteros
min_price = int(df['Price'].min() or 0)
max_price = int(df['Price'].max() or 0)

# Crear rangos logarítmicos para los precios
# Usamos numpy logspace para crear una secuencia logarítmica
# Añadimos 1 al precio mínimo para evitar log(0)
log_min = np.log10(min_price + 1)
log_max = np.log10(max_price)
num_steps = 100  # Número de pasos en el slider

# Crear los valores logarítmicos y redondearlos a números enteros
price_values = np.round(np.logspace(log_min, log_max, num_steps)).astype(int)
# Asegurarse de que el precio mínimo y máximo estén incluidos
price_values = np.unique(np.append(price_values, [min_price, max_price]))
# Ordenar los valores
price_values.sort()

# Crear las opciones del slider con el formato correcto
price_options = [f"¥{i:,.0f}" for i in price_values]

# Encontrar los índices más cercanos para los valores por defecto
min_price_idx = np.searchsorted(price_values, min_price)
max_price_idx = np.searchsorted(price_values, max_price)

# Usar los valores formateados correspondientes a estos índices
default_min_price = price_options[min_price_idx]
default_max_price = price_options[max_price_idx - 1]  # -1 para asegurarnos de que está en el rango

# Configurar el select_slider con opciones formateadas
price_range = st.sidebar.select_slider(
    "Rango de Precio (¥)",
    options=price_options,
    value=(default_min_price, default_max_price)
)

# Parsear el rango seleccionado de vuelta a enteros
selected_min_price = int(price_range[0].replace("¥", "").replace(",", ""))
selected_max_price = int(price_range[1].replace("¥", "").replace(",", ""))



# Aplicar filtros
mask = df['Price'].between(selected_min_price, selected_max_price)
mask &= df['Occupancy'].isin(ocupacion)
if comarca != "Todas":
    mask &= (df['Comarca'] == comarca)
if barrios_seleccionados:  # Si hay barrios seleccionados
    mask &= df['Barrio'].isin(barrios_seleccionados)

filtered_df = df[mask]

# Título principal
st.title("🏠 Análisis de Propiedades Inmobiliarias")

# Métricas principales
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Precio Promedio",
        f"¥{filtered_df['Price'].mean():,.0f}" if not filtered_df.empty else "N/A",
        f"{filtered_df['Price'].mean() / df['Price'].mean() - 1:+.1%}" if not filtered_df.empty else "N/A"
    )

with col2:
    st.metric(
        "Rentabilidad Media",
        f"{filtered_df['Rentability Index'].mean():.2%}" if not filtered_df.empty else "N/A",
        f"{filtered_df['Rentability Index'].mean() / df['Rentability Index'].mean() - 1:+.1%}" if not filtered_df.empty else "N/A"
    )

with col3:
    st.metric(
        "Propiedades",
        f"{len(filtered_df):,}" if not filtered_df.empty else "0",
        f"{len(filtered_df) / len(df) - 1:+.1%}" if not filtered_df.empty else "N/A"
    )

with col4:
    st.metric(
        "Periodo de Recuperación",
        f"{filtered_df['Payback Period'].mean():.1f} años" if not filtered_df.empty else "N/A",
        f"{filtered_df['Payback Period'].mean() / df['Payback Period'].mean() - 1:+.1%}" if not filtered_df.empty else "N/A"
    )

# Gráficos
st.header("Análisis de Mercado")

tab1, tab2, tab3 = st.tabs(["Distribución", "Correlaciones", "Mapa"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fig_price = px.histogram(
            filtered_df,
            x="Price",
            nbins=50,
            title="Distribución de Precios",
            labels={"Price": "Precio (¥)", "count": "Cantidad"}
        )
        fig_price.update_layout(showlegend=False)
        st.plotly_chart(fig_price, use_container_width=True)
    with col2:
        fig_rent = px.histogram(
            filtered_df,
            x="Rentability Index",
            nbins=50,
            title="Distribución de Rentabilidad",
            labels={"Rentability Index": "Índice de Rentabilidad", "count": "Cantidad"}
        )
        fig_rent.update_layout(showlegend=False)
        st.plotly_chart(fig_rent, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        fig_scatter = px.scatter(
            filtered_df,
            x="Price",
            y="Rentability Index",
            color="Occupancy",
            title="Rentabilidad vs Precio",
            labels={"Price": "Precio (¥)", "Rentability Index": "Índice de Rentabilidad", "Occupancy": "Ocupación"}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    with col2:
        fig_size = px.scatter(
            filtered_df,
            x="Size",
            y="Price",
            color="Occupancy",
            title="Precio vs Tamaño",
            labels={"Size": "Tamaño (m²)", "Price": "Precio (¥)", "Occupancy": "Ocupación"}
        )
        st.plotly_chart(fig_size, use_container_width=True)

with tab3:
    if not filtered_df.empty:
        fig_map = px.scatter_mapbox(
            filtered_df,
            lat='lat',
            lon='lon',
            color='Rentability Index',
            size='Price',
            hover_name='Address',
            hover_data={'Price': ':,.0f', 'Rentability Index': ':.2%', 'Payback Period': ':.1f'},
            color_continuous_scale='Viridis',
            zoom=10,
            title="Mapa de Propiedades",
            mapbox_style="open-street-map"
        )
        fig_map.update_layout(
            height=600,
            mapbox=dict(center=dict(lat=filtered_df['lat'].mean(), lon=filtered_df['lon'].mean()))
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning("No hay propiedades que coincidan con los filtros seleccionados.")

if 'column_order' not in st.session_state:
    st.session_state.column_order = ['Address', 'Price', 'Size', 'Rentability Index', 'Payback Period', 'Link']


# Tabla de datos detallados
st.header("Propiedades Detalladas")

# Seleccionar columnas a mostrar
# Configurar AgGrid
gb = GridOptionsBuilder.from_dataframe(df)

# Renderizador JavaScript para la columna 'Link'
link_renderer = JsCode('''
function(params) {
    if (params.value) {
        return `<a href="${params.value}" target="_blank" style="text-decoration: none; color: #1f77b4;">Abrir enlace</a>`;
    } else {
        return '';
    }
}
''')

# Configuración de la columna 'Link' con el renderizador
gb.configure_column("Link", cellRenderer=link_renderer)

# Configurar columnas
gb.configure_default_column(resizable=True, suppressMovable=False)
grid_options = gb.build()

# Renderizar la tabla con AgGrid
AgGrid(
    df,
    gridOptions=grid_options,
    allow_unsafe_jscode=True,  # Permitir JavaScript personalizado
    theme="streamlit",
    enable_enterprise_modules=False,
    fit_columns_on_grid_load=True
)