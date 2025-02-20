
import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routers import categories_controller, portfolios_controller, strategies_controller, backtest_controller
from fastapi.staticfiles import StaticFiles
import uvicorn


app = FastAPI()

app.include_router(strategies_controller.router)
app.include_router(categories_controller.router)
app.include_router(backtest_controller.router)
app.include_router(portfolios_controller.router)

templates = Jinja2Templates(directory="./app/templates")

app.mount("/static", StaticFiles(directory="./app/templates/static"), name="static")


backtests_plot_path = './app/templates/static/backtest_plots'
if not os.path.exists(backtests_plot_path):
    os.mkdir(backtests_plot_path)
    
app.mount("/backtest_plots", StaticFiles(directory=backtests_plot_path), name="backtest_plots")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)