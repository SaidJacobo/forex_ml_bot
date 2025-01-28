from datetime import date
import json
import os
from typing import Optional
from fastapi import APIRouter, Query
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pandas import Timestamp
from app.backbone.services.bot_service import BotService
from app.backbone.services.strategy_service import StrategyService
from app.backbone.services.test_service import TestService
from app.view_models.backtest_create_vm import BacktestCreateVM
from app.view_models.bot_performance_metrics_vm import PerformanceMetricsVM
from app.view_models.bot_performance_vm import BotPerformanceVM
from app.view_models.category_vm import CategoryVM
from app.view_models.strategy_vm import StrategyVM
from app.view_models.ticker_vm import TickerVM
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
test_service = TestService()
bot_service = BotService()

@router.get("/backtest", response_class=HTMLResponse)
async def backtest_strategies(request: Request):
    result_strategies = strategy_service.get_used_strategies()
    
    if result_strategies.ok:
        strategies_vm = [StrategyVM.model_validate(strategy) for strategy in result_strategies.item]
        return templates.TemplateResponse("/backtest/index.html", {"request": request, 'strategies': strategies_vm})

    else:
        return {
            "message": "Error",
            "data": result_strategies.message
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
    
    return RedirectResponse(url="/backtest", status_code=303)

@router.get('/backtest/ticker/{ticker_id}')
def get_backtest_by_ticker(request: Request, ticker_id: UUID, strategy_id: UUID = Query(...)):
    
    result = backtest_service.get_performances_by_strategy_ticker(ticker_id=ticker_id, strategy_id=strategy_id)
    
    if result.ok:
        bot_performance_vm = [PerformanceMetricsVM.model_validate(performance) for performance in result.item]
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
        
        str_date_from = str(bot_performance.DateFrom).replace('-','')
        str_date_to = str(bot_performance.DateFrom).replace('-','')
        file_name=f'{bot_performance.Bot.Name}_{str_date_from}_{str_date_to}.html'
        
        luck_test_plot = None
        luck_plot_path = './app/templates/static/luck_test_plots'
        
        if os.path.exists(os.path.join(luck_plot_path, file_name)):
            with open(os.path.join(luck_plot_path, file_name), 'r') as f:
                luck_test_plot = json.load(f)  # Cargar el contenido JSON

        correlation_test_plot = None
        correlation_plot_path = './app/templates/static/correlation_plots'
        if os.path.exists(os.path.join(correlation_plot_path, file_name)):
            with open(os.path.join(correlation_plot_path, file_name), 'r') as f:
                correlation_test_plot = json.load(f)  # Cargar el contenido JSON
                
            bot_performance_vm.HasCorrelationTest = True

        
        return templates.TemplateResponse(
            "/backtest/view_bot_performance.html", 
            {
                "request": request, 
                "performance": bot_performance_vm, 
                'equity_plot': equity_plot,
                'luck_test_plot': luck_test_plot or {"data": [], "layout": {}},
                'correlation_test_plot': correlation_test_plot or {"data": [], "layout": {}},
            }
        )
        
    else:
        return {'error': result.message}

@router.get('/backtest/{bot_performance_id}/montecarlo', response_class=HTMLResponse)
async def get_montecarlo_modal(request: Request, bot_performance_id: UUID):
    performance = {"Id": bot_performance_id}
    return templates.TemplateResponse("/backtest/montecarlo_form.html", {"request": request, "performance": performance})

@router.post('/backtest/{bot_performance_id}/montecarlo')
def run_montecarlo_test(
    request: Request, 
    bot_performance_id:UUID,
    simulations: int = Form(...),
    threshold_ruin: float = Form(...),
):
    
    result = test_service.run_montecarlo_test(
        bot_performance_id=bot_performance_id, 
        n_simulations=simulations,
        threshold_ruin=threshold_ruin
    )
    
    if result.ok:
        referer = request.headers.get('referer')  # Obtiene la URL de la página anterior
        return RedirectResponse(url=referer, status_code=303)

    else:
        return {'error': result.message}

@router.get('/backtest/{bot_performance_id}/luck_test', response_class=HTMLResponse)
async def get_luck_test_modal(request: Request, bot_performance_id: UUID):
    performance = {"Id": bot_performance_id}
    return templates.TemplateResponse("/backtest/luck_test_form.html", {"request": request, "performance": performance})

@router.post('/backtest/{performance_id}/luck_test')
def run_luck_test(request: Request, performance_id:UUID, percent_trades_to_remove: int = Form(...)):

    result = test_service.run_luck_test(
        bot_performance_id=performance_id, 
        trades_percent_to_remove=percent_trades_to_remove 
    )
    
    if result.ok:
        referer = request.headers.get('referer')  # Obtiene la URL de la página anterior
        return RedirectResponse(url=referer, status_code=303)

    else:
        return {'error': result.message}

@router.get('/backtest/{bot_performance_id}/random_test', response_class=HTMLResponse)
async def get_random_test_modal(request: Request, bot_performance_id: UUID):
    performance = {"Id": bot_performance_id}
    return templates.TemplateResponse("/backtest/random_test_form.html", {"request": request, "performance": performance})

@router.post('/backtest/{performance_id}/random_test')
def run_random_test(request: Request, performance_id:UUID, iterations: int = Form(...)):

    result = test_service.run_random_test(performance_id, n_iterations=iterations)
    
    if result.ok:
        referer = request.headers.get('referer')  # Obtiene la URL de la página anterior
        return RedirectResponse(url=referer, status_code=303)

    else:
        return {'error': result.message}

@router.post('/backtest/{performance_id}/correlation_test')
def run_correlation_test(request: Request, performance_id:UUID):

    result = test_service.run_correlation_test(performance_id)
    
    if result.ok:
        referer = request.headers.get('referer')  # Obtiene la URL de la página anterior
        return RedirectResponse(url=referer, status_code=303)

    else:
        return {'error': result.message}

@router.post('/backtest/{performance_id}/delete')
def run_correlation_test(request: Request, performance_id:UUID):
    result = backtest_service.delete(performance_id)
    
    if result.ok:
        return RedirectResponse(url='/backtest', status_code=303)
    else:
        return {'error': result.message}
        
@router.get('/backtest/strategies/{strategy_id}/get_robusts', response_class=HTMLResponse)
def get_robusts(request: Request, strategy_id:UUID):
    result = backtest_service.get_robusts_by_strategy_id(strategy_id=strategy_id)
    
    if result.ok:
        bot_performances_vm = [PerformanceMetricsVM.model_validate(performance) for performance in result.item]
        
        return templates.TemplateResponse("/backtest/modal_robust.html", {"request": request, "performances": bot_performances_vm})
    
    else:
        return {'error': result.message}
     
@router.get("/backtest/strategies/{strategy_id}/tickers")
async def get_tickers_by_strategy(request: Request, strategy_id: UUID):

    result = ticker_service.get_tickers_by_strategy(strategy_id)
    if result.ok:
        tickers = [TickerVM.model_validate(ticker) for ticker in result.item]
        
        return templates.TemplateResponse("/backtest/modal_tickers.html", {"request": request, "tickers": tickers, "strategy_id":strategy_id})
    else:
        return {'error': result.message}
    
@router.post("/backtest/{performance_id}/favorites")
async def update_favorites(request: Request, performance_id: UUID):
    result = backtest_service.update_favorite(performance_id)
    if result.ok:
        return {'result':  result.item.Favorite}
    
    else:
        return {'result': result.error}
    
    


