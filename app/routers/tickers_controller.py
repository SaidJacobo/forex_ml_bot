from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.view_models.category_vm import CategoryVM
from app.view_models.ticker_vm import TickerVM
from backbone.services.ticker_service import TickerService


router = APIRouter()

templates = Jinja2Templates(directory="./app/templates")

ticker_service = TickerService()

@router.get("/tickers/{strategy_id}")
async def get_tickers_by_strategy(strategy_id: UUID):

    result = ticker_service.get_tickers_by_strategy(strategy_id)
    if result.ok:
        tickers_vm = [TickerVM.model_validate(ticker) for ticker in result.item]
        
        return {"tickers": tickers_vm}