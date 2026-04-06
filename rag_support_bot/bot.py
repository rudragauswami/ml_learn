import os
import sys
from config import Config

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Ensure API Key is set
if not Config.GROQ_API_KEY or Config.GROQ_API_KEY == "your_groq_api_key_here":
    print("WARNING: You must set your GROQ_API_KEY inside the .env file.")
    sys.exit(1)

# Connect to the local Vector Database
print("Loading Local Database...")
embedding_model = HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL_NAME)
vector_store = Chroma(
    persist_directory=Config.CHROMA_DB_DIR,
    embedding_function=embedding_model
)

# Create a Retriever that searches the top 3 most relevant paragraphs
retriever = vector_store.as_retriever(search_kwargs={"k": 3})

# Initialize the LLM (Groq is very fast, using LLaMA-3)
print("Initializing LLM...")
llm = ChatGroq(
    model_name=Config.LLM_MODEL_NAME, 
    temperature=Config.LLM_TEMPERATURE
)

# Crafting the System Prompt
# The '{context}' placeholder is where LangChain injects the relevant chunks from the database
system_prompt = (
    "You are a helpful customer support bot for a hardware company.\n"
    "Use the following pieces of retrieved context to answer the user's question.\n"
    "If you don't know the answer or the context doesn't contain the answer, "
    "just say 'I don't have information on that' and politely decline to guess.\n"
    "DO NOT hallucinate or make up policies. Keep answers concise.\n"
    "----\nContext:\n{context}"
)

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

# Create the specific components: Document Chain & Retrieval Chain
question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

def print_separator():
    print("-" * 50)

def main():
    print("\n\n" + "="*50)
    print(" Welcome to the SupportMaster AI Bot ")
    print("="*50)
    print("Type 'quit' or 'exit' at any time to leave.")
    print_separator()

    while True:
        user_query = input("\nUser: ")
        
        if user_query.lower() in ["quit", "exit"]:
            print("SupportMaster: Goodbye!")
            break
        
        if not user_query.strip():
            continue
            
        print("SupportMaster: (thinking...)")
        
        # Invoke the RAG chain
        # 1. Matches text in ChromaDB using vector similarity
        # 2. Injects the matches into `qa_prompt`
        # 3. Sends prompt + matches to LLM
        # 4. LLM answers!
        response = rag_chain.invoke({"input": user_query})
        
        print("\nSupportMaster: " + response["answer"])
        print_separator()

if __name__ == "__main__":
    main()
