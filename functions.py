import os
import streamlit as st
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms.ollama import Ollama
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

from configuration import DATA_PATH, CHROMA_PATH, PROMPT_TEMPLATE


def get_embeddings():
    return OllamaEmbeddings(model="nomic-embed-text")


def load_documents():
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    documents_loader = PyPDFDirectoryLoader(DATA_PATH)
    loaded_docs = documents_loader.load()
    st.write(f"Debug: Loaded {len(loaded_docs)} documents from {DATA_PATH}")
    return loaded_docs


def split_document(document):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False,
    )
    return splitter.split_documents(document)


def calculate_chunk_ids(chunks):
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        chunk.metadata["id"] = chunk_id

    return chunks


def add_to_chroma(chunks):
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embeddings()
    )

    chunks_with_ids = calculate_chunk_ids(chunks)

    existing_items = db.get(include=[])
    existing_ids = set(existing_items["ids"])

    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    if len(new_chunks):
        st.info(f"👉 Adding {len(new_chunks)} new document chunks to the database...")
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        db.add_documents(new_chunks, ids=new_chunk_ids)
        st.success("✅ Documents added successfully.")
    else:
        st.info("✅ No new documents to add (database is up to date).")


def get_available_sources():
    if not os.path.exists(CHROMA_PATH):
        return []

    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embeddings())
    all_data = db.get()
    sources = set([meta.get('source') for meta in all_data['metadatas'] if meta.get('source')])
    return list(sources)


def query_rag(query_text, selected_pdfs=None):
    embedding_function = get_embeddings()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    results = db.similarity_search_with_score(query_text, k=10)

    if selected_pdfs:
        selected_norms = [os.path.normpath(p) for p in selected_pdfs]

        filtered_results = []
        for doc, score in results:
            doc_source = os.path.normpath(doc.metadata.get("source", ""))
            if doc_source in selected_norms:
                filtered_results.append((doc, score))
        results = filtered_results

    results = results[:5]

    if not results:
        return "No relevant context found in the selected documents.", []

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])

    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    with st.expander("View Constructed Prompt"):
        st.text(prompt)

    model = Ollama(model="mistral")
    response_text = model.invoke(prompt)

    sources = [doc.metadata.get("id", None) for doc, _score in results]

    return response_text, sources