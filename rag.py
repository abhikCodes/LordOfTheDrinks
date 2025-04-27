import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
from pinecone import Pinecone

oai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'), environment=os.getenv('PINECONE_ENVIRONMENT'))
food_ix = pc.Index('food-embeddings')
drink_ix = pc.Index('drink-embeddings')

async def retrieve_recipe_id(query: str) -> str:
    emb = oai.embeddings.create(input=query, model='text-embedding-ada-002').data[0].embedding
    res = food_ix.query(vector=emb, top_k=1)
    return res.matches[0].id

async def retrieve_drink_ids(emb: list, k: int = 3) -> list:
    res = drink_ix.query(vector=emb, top_k=k)
    return [m.id for m in res.matches]