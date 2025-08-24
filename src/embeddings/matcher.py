# src/pasa/embeddings/matcher.py
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')  # lightweight and effective

def compute_similarity(text1, text2):
    embeddings = model.encode([text1, text2], convert_to_tensor=True)
    return util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
