
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from routers import strategies_controller


app = FastAPI()

app.include_router(strategies_controller.router)

templates = Jinja2Templates(directory="./templates")


@app.get("/home", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})