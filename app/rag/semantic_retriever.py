from sentence_transformers import SentenceTransformer, util


# ==========================================
# LOAD EMBEDDING MODEL
# ==========================================

model = SentenceTransformer("all-MiniLM-L6-v2")


# ==========================================
# RETRIEVE SEMANTICALLY RELEVANT CHUNKS
# WITH SOURCE METADATA
# ==========================================

def retrieve_semantic_chunks(question, chunks, top_k=3, jurisdiction=None):
    """
    Retrieve relevant regulatory document chunks
    using semantic similarity.

    Supports:
    - Semantic similarity search
    - Source metadata preservation
    - Jurisdiction filtering
    """

    if not chunks or top_k <= 0:
        return []

    # Filter chunks by jurisdiction if specified
    if jurisdiction:
        chunks = [
            chunk for chunk in chunks
            if chunk["jurisdiction"].lower() == jurisdiction.lower()
        ]

    if not chunks:
        return []

    # Extract text for embedding
    chunk_texts = [
        chunk["text"]
        for chunk in chunks
    ]

    # Generate question embedding
    question_embedding = model.encode(
        question,
        convert_to_tensor=True
    )

    # Generate document embeddings
    chunk_embeddings = model.encode(
        chunk_texts,
        convert_to_tensor=True
    )

    # Calculate cosine similarity
    similarity_scores = util.cos_sim(
        question_embedding,
        chunk_embeddings
    )[0]

    # Determine number of results
    top_k = min(top_k, len(chunks))

    # Retrieve highest-scoring chunks
    top_results = similarity_scores.topk(k=top_k)

    # Preserve metadata in retrieved results
    relevant_chunks = []

    for score, index in zip(
        top_results.values,
        top_results.indices
    ):

        chunk = chunks[index.item()].copy()

        chunk["similarity_score"] = round(
            score.item(), 4
        )

        relevant_chunks.append(chunk)

    return relevant_chunks