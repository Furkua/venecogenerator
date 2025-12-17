import streamlit as st
from generator import generate_names

st.set_page_config(page_title="Nombre Veneco Generator", layout="centered")

st.title("Generador de nombres estilo venezolano")
st.caption("Combina mamá + papá con tres modos: Normal, Veneco, Cágate la vida.")

with st.form("form"):
    col1, col2 = st.columns(2)
    with col1:
        father = st.text_input("Nombre del papá", value="Padre").strip()
    with col2:
        mother = st.text_input("Nombre de la mamá", value="Madre").strip()

    col3, col4 = st.columns(2)
    with col3:
        gender = st.radio("Género", options=["M", "H"], horizontal=True, help="M = mujer, H = hombre")
    with col4:
        mode = st.selectbox("Modo", options=["Normal", "Veneco", "Cágate la vida"])

    k = st.slider("Cantidad de resultados", min_value=1, max_value=5, value=3, step=1)
    seed = st.number_input("Semilla (para repetir resultados)", min_value=0, max_value=10_000_000, value=42, step=1)

    submitted = st.form_submit_button("Generar")

if submitted:
    if not father or not mother:
        st.error("Completa ambos nombres (papá y mamá).")
    else:
        names = generate_names(
            father=father,
            mother=mother,
            gender=gender,
            mode=mode,
            k=int(k),
            seed=int(seed),
        )

        if not names:
            st.warning("No se pudieron generar nombres con esos parámetros.")
        else:
            st.subheader("Resultados")
            for i, n in enumerate(names, start=1):
                st.write(f"{i}. {n}")

st.divider()
st.caption("Nota: el modo cágate la vida está diseñado para maximizar el desagrado de tu nombre fuera de Venezuela (ojala te deporten).")
