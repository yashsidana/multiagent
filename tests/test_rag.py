from src.rag.ingest import RecursiveTextSplitter


def test_recursive_splitter_chunking():
    splitter = RecursiveTextSplitter(chunk_size=100, chunk_overlap=20)
    sample_text = (
        "## Section 1\n"
        "This is a paragraph about business operations. We strive for excellence and efficiency.\n\n"
        "## Section 2\n"
        "This is another paragraph outlining quarterly goals and key revenue milestones for the company."
    )
    chunks = splitter.split_text(sample_text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) > 0

