
import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routers import categories_controller, strategies_controller, backtest_controller, tickers_controller
from fastapi.staticfiles import StaticFiles


app = FastAPI()

app.include_router(strategies_controller.router)
app.include_router(categories_controller.router)
app.include_router(backtest_controller.router)
app.include_router(tickers_controller.router)

templates = Jinja2Templates(directory="./app/templates")

app.mount("/static", StaticFiles(directory="./app/templates/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})