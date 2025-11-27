import streamlit as st

st.set_page_config(page_title="Test", layout="wide")

st.title("Simple Test")
st.write("If you see this without flashing, the basic app works.")

if st.button("Click me"):
    st.success("Button clicked!")
