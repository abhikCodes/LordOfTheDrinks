import argparse
import os, requests, string
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import Drink
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
if 'drink-embeddings' not in [idx.name for idx in pc.list_indexes().indexes]:
    pc.create_index(
        name='drink-embeddings', dimension=1536, metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
drink_ix = pc.Index('drink-embeddings')

# ── Database setup ────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
session: Session = SessionLocal()

# ── First-run detection ───────────────────────────────────────────────────────
existing = session.query(Drink).first()
if existing and not args.force:
    print("🍸 Drinks table already populated; skipping ingestion.")
    session.close()
    exit(0)

# ── Clear old data & embeddings ──────────────────────────────────────────────
session.query(Drink).delete()
session.commit()
drink_ix.delete(delete_all=True)

# ── Fetch & ingest ───────────────────────────────────────────────────────────
lowercase_letters = list(string.ascii_lowercase)
print("Starting Drinks Ingestion...")
for c in tqdm(lowercase_letters):
    try:
        resp = requests.get(f'https://www.thecocktaildb.com/api/json/v1/1/search.php?f={c}')
        drinks = resp.json().get('drinks') or []
        for d in drinks:
            dr = Drink(
                id=int(d['idDrink']),
                name=d['strDrink'],
                drink_type=d['strCategory'],
                instructions=d['strInstructions'] or "",
                ingredients=[d[f'strIngredient{i}'] for i in range(1,16) if d.get(f'strIngredient{i}')],
                embedding_id=f"drink-{d['idDrink']}"
            )
            session.add(dr)
            emb = oai.embeddings.create(
                input=dr.name + ' ' + dr.instructions,
                model='text-embedding-ada-002'
            ).data[0].embedding
            drink_ix.upsert(vectors=[{'id': dr.embedding_id, 'values': emb}])
    except Exception as e:
        print(f"Error on letter {c}: {e}")
        continue

session.commit()
session.close()
print('✅ CocktailDB ingestion done')
