# main.py
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_community.llms import HuggingFacePipeline
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import git
from pathlib import Path
import os

REPO_URL = "https://github.com/in28minutes/spring-boot-examples.git"
LOCAL_REPO = "./spring-boot-examples"


def clone_repo():
    if not os.path.exists(LOCAL_REPO):
        print("Cloning repo...")
        git.Repo.clone_from(REPO_URL, LOCAL_REPO)
    else:
        print("Repo already cloned.")


def load_documents():
    print("Loading Java files...")
    paths = Path(LOCAL_REPO).rglob("*.java")
    docs = []
    for path in paths:
        try:
            if path.stat().st_size == 0:
                continue
            loader = TextLoader(str(path))
            docs.extend(loader.load())
        except Exception as e:
            print(f"Failed to load {path}: {e}")
    print(f"Loaded {len(docs)} documents.")
    return docs


def build_vector_store(docs):
    print("Splitting documents...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = splitter.split_documents(docs)
    print(f"Total chunks: {len(splits)}")

    embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.from_documents(splits, embedder)
    db.save_local("vector_store")
    return db


def load_llm():
    print("Loading LLM pipeline...")
    #model_id = "mistralai/Mistral-7B-Instruct-v0.2"
    model_id = "Salesforce/codegen-350M-mono"  # Open access
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto")
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=512)
    return HuggingFacePipeline(pipeline=pipe)


def qa_loop(qa):
    while True:
        query = input("\nAsk something about the code (or type 'exit'): ")
        if query.lower() in ["exit", "quit"]:
            break
        try:
            answer = qa.run(query)
            print("\nAnswer:\n", answer)
        except Exception as e:
            print(f"Error during QA: {e}")


def main():
    #clone_repo()
    if not os.path.exists("vector_store"):
        docs = load_documents()
        if not docs:
            print("No documents found to index. Exiting.")
            return
        db = build_vector_store(docs)
    else:
        embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        db = FAISS.load_local("vector_store", embedder, allow_dangerous_deserialization=True)

    retriever = db.as_retriever(search_kwargs={"k": 5})
    llm = load_llm()
    qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
    qa_loop(qa)


if __name__ == "__main__":
    main()
