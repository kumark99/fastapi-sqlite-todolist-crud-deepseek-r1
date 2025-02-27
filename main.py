# main.py
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./todos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database model
class DBTodo(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    category = Column(String(50))
    description = Column(Text)
    due_date = Column(DateTime)
    completed = Column(Boolean, default=False)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic model
class TodoCreate(BaseModel):
    title: str
    category: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: bool = False

class Todo(TodoCreate):
    id: int

    class Config:
        orm_mode = True

# FastAPI app setup
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Endpoints
@app.post("/api/todos/", response_model=Todo)
def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
    db_todo = DBTodo(**todo.dict())
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

@app.get("/api/todos/", response_model=list[Todo])
def read_todos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(DBTodo).offset(skip).limit(limit).all()

@app.get("/api/todos/{todo_id}", response_model=Todo)
def read_todo(todo_id: int, db: Session = Depends(get_db)):
    todo = db.query(DBTodo).filter(DBTodo.id == todo_id).first()
    return todo

@app.put("/api/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: int, todo: TodoCreate, db: Session = Depends(get_db)):
    db_todo = db.query(DBTodo).filter(DBTodo.id == todo_id).first()
    for key, value in todo.dict().items():
        setattr(db_todo, key, value)
    db.commit()
    db.refresh(db_todo)
    return db_todo

@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    db.query(DBTodo).filter(DBTodo.id == todo_id).delete()
    db.commit()
    return {"message": "Todo deleted"}

# Web Interface
@app.get("/", response_class=HTMLResponse)
async def read_todos_web(request: Request, db: Session = Depends(get_db)):
    todos = db.query(DBTodo).all()
    return templates.TemplateResponse("index.html", {"request": request, "todos": todos})

@app.post("/add", response_class=RedirectResponse)
async def add_todo(
    title: str = Form(...),
    category: str = Form(None),
    description: str = Form(None),
    due_date: datetime = Form(None),
    db: Session = Depends(get_db)
):
    todo = DBTodo(
        title=title,
        category=category,
        description=description,
        due_date=due_date
    )
    db.add(todo)
    db.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/edit/{todo_id}", response_class=RedirectResponse)
async def edit_todo(
    todo_id: int,
    title: str = Form(...),
    category: str = Form(None),
    description: str = Form(None),
    due_date: datetime = Form(None),
    completed: bool = Form(False),
    db: Session = Depends(get_db)
):
    todo = db.query(DBTodo).filter(DBTodo.id == todo_id).first()
    todo.title = title
    todo.category = category
    todo.description = description
    todo.due_date = due_date
    todo.completed = completed
    db.commit()
    return RedirectResponse("/", status_code=303)

@app.get("/delete/{todo_id}", response_class=RedirectResponse)
async def delete_todo_web(todo_id: int, db: Session = Depends(get_db)):
    db.query(DBTodo).filter(DBTodo.id == todo_id).delete()
    db.commit()
    return RedirectResponse("/", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)