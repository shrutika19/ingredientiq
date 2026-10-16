from app.knowledge.embedding.client import GeminiEmbeddingClient


def main():
    client = GeminiEmbeddingClient()

    vector = client.embed_document(
        content=(
            "Synthetic test text for validating "
            "the IngredientIQ embedding integration."
        ),
        title="IngredientIQ Embedding Test",
    )

    print(f"Embedding dimensions: {len(vector)}")
    print(f"First five values: {vector[:5]}")


if __name__ == "__main__":
    main()