import streamlit as st
import os
import shutil
from langchain_community.vectorstores import Chroma
from configuration import DATA_PATH, CHROMA_PATH
from functions import load_documents, split_document, add_to_chroma, get_available_sources, query_rag, get_embeddings

st.set_page_config(page_title="RAG Search", layout="wide")

if "db_updated" not in st.session_state:
    st.session_state.db_updated = False

with st.sidebar:
    st.subheader("Data Source")

    uploaded_files = st.file_uploader(
        "Add new documents (PDF)",
        accept_multiple_files=True,
        type=["pdf"]
    )

    data_folder_has_files = os.path.exists(DATA_PATH) and len(os.listdir(DATA_PATH)) > 0

    if st.button("Update Database", use_container_width=True):
        if uploaded_files:
            if not os.path.exists(DATA_PATH):
                os.makedirs(DATA_PATH)

            for uploaded_file in uploaded_files:
                file_path = os.path.join(DATA_PATH, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

            st.success(f"Saved {len(uploaded_files)} new file(s).")

        if uploaded_files or data_folder_has_files:
            with st.spinner("Processing..."):
                documents = load_documents()
                chunks = split_document(documents)
                add_to_chroma(chunks)
                st.session_state.db_updated = True
                st.rerun()
        else:
            st.warning("No files to process.")

    st.divider()

    if st.button("Reset", type="secondary", use_container_width=True):
        if os.path.exists(CHROMA_PATH):
            try:
                db = Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embeddings())
                ids = db.get()["ids"]
                if ids:
                    db.delete(ids)
            except Exception:
                pass

        if os.path.exists(DATA_PATH):
            try:
                shutil.rmtree(DATA_PATH)
            except Exception:
                pass

        st.session_state.db_updated = True
        st.success("System cleared.")
        st.rerun()

st.title("Knowledge Base")

available_pdfs = get_available_sources()

if available_pdfs:
    col1, col2 = st.columns([3, 1])
    with col1:
        query_text = st.text_input("Search query", placeholder="Ask a question about your documents...")
    with col2:
        selected_pdfs = st.multiselect(
            "Filter context",
            available_pdfs,
            default=available_pdfs,
            label_visibility="visible"
        )

    st.divider()

    if query_text:
        with st.spinner("Generating response..."):
            response, sources = query_rag(query_text, selected_pdfs)

            st.markdown(response)

            with st.expander("View Sources"):
                st.write(sources)
else:
    st.info("Database is empty. Please add documents in the sidebar.")