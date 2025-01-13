from fastapi import APIRouter
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from pydantic import BaseModel, ConfigDict
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
        vm.Categories = [CategoryVM.model_validate(category) for category in result_categories.item]
        vm.Strategies = [StrategyVM.model_validate(strategy) for strategy in result_strategies.item]
        vm.Timeframes = [TimeframeVM.model_validate(timeframe) for timeframe in result_timeframes.item]
        
        return templates.TemplateResponse("/backtest/create.html", {"request": request, "model": vm})





# Ruta POST: Procesa datos del formulario
@router.post("/backtest/create")
async def create_post(
    strategy: str = Form(...),
    category: str = Form(...),
    ticker: str = Form(...),
    timeframe: str = Form(...),
    datefrom: str = Form(...),
    dateto: str = Form(...),
    risk: str = Form(...),
):
    
    print('strategy: ', strategy)
    print('category: ', category)
    print('ticker: ', ticker)
    print('timeframe: ', timeframe)
    print('datefrom: ', datefrom)
    print('dateto: ', dateto)
    print('risk: ', risk)
    
            
    try:

        result = backtest_service.run(
            strategy,
            category,
            ticker,
            datefrom,
            dateto,
            risk,
        )
        
        if result.ok:
            strategy_vm = StrategyVM.model_validate(result.item)
            return RedirectResponse(url="/strategies/", status_code=303)

        else:
            return {
                "message": "Error",
                "data": result.message
            }
            

    except ValidationError as e:
        return {"error": e.errors()}
    
    
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