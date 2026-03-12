import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Radar Auto & Analiză", layout="wide", page_icon="🏎️")

st.title("🏎️ Radar Auto: Analiză & Best Value")
st.markdown("Analizează piața auto și găsește cele mai subevaluate anunțuri pe baza datelor tale.")


# --- ÎNCĂRCAREA DATELOR ---
@st.cache_data
def load_data():

    return pd.read_excel('processed_listings.xlsx')

df = load_data()

# --- SIDEBAR PENTRU FILTRE ---
st.sidebar.header("🔍 Filtrează Baza de Date")

# Filtru cascadat: Selectezi Marca, apoi se updateaza Modelele
brand_options = sorted(df['Brand'].dropna().unique())
selected_brands = st.sidebar.multiselect("Marcă", brand_options, default=brand_options[:3])

# Filtram modelele disponibile pe baza marcilor selectate
available_models = df[df['Brand'].isin(selected_brands)]['Model'].dropna().unique() if selected_brands else df[
    'Model'].unique()
selected_models = st.sidebar.multiselect("Model", sorted(available_models), default=[])

year_min, year_max = st.sidebar.slider("An de fabricație", int(df['year'].min()), int(df['year'].max()), (2015, 2023))
price_max = st.sidebar.number_input("Preț maxim (EUR)", value=int(df['price'].max()), step=1000)
seller_types = st.sidebar.multiselect("Tip Vânzător", df['seller_type'].unique(), default=df['seller_type'].unique())

# Aplicarea filtrelor globale
mask = (df['Brand'].isin(selected_brands)) & \
       (df['year'] >= year_min) & (df['year'] <= year_max) & \
       (df['price'] <= price_max) & \
       (df['seller_type'].isin(seller_types))

if selected_models:
    mask = mask & (df['Model'].isin(selected_models))

df_filtered = df[mask]

# --- METRICE PRINCIPALE ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Anunțuri Filtrate", f"{len(df_filtered):,}")
col2.metric("Preț Median", f"{df_filtered['price'].median():,.0f} €" if not df_filtered.empty else "N/A")
col3.metric("Rulaj Median", f"{df_filtered['mileage_km'].median():,.0f} km" if not df_filtered.empty else "N/A")
# Procentaj dealeri
dealer_pct = (len(df_filtered[df_filtered['seller_type'] == 'Dealer']) / len(
    df_filtered) * 100) if not df_filtered.empty else 0
col4.metric("% Vândute de Dealeri", f"{dealer_pct:.1f}%")

st.divider()

# --- TAB-URI ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Analiză Piață", "📍 Analiză Vânzători & Locație", "💎 Radar Chilipiruri (Best Value)", "Bonus ca mi s-a parut misto"])

with tab1:
    st.subheader("Dinamica Prețului și a Deprecierii")

    col_a, col_b = st.columns(2)
    with col_a:
        # Pret per An si Tip Combustibil
        fig1 = px.box(df_filtered, x="year", y="price", color="fuel_type",
                      title="Evoluția prețului pe ani, după combustibil")
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        # Corelatia Pret vs Rulaj
        fig2 = px.scatter(df_filtered, x="mileage_km", y="price", color="Brand",
                          opacity=0.6, hover_data=['Model', 'year', 'seller_type'],
                          title="Corelație: Preț vs. Kilometraj")
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.subheader("Influența Vânzătorului și a Locației asupra Prețului")
    col_c, col_d = st.columns(2)

    with col_c:
        # Vanzator privat vs dealer per marca
        fig3 = px.histogram(df_filtered, x="Brand", y="price", color="seller_type",
                            barmode="group", histfunc="avg",
                            title="Preț Mediu: Privat vs. Dealer pe Mărci")
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        # Top locatii
        top_locations = df_filtered.groupby('location').size().nlargest(10).reset_index(name='count')
        fig4 = px.bar(top_locations, x='location', y='count',
                      title="Volumul anunțurilor pe orașe/județe (Top 10)")
        st.plotly_chart(fig4, use_container_width=True)

with tab3:
    st.subheader("💎 Radar Chilipiruri - Cele mai subevaluate mașini")
    st.markdown(
        "Algoritmul caută mașini care sunt **mai ieftine** decât mediana pieței pentru modelul și anul respectiv, având **mai puțini kilometri**.")

    if not df_filtered.empty:
        # Creăm o copie pentru analiză
        df_eval = df_filtered.copy()

        # Calculăm mediana la nivel de Grup (Brand, Model, An)
        # Folosim groupby si transform pentru a aloca mediana calculata inapoi fiecarui rand
        df_eval['median_price_group'] = df_eval.groupby(['Brand', 'Model', 'year'])['price'].transform('median')
        df_eval['median_km_group'] = df_eval.groupby(['Brand', 'Model', 'year'])['mileage_km'].transform('median')

        # Filtram: Vrem masini sub pretul median SI cu rulaj sub cel median
        best_value = df_eval[
            (df_eval['price'] < df_eval['median_price_group'] * 0.95) &  # Cu cel putin 5% mai ieftin decat mediana
            (df_eval['mileage_km'] < df_eval['median_km_group']) &  # Rulaj mai mic decat mediana
            (df_eval['price'] > 1000)  # Excludem anomaliile (preturi setate la 1 EUR sau 100 EUR etc)
            ].copy()

        if not best_value.empty:
            # Calculam cat salvam
            best_value['discount_eur'] = best_value['median_price_group'] - best_value['price']

            # Sortam descrescator dupa cat salvam
            best_value = best_value.sort_values('discount_eur', ascending=False)

            # Selectam coloanele utile pentru afisare
            display_cols = ['image_url', 'Brand', 'Model', 'year', 'fuel_type', 'price', 'mileage_km', 'seller_type',
                            'location', 'discount_eur', 'url']
            df_display = best_value[display_cols]

            # Folosim configurarea avansata de la Streamlit pentru a face tabelul superb
            st.dataframe(
                df_display,
                column_config={
                    "image_url": st.column_config.ImageColumn("Poza", help="Imagine mașină"),
                    "Brand": "Marcă",
                    "year": "An",
                    "fuel_type": "Combustibil",
                    "price": st.column_config.NumberColumn("Preț (€)", format="%d €"),
                    "mileage_km": st.column_config.NumberColumn("Rulaj (km)", format="%d km"),
                    "discount_eur": st.column_config.NumberColumn("Sub media pieței", format="%d € 🔻"),
                    "seller_type": "Tip Vânzător",
                    "url": st.column_config.LinkColumn("Link", display_text="Vezi Anunț ↗")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info(
                "Nu au fost găsite oferte de tip 'Best Value' pentru filtrele curente. Încearcă să extinzi selecția (mai mulți ani, preț mai mare).")
    else:
        st.warning("Nu există date conform filtrelor selectate.")
with tab4:
    st.header("Graficul 4 — Heatmap: Matricea corelațiilor")

    coloane_numerice = ["price", "mileage_km", "year"]
    corr = df[coloane_numerice].corr().round(2)

    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.index,
        colorscale="RdBu",
        zmid=0,
        text=corr.values,
        texttemplate="%{text}",
        hoverongaps=False,
    ))

    fig.update_layout(title="Matricea corelațiilor")
    st.plotly_chart(fig, use_container_width=True)

    st.header("Graficul 5 — Sunburst: Structura ierarhică a datelor")

    fig = px.sunburst(
        df,
        path=["Brand", "Model"],
        values="price",
        color="Brand",
        title="Structura ierarhică a datelor (Brand -> Model)"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")