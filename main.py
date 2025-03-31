from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from datetime import datetime, timedelta
import jwt 
import os  
import uuid 

app = FastAPI()

links = {}

EXPIRATION_DAYS = 30
EXPIRATION_DAYS = os.getenv("EXPIRATION_DAYS", "Days_before_link_deleting")

class LinkCreate(BaseModel):
    original_url: str
    custom_alias: str = None
    expires_at: datetime = None

class LinkUpdate(BaseModel):
    new_url: str
    custom_alias: str = None

class User(BaseModel):
    id: uuid.UUID
    username: str
    password: str

def generate_short_code(original_url):
    """Генерация короткого кода с использованием JWT."""
    secret_key = os.getenv("SECRET_KEY", "your_secret_key")
    payload = {"url": original_url}  
    token = jwt.encode(payload, secret_key, algorithm="HS256") 
    return token 

@app.post("/links/shorten")
def shorten_link(link: LinkCreate):
    """Создает короткую ссылку для заданного оригинального URL."""
    if link.custom_alias and link.custom_alias in links:
        raise HTTPException(status_code=400, detail="Custom alias already exists.")
    
    short_code = link.custom_alias if link.custom_alias else generate_short_code(link.original_url)
    
    if short_code in links:
        raise HTTPException(status_code=400, detail="Short code already exists.")
    
    expires_at = datetime.now() + timedelta(days=EXPIRATION_DAYS)
    
    links[short_code] = {
        "original_url": link.original_url,
        "expires_at": expires_at,
        "created_at": datetime.now(),
        "last_used": None,
        "click_count": 0
    }
    
    return {"short_code": short_code, "original_url": link.original_url}

@app.get("/links/{short_code}")
def redirect_link(short_code: str):
    """Перенаправляет на оригинальный URL по заданному короткому коду."""
    link_data = links.get(short_code)
    
    if not link_data:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if link_data["expires_at"] and datetime.now() > link_data["expires_at"]:
        del links[short_code] 
        raise HTTPException(status_code=404, detail="Link has expired")
    
    if link_data["last_used"] and (datetime.now() - link_data["last_used"]).days > EXPIRATION_DAYS:
        del links[short_code] 
        raise HTTPException(status_code=404, detail="Link has been deleted due to inactivity")
    
    links[short_code]["last_used"] = datetime.now()
    links[short_code]["click_count"] += 1  
    
    return {"original_url": link_data["original_url"]}

@app.delete("/links/{short_code}")
def delete_link(short_code: str):
    """Удаляет ссылку по заданному короткому коду."""
    if short_code not in links:
        raise HTTPException(status_code=404, detail="Link not found")
    
    del links[short_code]
    return {"detail": "Link deleted successfully"}


@app.put("/links/{short_code}")
def update_link(short_code: str, link: LinkUpdate):
    """Обновляет оригинальный URL и кастомный alias для заданного короткого кода."""
    if short_code not in links:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if link.custom_alias and link.custom_alias in links:
        raise HTTPException(status_code=400, detail="Custom alias already exists.")
    
    links[short_code]["original_url"] = link.new_url
    if link.custom_alias:
        links[link.custom_alias] = links.pop(short_code)
    
    return {"detail": "Link updated successfully", "new_url": link.new_url}

@app.get("/links/{short_code}/stats")
def get_link_stats(short_code: str):
    """Возвращает статистику по ссылке."""
    link_data = links.get(short_code)
    
    if not link_data:
        raise HTTPException(status_code=404, detail="Link not found")
    
    stats = {
        "original_url": link_data["original_url"],
        "click_count": link_data["click_count"],
        "last_used": link_data["last_used"],
        "expires_at": link_data["expires_at"]
    }
    
    return stats


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", log_level="info")
