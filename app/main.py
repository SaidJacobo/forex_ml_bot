
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from routers import strategies_controller, tickers_controller


app = FastAPI()

app.include_router(strategies_controller.router)
app.include_router(tickers_controller.router)

templates = Jinja2Templates(directory="./templates")


@app.get("/home", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})