from sqlalchemy import Column, Integer, String, JSON
from database import Base

class Recipe(Base):
    __tablename__ = 'recipes'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    cuisine = Column(String)
    instructions = Column(String)
    ingredients = Column(JSON)
    embedding_id = Column(String, unique=True)

class Drink(Base):
    __tablename__ = 'drinks'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    drink_type = Column(String)
    instructions = Column(String)
    ingredients = Column(JSON)
    embedding_id = Column(String, unique=True)