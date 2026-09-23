from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr
import vertexai
import time
import os

PROJECT_ID = (
    os.environ.get("GOOGLE_CLOUD_PROJECT")
    or os.environ.get("PROJECT_ID")
    or "qwiklabs-gcp-04-0b819a9381db"
)
LOCATION = os.environ.get("LOCATION", "us-central1")
BUCKET_NAME = os.environ.get("IMAGE_BUCKET_NAME", f"smart-chef-pantry-{PROJECT_ID}")
GCS_PATH = f"gs://{BUCKET_NAME}/rag/pg49513.txt"

print("Initializing vertexai...")
vertexai.init(project=PROJECT_ID, location=LOCATION)

# 1. Switch the region's RAG managed DB to serverless mode
cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
print(f"Setting RAG engine config for {cfg} to Serverless...")
try:
    rag.update_rag_engine_config(rag_engine_config=rag.RagEngineConfig(
        name=cfg,
        rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
    ))
    print("Serverless mode enabled.")
except Exception as e:
    print("Warning updating rag engine config:", e)

# 2. Create the corpus
print("Creating RAG corpus...")
corpus = rag.create_corpus(
    display_name="culinary-herbal-corpus",
    embedding_model_config=rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-005"
    ),
)
print("CORPUS_NAME:", corpus.name)

# 3. Import + chunk + embed
print(f"Importing {GCS_PATH} into corpus...")
resp = rag.import_files(
    corpus_name=corpus.name,
    paths=[GCS_PATH],
    transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
    ),
)
print(f"Import completed! Files imported: {resp.imported_rag_files_count}")

# 4. Standalone retrieval test
print("Testing retrieval query for 'rosemary'...")
time.sleep(5)
try:
    test_res = rag.retrieval_query(
        text="What are the culinary and medicinal uses of rosemary or thyme?",
        rag_resources=[rag.RagResource(rag_corpus=corpus.name)],
        rag_retrieval_config=rag.RagRetrievalConfig(top_k=3),
    )
    print("Retrieval results count:", len(test_res.contexts.contexts))
    for c in test_res.contexts.contexts[:2]:
        print("Score:", c.score, "Snippet:", c.text[:150])
except Exception as e:
    print("Initial retrieval query note (indexing may be in progress):", e)

# Save corpus name to a file so tools and scripts can reference it
with open("/config/Desktop/BuildWithGemini/smart-chef-pantry-concierge/rag_corpus_id.txt", "w") as f:
    f.write(corpus.name)
print("Saved corpus ID to rag_corpus_id.txt")
