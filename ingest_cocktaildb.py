import os, requests, string
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import Drink
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

load_dotenv()
oai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'), environment=os.getenv('PINECONE_ENVIRONMENT'))

if 'drink-embeddings' not in [idx.name for idx in pc.list_indexes().indexes]:
    pc.create_index(
        name='drink-embeddings', dimension=1536, metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
drink_ix = pc.Index('drink-embeddings')

Base.metadata.create_all(bind=engine)
session: Session = SessionLocal()

# ← clear out the old data
session.query(Drink).delete()
session.commit()

lowercase_letters = list(string.ascii_lowercase)

for c in lowercase_letters:
    resp = requests.get(f'https://www.thecocktaildb.com/api/json/v1/1/search.php?f={c}').json().get('drinks', [])
    if resp:
        for d in resp:
            dr = Drink(
                id=int(d['idDrink']), name=d['strDrink'], drink_type=d['strCategory'],
                instructions=d['strInstructions'],
                ingredients=[d[f'strIngredient{i}'] for i in range(1,16) if d.get(f'strIngredient{i}')],
                embedding_id=f"drink-{d['idDrink']}"
            )
            session.merge(dr)
            resp_e = oai.embeddings.create(
                input=dr.name + ' ' + dr.instructions,
                model='text-embedding-ada-002'
            )
            emb = resp_e.data[0].embedding
            drink_ix.upsert(vectors=[{'id': dr.embedding_id, 'values': emb}])
session.commit()
print('CocktailDB ingestion done')