from uuid import UUID
from fastapi import APIRouter
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from app.backbone.services.backtest_service import BacktestService
from app.backbone.services.portfolio_service import PortfolioService
from app.view_models.bot_performance_metrics_vm import PerformanceMetricsVM
from app.view_models.bot_performance_vm import BotPerformanceVM
from app.view_models.portfolio_admin_vm import PortfolioAdminVM
from app.view_models.portfolio_metrics_vm import PortfolioPerformanceMetricsVM
from app.view_models.portfolio_vm import PortfolioVM


router = APIRouter()

templates = Jinja2Templates(directory="./app/templates")

portfolio_service = PortfolioService()
backtest_service = BacktestService()

# Ruta GET: muestra el formulario
@router.get("/portfolios", response_class=HTMLResponse)
async def form_page(request: Request):
    result = portfolio_service.get_all()
    
    if result.ok:
        portfolios = [PortfolioVM.model_validate(portfolio) for portfolio in result.item]
        
        return templates.TemplateResponse("/portfolios/index.html", {"request": request, "portfolios": portfolios})
    else:
        print(result)
        return {
            "message": "Error",
            "data": result.message
        }

@router.get("/portfolios/new", response_class=HTMLResponse)
async def create_get(request: Request):
    return templates.TemplateResponse("/portfolios/create.html", {"request": request})

@router.post("/portfolios")
async def create_post(
    name: str = Form(...),
    description: str = Form(...),
):
    try:

        result = portfolio_service.create(name=name, description=description)
        
        if result.ok:
            return RedirectResponse(url="/portfolios", status_code=303)

        else:
            return {
                "message": "Error",
                "data": result.message
            }
            

    except ValidationError as e:
        return {"error": e.errors()}

@router.get("/portfolios/{portfolio_id}/candidates", response_class=HTMLResponse)
def get_candidates(request:Request, portfolio_id):
   # Obtener todos los bt robustos
    result = backtest_service.get_robusts()
    
    if result.ok:
        robusts_backtests = result.item
    
    # OBtener todos los favoritos
    result = backtest_service.get_favorites()
    if result.ok:
        favorites_backtests = result.item
    
    result = portfolio_service.get_backtests_from_portfolio(portfolio_id=portfolio_id)
    if result.ok:
        used_backtests = result.item
    
    used_backtests_ids = [bt.Id for bt in used_backtests]
    
    unique_backtests = {bt.Id: bt for bt in robusts_backtests + favorites_backtests if bt.Id not in used_backtests_ids}
    
    favorites_and_robusts = list(unique_backtests.values())
    
    favorites_and_robusts = [PerformanceMetricsVM.model_validate(backtest) for backtest in favorites_and_robusts]
    
    return templates.TemplateResponse("/portfolios/modal_favorites_robusts.html", {
        "request": request, 
        'favorites_and_robusts': favorites_and_robusts,
        'portfolio_id': portfolio_id
    })

@router.get("/portfolios/admin/{portfolio_id}/metrics", response_class=HTMLResponse)
async def get_portfolio_metrics(request: Request, portfolio_id:UUID):
    result = portfolio_service.get_portfolio_by_id(portfolio_id=portfolio_id)
    if not result.ok:
        return {'error': True, 'message': result.message}
    
    # Obtengo todos los backtest de un portfolio
    result = portfolio_service.get_backtests_from_portfolio(portfolio_id=portfolio_id)

    if not result.ok:
        return {'error': True, 'message': result.message}
    
    used_backtests = result.item
    
    used_backtests = [PerformanceMetricsVM.model_validate(backtest) for backtest in used_backtests]
    
    # obtengo las equity curves de todos los backtest en formato df
    result = portfolio_service.get_df_trades(portfolio_id)

    if not result.ok:
        return result

    trades_with_equity = result.item

    # Obtengo la curva de equity del portfolio
    equity_curve_result = portfolio_service.get_portfolio_equity_curve(trades_with_equity)
    if not equity_curve_result.ok:
        return {'error': True, 'message': result.message}
    
    portfolio_equity_curve = equity_curve_result.item
    
    # Calculo las metricas del portfolio (return, dd, stability, negative hits, etc.)
    metrics_results = portfolio_service.get_portfolio_metrics(portfolio_equity_curve=portfolio_equity_curve)
    
    if not metrics_results.ok:
        return {'error': True, 'message': result.message}
    
    metrics = metrics_results.item
    
    result_challenge_metrics = portfolio_service.get_challenge_metrics(portfolio_equity_curve)
    if not result_challenge_metrics.ok:
        return {'error': True, 'message': result.message}
    
    challenge_metrics = result_challenge_metrics.item
    
    result_margin_metrics = portfolio_service.get_margin_metrics(trades_with_equity, portfolio_equity_curve)
    if not result_challenge_metrics.ok:
        return {'error': True, 'message': result.message}
        
    margin_metrics = result_margin_metrics.item
    
    metrics_vm = PortfolioPerformanceMetricsVM(
        StabilityRatio=metrics.stability_ratio,
        Return=metrics.return_,
        Drawdown=metrics.dd,
        RreturnDd=metrics.return_dd,
        
        PositiveHits=challenge_metrics.positive_hits,
        NegativeHits=challenge_metrics.negative_hits,
        MeanTimeToPositive=challenge_metrics.mean_time_to_positive,
        MeanTimeToNegative=challenge_metrics.mean_time_to_negative,
        StdTimeToPositive=challenge_metrics.std_time_to_positive,
        StdTimeToNegative=challenge_metrics.std_time_to_negative,
        
        MarginCalls = margin_metrics.margin_calls,
        StopOuts = margin_metrics.stop_outs
    )
    
    # Obtengo el plot del portfolio
    trades_with_equity['portfolio'] = portfolio_equity_curve
    
    equity_plot_result = portfolio_service.plot_portfolio_equity_curve(trades_with_equity)
    if not equity_plot_result.ok:
        return {'error': True, 'message': result.message}
    
    equity_plot = equity_plot_result.item
    
    return templates.TemplateResponse(
        "/portfolios/portfolio_metrics.html", 
        {
            "request": request, 
            'metrics': metrics_vm,
            'equity_plot': equity_plot
        }
    )
    


@router.get("/portfolios/admin/{portfolio_id}", response_class=HTMLResponse)
async def get_portfolios_admin(request: Request, portfolio_id:UUID):
       
    result = portfolio_service.get_portfolio_by_id(portfolio_id=portfolio_id)
    if not result.ok:
        return {'error': True, 'message': result.message}
    
    portfolio = result.item
    
    # Obtengo todos los backtest de un portfolio
    result = portfolio_service.get_backtests_from_portfolio(portfolio_id=portfolio_id)

    if not result.ok:
        return {'error': True, 'message': result.message}
    
    used_backtests = result.item
    
    used_backtests = [PerformanceMetricsVM.model_validate(backtest) for backtest in used_backtests]
    
    portfolio_vm = PortfolioVM(
        Id=portfolio_id,
        Name=portfolio.Name,
        Description=portfolio.Description,
        # Metrics=metrics_vm,
        BotPerformances = used_backtests
    )
    
    return templates.TemplateResponse(
        "/portfolios/admin.html", 
        {
            "request": request, 
            'portfolio':portfolio_vm,
        }
    )

@router.post("/portfolios/admin/{portfolio_id}/add/{bot_performance_id}")
async def get_portfolios_admin(request: Request, portfolio_id:UUID, bot_performance_id:UUID):
    
    #agregar el registro de botperformance-portfolio a la base de datos
    result = portfolio_service.add_performance(portfolio_id=portfolio_id, bot_performance_id=bot_performance_id)
    
    print(result)
    
    if result.ok:
        return {'ok': result.ok}
    #calcular grafico de curva de equity y enviar

    return {'ok': result.message}

@router.post("/portfolios/admin/{portfolio_id}/delete/{bot_performance_id}")
async def get_portfolios_admin(request: Request, portfolio_id:UUID, bot_performance_id:UUID):
    # eliminar el registro de botperformance-portfolio a la base de datos
    result = portfolio_service.delete_performance(portfolio_id=portfolio_id, bot_performance_id=bot_performance_id)
    
    print('el resultado del delete es: ', result)
    
    if result.ok:
        return {'ok': result.ok}
    #calcular grafico de curva de equity y enviar

    return {'ok': result.message}
