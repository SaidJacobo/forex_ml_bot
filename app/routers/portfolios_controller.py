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
    

@router.get("/portfolios/admin/{portfolio_id}", response_class=HTMLResponse)
async def get_portfolios_admin(request: Request, portfolio_id:UUID):
    
    # Despues deberia tratar de que todo esto se haga por pydantic
    
    result = portfolio_service.get_portfolio_by_id(portfolio_id=portfolio_id)
    if not result.ok:
        return {'error': True, 'message': result.message}
    
    portfolio = result.item
    
    result = portfolio_service.get_backtest_from_portfolio(portfolio_id=portfolio_id)

    if not result.ok:
        return {'error': True, 'message': result.message}
    
    
    used_backtests = result.item
    
    used_backtests = [PerformanceMetricsVM.model_validate(backtest) for backtest in used_backtests]
    
    portfolio_vm = PortfolioVM(
        Id=portfolio_id,
        Name=portfolio.Name,
        Description=portfolio.Description,
        # Metrics=portfolio.Metrics,
        BotPerformances = used_backtests
    )
    
    
    return templates.TemplateResponse("/portfolios/admin.html", {"request": request, 'portfolio':portfolio_vm})


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
    
    
    unique_backtests = {bt.Id: bt for bt in robusts_backtests + favorites_backtests}
    favorites_and_robusts = list(unique_backtests.values())
    
    favorites_and_robusts = [PerformanceMetricsVM.model_validate(backtest) for backtest in favorites_and_robusts]
    
    return templates.TemplateResponse("/portfolios/modal_favorites_robusts.html", {
        "request": request, 
        'favorites_and_robusts': favorites_and_robusts,
        'portfolio_id': portfolio_id
    })

@router.post("/portfolios/admin/{portfolio_id}/add/{bot_performance_id}")
async def get_portfolios_admin(request: Request, portfolio_id:UUID, bot_performance_id:UUID):
    
    #agregar el registro de botperformance-portfolio a la base de datos
    result = portfolio_service.add_performance(portfolio_id=portfolio_id, bot_performance_id=bot_performance_id)
    
    print(result)
    
    if result.ok:
        return {'ok': result.ok}
    #calcular grafico de curva de equity y enviar

    return {'ok': result.message}

@router.post("/portfolios/admin/{portfolio_id}/delete/{bot_performance_id}", response_class=HTMLResponse)
async def get_portfolios_admin(request: Request, portfolio_id:UUID, bot_performance_id:UUID):
    
    #eliminar el registro de botperformance-portfolio a la base de datos
    
    #calcular grafico de curva de equity y enviar
    
    return {}

    
