from typing import Optional
from fastapi import APIRouter
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pandas import Timestamp
from pydantic import ValidationError
from pydantic import BaseModel, ConfigDict
import pytz
from app.backbone.services.strategy_service import StrategyService
from app.view_models.backtest_vm import BacktestCreateVM
from app.view_models.category_vm import CategoryVM
from app.view_models.strategy_vm import StrategyVM
from app.view_models.timeframe_vm import TimeframeVM
from backbone.services.ticker_service import TickerService
from backbone.services.backtest_service import BacktestService

from uuid import UUID



router = APIRouter()

templates = Jinja2Templates(directory="./app/templates")

ticker_service = TickerService()
strategy_service = StrategyService()
backtest_service = BacktestService()

# Ruta GET: muestra el formulario
@router.get("/backtest/", response_class=HTMLResponse)
async def form_page(request: Request):
        
    return templates.TemplateResponse("/backtest/index.html", {"request": request})


# Ruta GET: muestra el formulario
@router.get("/backtest/create", response_class=HTMLResponse)
async def create_get(request: Request):
    result_timeframes = ticker_service.get_all_timeframes()
    result_strategies = strategy_service.get_all()
    result_categories = ticker_service.get_all_categories()
    
    
    if result_categories.ok and result_strategies.ok and result_timeframes.ok:
        vm = BacktestCreateVM()
        vm.Strategies = [StrategyVM.model_validate(strategy) for strategy in result_strategies.item]
        vm.Timeframes = [TimeframeVM.model_validate(timeframe) for timeframe in result_timeframes.item]
        vm.Categories = [CategoryVM.model_validate(category) for category in result_categories.item]
        
        return templates.TemplateResponse("/backtest/create.html", {"request": request, "model": vm})
    
    else:
        print([result_categories.message, result_strategies.message, result_timeframes.message])
        return {
            'error': [result_categories.message, result_strategies.message, result_timeframes.message]
        }
        





# Ruta POST: Procesa datos del formulario
@router.post("/backtest/create")
async def create_post(
    strategy_id: UUID = Form(...),
    category_id: Optional[str] = Form(None),
    ticker_id: Optional[str] = Form(None),
    timeframe_id: Optional[str] = Form(None),
    date_from: str = Form(...),
    date_to: str = Form(...),
    risk: float = Form(...),
):
       
    category_id = UUID(category_id) if category_id else None
    ticker_id = UUID(ticker_id) if ticker_id else None
    timeframe_id = UUID(timeframe_id) if timeframe_id else None
    
    date_from = Timestamp(date_from, tz="UTC")
    date_to = Timestamp(date_to, tz="UTC")
    
    
    # try:

    strategy = strategy_service.get_by_id(id=strategy_id).item
    
    if category_id is None:
        tickers = ticker_service.get_all_tickers().item
    
    elif category_id is not None and ticker_id is None:
        tickers = ticker_service.get_tickers_by_category(category_id=category_id).item
    
    elif category_id is not None and ticker_id is not None:
        tickers = [ticker_service.get_ticker_by_id(id=ticker_id).item]
        
    
    if timeframe_id is None:
        timeframes = ticker_service.get_all_timeframes().item
    else:
        timeframes = [ticker_service.get_timeframe_by_id(timeframe_id).item]
    
    result = backtest_service.run(
        10_000, # viene del front
        strategy,
        tickers,
        timeframes,
        date_from,
        date_to,
        risk,
    )
    
    #     if result.ok:
    #         strategy_vm = StrategyVM.model_validate(result.item)
    #         return RedirectResponse(url="/strategies/", status_code=303)

    #     else:
    #         return {
    #             "message": "Error",
    #             "data": result.message
    #         }
            

    # except ValidationError as e:
    #     return {"error": e.errors()}
    
    
# @router.post("/strategies/delete/{strategy_id}")
# async def delete(strategy_id: UUID):
#     result = strategy_service.delete(id=strategy_id)
    
#     if result.ok:
#         return RedirectResponse(url="/strategies/", status_code=303)

#     else:
#         return {
#             "message": "Error",
#             "data": result.message
#         }