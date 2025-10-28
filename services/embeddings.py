# services/embeddings.py
import pandas as pd
import pickle
from sentence_transformers import SentenceTransformer

class SemanticSimilarityEngine:
    """Generate and save embeddings for project ideas"""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        print(f"🤖 Loading AI model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("✅ Model loaded successfully!")

    def generate_embeddings_batch(self, texts):
        """Generate embeddings for a batch of text inputs"""
        print(f"\n🔄 Generating embeddings for {len(texts)} ideas...")

        # Clean and convert to string
        texts = [str(t) if t and not pd.isna(t) else "" for t in texts]

        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        print(f"✅ Generated {len(embeddings)} embeddings (shape: {embeddings.shape})")
        return embeddings

    def save_embeddings(self, embeddings, df, filename: str):
        """Save embeddings and metadata"""
        data = {
            'embeddings': embeddings,
            'ideas': df,
            'model_name': 'all-MiniLM-L6-v2'
        }
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
        print(f"💾 Saved embeddings to: {filename}")


if __name__ == "__main__":
    # Step 1: Load the CSV
    df = pd.read_csv('data/student_ideas_transformed.csv')
    print(f"📂 Loaded {len(df)} project ideas")

    # Step 2: Combine key text fields
    text_fields = [
        'title', 'tagline', 'description',
        'problem_statement', 'domain', 'category'
    ]

    df['combined_text'] = df[text_fields].fillna('').agg(' '.join, axis=1)

    # Step 3: Generate embeddings
    engine = SemanticSimilarityEngine()
    embeddings = engine.generate_embeddings_batch(df['combined_text'].tolist())

    # Step 4: Save embeddings
    engine.save_embeddings(embeddings, df, 'data/idea_embeddings.pkl')

    print("\n✅ All done! Embeddings saved to 'data/idea_embeddings.pkl'")
