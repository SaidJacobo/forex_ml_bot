from collections import defaultdict
from datetime import date
from typing import Optional
from fastapi import APIRouter, Query
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pandas import Timestamp
from app.backbone.services.bot_service import BotService
from app.backbone.services.strategy_service import StrategyService
from app.view_models.backtest_create_vm import BacktestCreateVM
from app.view_models.bot_performance_vm import BotPerformanceVM
from app.view_models.category_vm import CategoryVM
from app.view_models.strategy_vm import StrategyVM
from app.view_models.timeframe_vm import TimeframeVM
from backbone.services.ticker_service import TickerService
from backbone.services.backtest_service import BacktestService
import plotly.graph_objects as go

from uuid import UUID

router = APIRouter()

templates = Jinja2Templates(directory="./app/templates")

ticker_service = TickerService()
strategy_service = StrategyService()
backtest_service = BacktestService()
bot_service = BotService()

@router.get("/backtest", response_class=HTMLResponse)
async def backtest_strategies(request: Request):
    result = strategy_service.get_used_strategies()
    
    if result.ok:
        strategies_vm = [StrategyVM.model_validate(strategy) for strategy in result.item]
        return templates.TemplateResponse("/backtest/index.html", {"request": request, 'strategies': strategies_vm})

    else:
        return {
            "message": "Error",
            "data": result.message
        }
        
@router.get("/backtest/new", response_class=HTMLResponse)
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
        
@router.post("/backtest")
async def create_post(
    strategy_id: UUID = Form(...),
    category_id: Optional[str] = Form(None),
    ticker_id: Optional[str] = Form(None),
    timeframe_id: Optional[str] = Form(None),
    date_from: str = Form(...),
    date_to: str = Form(...),
    risk: float = Form(...),
    initial_cash: float = Form(...),
    metatrader_name: str = Form(...),
):
       
    category_id = UUID(category_id) if category_id else None
    ticker_id = UUID(ticker_id) if ticker_id else None
    timeframe_id = UUID(timeframe_id) if timeframe_id else None
    
    date_from = Timestamp(date_from, tz="UTC")
    date_to = Timestamp(date_to, tz="UTC")
    
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
    
    backtest_service.run_backtest(
        initial_cash,
        strategy,
        tickers,
        timeframes,
        date_from,
        date_to,
        'pa', # viene del front
        metatrader_name,
        risk,
    )
    
    return RedirectResponse(url="/backtest", status_code=303) # aca deberia enviarte a la pantalla del que acabas de correr

@router.get('/backtest/ticker/{ticker_id}')
def get_backtest_by_ticker(request: Request, ticker_id: UUID, strategy_id: UUID = Query(...)):
    
    result = backtest_service.get_performances_by_strategy_ticker(ticker_id=ticker_id, strategy_id=strategy_id)
    
    if result.ok:
        bot_performance_vm = [BotPerformanceVM.model_validate(performance) for performance in result.item]
        return templates.TemplateResponse("/backtest/view_performances.html", {"request": request, "performances": bot_performance_vm})

    else:
        return {'error': result.message}

@router.get('/backtest/bot/{bot_id}')
def get_bot_backtes(request: Request, bot_id: UUID, date_from: date = Query(...), date_to: date = Query(...)):
    result = backtest_service.get_performances_by_bot_dates(bot_id=bot_id, date_from=date_from, date_to=date_to)
    
    if result.ok:
        bot_performance = result.item
        
        bot_performance_vm = BotPerformanceVM.model_validate(bot_performance)
        bot_performance_vm.TradeHistory = sorted(bot_performance_vm.TradeHistory, key=lambda trade: trade.ExitTime)

        # Equity plot
        dates = [trade.ExitTime for trade in bot_performance_vm.TradeHistory]
        equity = [trade.Equity for trade in bot_performance_vm.TradeHistory]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=equity,
                            mode='lines',
                            name='equity original'))
        fig.update_layout(
            xaxis_title='Time',
            yaxis_title='Equity'
        )
        equity_plot = fig.to_json()
        
        # LuckTest Plot
        result = backtest_service.get_luck_test_equity_curve(bot_performance_vm.Id)
        if not result.ok:
            return {'error': result.error}
        
        luck_test_equity_curve = result.item
        
        result = backtest_service.get_luck_test_equity_curve(bot_performance_vm.Id, remove_only_good_luck=True)
        if not result.ok:
            return {'error': result.error} 
        
        luck_test_remove_only_good = result.item
       
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=equity,
                            mode='lines',
                            name='Equity'))

        fig.add_trace(go.Scatter(x=luck_test_equity_curve.ExitTime, y=luck_test_equity_curve.Equity,
                            mode='lines',
                            name=f'Luck test'))
        
        fig.add_trace(go.Scatter(x=luck_test_remove_only_good.ExitTime, y=luck_test_remove_only_good.Equity,
                            mode='lines',
                            name=f'Luck test (BL)'))

        fig.update_layout(
            xaxis_title='Time',
            yaxis_title='Equity'
        )   
        luck_test_plot = fig.to_json()
        
        
        
        return templates.TemplateResponse(
            "/backtest/view_bot_performance.html", 
            {
                "request": request, 
                "performance": bot_performance_vm, 
                'equity_plot': equity_plot,
                'luck_test_plot': luck_test_plot
            }
        )
        
    else:
        return {'error': result.message}

@router.post('/backtest/{bot_performance_id}/montecarlo')
def run_montecarlo_test(request: Request, bot_performance_id:UUID):
    
    result = backtest_service.run_montecarlo_test(
        bot_performance_id=bot_performance_id, 
        n_simulations=1000, # Viene del front
        threshold_ruin=0.9 # Viene del front
    )
    
    if result.ok:
        referer = request.headers.get('referer')  # Obtiene la URL de la página anterior
        return RedirectResponse(url=referer, status_code=303)

    else:
        return {'error': result.message}
    
@router.post('/backtest/{performance_id}/luck_test')
def run_luck_test(request: Request, performance_id:UUID):
    
    result = backtest_service.run_luck_test(
        bot_performance_id=performance_id, 
        trades_percent_to_remove=5 
    )
    
    if result.ok:
        referer = request.headers.get('referer')  # Obtiene la URL de la página anterior
        return RedirectResponse(url=referer, status_code=303)

    else:
        return {'error': result.message}
     
    

    
    