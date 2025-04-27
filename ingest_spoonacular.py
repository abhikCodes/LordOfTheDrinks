import argparse
import os, requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import Recipe
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm

# ── CLI setup ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--force', action='store_true', help='Wipe and re-ingest even if data exists')
args = parser.parse_args()

load_dotenv()
oai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'), environment=os.getenv('PINECONE_ENVIRONMENT'))

# ── Pinecone index setup ─────────────────────────────────────────────────────
if 'food-embeddings' not in [idx.name for idx in pc.list_indexes().indexes]:
    pc.create_index(
        name='food-embeddings', dimension=1536, metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
food_ix = pc.Index('food-embeddings')

# ── Database setup ────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
session: Session = SessionLocal()

# ── First-run detection ───────────────────────────────────────────────────────
existing = session.query(Recipe).first()
if existing and not args.force:
    print("🍲 Recipes table already populated; skipping ingestion.")
    session.close()
    exit(0)

# ── Clear old data & embeddings ──────────────────────────────────────────────
session.query(Recipe).delete()
session.commit()
food_ix.delete(delete_all=True)

# ── Fetch & ingest ───────────────────────────────────────────────────────────
API_KEY = os.getenv('SPOONACULAR_API_KEY')
print("Starting Recipes Ingestion...")
for offset in tqdm(range(0, 1000, 10)):
    data = requests.get(
        'https://api.spoonacular.com/recipes/complexSearch',
        params={'apiKey': API_KEY, 'number': 10, 'offset': offset, 'addRecipeInformation': True}
    ).json().get('results', [])
    for r in data:
        rec = Recipe(
            id=r['id'],
            title=r['title'],
            cuisine=(r.get('cuisines') or [''])[0],
            instructions=r.get('instructions', ''),
            ingredients=[i['name'] for i in r.get('extendedIngredients', [])],
            embedding_id=f"food-{r['id']}"
        )
        session.add(rec)
        emb = oai.embeddings.create(
            input=rec.title + ' ' + rec.instructions,
            model='text-embedding-ada-002'
        ).data[0].embedding
        food_ix.upsert(vectors=[{'id': rec.embedding_id, 'values': emb}])
    session.commit()

session.close()
print('✅ Spoonacular ingestion done')
