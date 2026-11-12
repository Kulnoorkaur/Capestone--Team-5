from docx import Document


# ==========================================
# FUNCTION 1: LOAD WORD DOCUMENT
# ==========================================

def load_word_document(file_path):
    """
    Extract text from a Word document,
    including paragraphs and tables.
    """

    # Open the Word document
    document = Document(file_path)

    # Extract text from paragraphs
    paragraphs = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    # Extract text from tables
    table_text = []

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    table_text.append(cell.text)

    # Combine all extracted text
    full_text = "\n".join(paragraphs + table_text)

    return full_text


# ==========================================
# FUNCTION 2: CHUNK DOCUMENT
# ==========================================

def chunk_document(text, chunk_size=1000, overlap=200):
    """
    Split document text into overlapping chunks
    while attempting to preserve paragraph boundaries.
    """

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0.")

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Prefer ending at a paragraph boundary
        if end < len(text):
            paragraph_break = text.rfind("\n", start + 1, end)

            if paragraph_break > start:
                end = paragraph_break + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        # Preserve overlap without splitting at arbitrary positions
        next_start = max(0, end - overlap)

        paragraph_start = text.find("\n", next_start, end)

        if paragraph_start != -1:
            next_start = paragraph_start + 1

        # Ensure forward progress
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks

# ==========================================
# FUNCTION 3: RETRIEVE RELEVANT CHUNKS
# ==========================================

def retrieve_relevant_chunks(question, chunks, top_k=3):
    """
    Retrieve document chunks based on keyword overlap.
    """

    # Convert the question into searchable words
    question_words = set(question.lower().split())

    # Store relevance scores
    scored_chunks = []

    for chunk in chunks:

        # Convert chunk into searchable words
        chunk_words = set(chunk.lower().split())

        # Count matching words
        score = len(question_words.intersection(chunk_words))

        # Keep chunks with at least one match
        if score > 0:
            scored_chunks.append((score, chunk))

    # Sort chunks by relevance score
    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    # Return the most relevant chunks
    return [chunk for score, chunk in scored_chunks[:top_k]]

# ==========================================
# FUNCTION 4: ATTACH SOURCE METADATA
# ==========================================

def add_source_metadata(chunks, source_name, jurisdiction):
    """
    Attach document source information to each chunk.

    Parameters:
        chunks (list): List of document text chunks.
        source_name (str): Name of the source document.
        jurisdiction (str): Regulatory jurisdiction.

    Returns:
        list: Chunks containing text and source metadata.
    """

    documented_chunks = []

    for index, chunk in enumerate(chunks):

        documented_chunk = {
            "chunk_id": index + 1,
            "text": chunk,
            "source": source_name,
            "jurisdiction": jurisdiction
        }

        documented_chunks.append(documented_chunk)

    return documented_chunks