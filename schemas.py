from pydantic import BaseModel
from typing import List

class PairRequest(BaseModel):
    food_query: str

class RecipeOut(BaseModel):
    id: int
    title: str
    cuisine: str
    instructions: str
    ingredients: List[str]

class DrinkOut(BaseModel):
    id: int
    name: str
    drink_type: str
    instructions: str
    ingredients: List[str]

class PairResponse(BaseModel):
    food: RecipeOut
    drinks: List[DrinkOut]
    explanation: str