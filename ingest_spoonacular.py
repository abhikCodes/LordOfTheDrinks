import os, requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import Recipe
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

load_dotenv()
oai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'), environment=os.getenv('PINECONE_ENVIRONMENT'))

# Create Pinecone index if missing
if 'food-embeddings' not in [idx.name for idx in pc.list_indexes().indexes]:
    pc.create_index(
        name='food-embeddings', dimension=1536, metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
food_ix = pc.Index('food-embeddings')

# Create tables
Base.metadata.create_all(bind=engine)
session: Session = SessionLocal()

# ← clear out the old data
session.query(Recipe).delete()
session.commit()

API_KEY = os.getenv('SPOONACULAR_API_KEY')

for offset in range(0, 1000, 10):
    data = requests.get(
        'https://api.spoonacular.com/recipes/complexSearch',
        params={'apiKey':API_KEY,'number':10,'offset':offset,'addRecipeInformation':True}
    ).json().get('results', [])
    for r in data:
        rec = Recipe(
            id=r['id'], title=r['title'], cuisine=(r.get('cuisines') or [''])[0],
            instructions=r.get('instructions',''),
            ingredients=[i['name'] for i in r.get('extendedIngredients',[])],
            embedding_id=f"food-{r['id']}"
        )
        session.merge(rec)
        # Generate embedding\ n        
        resp = oai.embeddings.create(
            input=r['title'] + ' ' + rec.instructions,
            model='text-embedding-ada-002'
        )
        emb = resp.data[0].embedding
        # Upsert vector
        food_ix.upsert(vectors=[{'id': rec.embedding_id, 'values': emb}])
    session.commit()
print('Spoonacular ingestion done')