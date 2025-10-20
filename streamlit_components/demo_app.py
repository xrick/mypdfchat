import streamlit as st

from streamlit_components import st_rich_text_area


st.set_page_config(page_title="Rich Text Area Demo", page_icon="📝", layout="centered")
st.title("📝 Rich Text Area – Custom Streamlit Component")
st.caption("Demonstrates a customizable rich‑text, multi‑line editor.")

with st.sidebar:
    st.header("Editor Options")
    height = st.slider("Editor height (px)", 120, 600, 260, step=20)
    show_toolbar = st.checkbox("Show toolbar", value=True)
    placeholder = st.text_input("Placeholder", value="Type here with rich formatting…")

st.write("Try bold, italic, lists, headings, and links.")

value = st_rich_text_area(
    label="Rich Text Input",
    value="<p><b>Hello</b> from <i>custom</i> <u>component</u>!</p>",
    height=height,
    placeholder=placeholder,
    toolbar=show_toolbar,
    key="demo_rich_text",
)

st.subheader("Returned HTML")
st.code(value or "", language="html")

st.subheader("Preview")
st.write(value, unsafe_allow_html=True)

