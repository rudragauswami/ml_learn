import os
import glob
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

DATA_DIR = "data"
DB_DIR = ".chroma_db"

def main():
    print(f"Loading documents from {DATA_DIR}...")
    # Find all txt files in the data directory
    txt_files = glob.glob(os.path.join(DATA_DIR, "*.txt"))
    if not txt_files:
        print(f"No .txt documents found in {DATA_DIR}/. Please add some!")
        return

    docs = []
    # Load all the text files
    for file_path in txt_files:
        loader = TextLoader(file_path, encoding='utf-8')
        docs.extend(loader.load())
    
    print(f"Loaded {len(docs)} document(s).")
    
    # Split text into chunks
    # We chunk because providing a massive 100-page document perfectly to an LLM context window usually fails.
    # Chunking splits it into specific, search-friendly paragraphs.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Split documents into {len(chunks)} chunks.")

    # Generate Embeddings & Save to Vector Database
    # Embeddings translate textual meaning into coordinate maps (vectors).
    # We use HuggingFace (locally) to avoid API charges during the embedding stage.
    print("Downloading/Loading Embedding Model (all-MiniLM-L6-v2)...")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print(f"Creating ChromaDB Vector Store in {DB_DIR}...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=DB_DIR
    )

    print("Success! The data has been ingested and the local vector database is ready.")

if __name__ == "__main__":
    main() 
