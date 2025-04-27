import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from schemas import PairRequest, PairResponse, RecipeOut, DrinkOut
from rag import retrieve_recipe_id, retrieve_drink_ids
from database import SessionLocal, engine, Base
from models import Recipe, Drink
from openai import OpenAI


# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],            # or lock down to your host
  allow_methods=["*"],
  allow_headers=["*"],
)

oai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
CHAT_MODEL = os.getenv('CHAT_MODEL', 'gpt-4o-mini')

# DB session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/pair", response_model=PairResponse)
async def pair(req: PairRequest, db: Session = Depends(get_db)):
    food_id = await retrieve_recipe_id(req.food_query)
    food_pk = int(food_id.replace('food-', ''))
    food = db.get(Recipe, food_pk)
    if not food:
        raise HTTPException(404, "Food not found")

    # Enhanced embedding query for better pairing
    query_text = f"{food.cuisine} {food.title} {' '.join(food.ingredients)}"
    emb = oai.embeddings.create(input=query_text, model='text-embedding-ada-002').data[0].embedding
    drink_ids = await retrieve_drink_ids(emb)
    
    if not drink_ids:
        raise HTTPException(404, "No drinks found for pairing")

    drinks = [db.get(Drink, int(d.replace('drink-', ''))) for d in drink_ids]

    # Chat ranking & rationale with personality
    drink_list_text = "\n".join(f"- {d.name} ({d.drink_type})" for d in drinks)
    user_prompt = (
        f"I'm enjoying a {food.cuisine} dish called '{food.title}'—sounds fancy, right? 🍽️\n"
        f"Here are three drinks that might go with it (or not, who knows?):\n{drink_list_text}\n"
        "Rank them from best to worst pairing, and give me a quick, witty reason for each. Maybe even suggest a tweak if you're feeling spicy! 🌶️"
    )
    chat_resp = oai.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You're a witty, world-class sommelier and chef with a knack for fun pairings."},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7
    )
    explanation = chat_resp.choices[0].message.content

    # Manual schema mapping
    food_out = RecipeOut(id=food.id, title=food.title, cuisine=food.cuisine,
                         instructions=food.instructions, ingredients=food.ingredients)
    drinks_out = [DrinkOut(id=d.id, name=d.name, drink_type=d.drink_type,
                           instructions=d.instructions, ingredients=d.ingredients)
                  for d in drinks]
    return PairResponse(food=food_out, drinks=drinks_out, explanation=explanation)


# serve front-end
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return FileResponse('frontend/index.html')

app.mount("/static", StaticFiles(directory="frontend"), name="static")