import streamlit as st
from generator import generate_names

st.set_page_config(page_title="Generador de nombres", page_icon="🧩", layout="centered")

st.title("Generador de nombres estilo venezolano")
st.caption("Crea nombres combinando mamá + papá, con tres niveles de estilo.")

with st.form("form"):
    col1, col2 = st.columns(2)
    with col1:
        father = st.text_input("Nombre del papá", value="padre").strip()
    with col2:
        mother = st.text_input("Nombre de la mamá", value="madre").strip()

    col3, col4 = st.columns(2)
    with col3:
        gender = st.radio("Género", options=["M", "H"], horizontal=True)
    with col4:
        mode = st.selectbox("Modo", options=["Normal", "Veneco", "Worst-case"])

    k = st.slider("Cantidad de resultados", min_value=5, max_value=50, value=20, step=5)
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
            st.warning("No se pudieron generar nombres con esos parámetros. Prueba con otros nombres o cambia el modo.")
        else:
            st.subheader("Resultados")
            st.write("\n".join([f"{i+1}. {n}" for i, n in enumerate(names)]))

st.divider()
st.caption("Nota: el modo Worst-case está diseñado para maximizar fricción fuera de Venezuela (ortografía/pronunciación/sistemas).")
