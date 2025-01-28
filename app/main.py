
import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routers import categories_controller, strategies_controller, backtest_controller, portfolio_controller
from fastapi.staticfiles import StaticFiles


app = FastAPI()

app.include_router(strategies_controller.router)
app.include_router(categories_controller.router)
app.include_router(backtest_controller.router)
app.include_router(portfolio_controller.router)

templates = Jinja2Templates(directory="./app/templates")

app.mount("/static", StaticFiles(directory="./app/templates/static"), name="static")
# app.mount("/backtest_plots", StaticFiles(directory="./app/templates/static/backtest_plots"), name="backtest_plots")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})