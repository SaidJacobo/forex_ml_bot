from uuid import UUID
from fastapi import APIRouter
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from app.view_models.strategy_vm import StrategyVM
from backbone.services.strategy_service import StrategyService


router = APIRouter()

templates = Jinja2Templates(directory="./app/templates")

strategy_service = StrategyService()

# Ruta GET: muestra el formulario
@router.get("/strategies", response_class=HTMLResponse)
async def form_page(request: Request):
    result = strategy_service.get_all()
    
    if result.ok:
        strategies = [StrategyVM.model_validate(strategy) for strategy in result.item]
        return templates.TemplateResponse("/strategies/index.html", {"request": request, "strategies": strategies})
    else:
        print(result)
        return {
            "message": "Error",
            "data": result.message
        }


# Ruta GET: muestra el formulario
@router.get("/strategies/new", response_class=HTMLResponse)
async def create_get(request: Request):
    return templates.TemplateResponse("/strategies/create.html", {"request": request})


# Ruta POST: Procesa datos del formulario
@router.post("/strategies")
async def create_post(
    name: str = Form(...),
    description: str = Form(...),
):
    try:

        result = strategy_service.create(name=name, description=description)
        
        if result.ok:
            strategy_vm = StrategyVM.model_validate(result.item)
            return RedirectResponse(url="/strategies", status_code=303)

        else:
            return {
                "message": "Error",
                "data": result.message
            }
            

    except ValidationError as e:
        return {"error": e.errors()}
    
    
@router.get("/strategies/{strategy_id}")
async def update_get(request: Request, strategy_id: UUID):

    # Obtener la estrategia de la base de datos
    result = strategy_service.get_by_id(strategy_id)
    
    if result.ok:
        strategy = result.item  # Estrategia obtenida
        return templates.TemplateResponse("/strategies/update.html", {"request": request, "strategy": strategy})
    
    return {
        "message": "Error",
        "data": result.message
    }


@router.post("/strategies/{strategy_id}")
async def update_post(
    id:UUID = Form(...),
    name: str = Form(...),
    description: str = Form(...),
):
    print(id, name, description)
    result = strategy_service.update(id=id, name=name, description=description)

    if result.ok:

        return RedirectResponse(url="/strategies", status_code=303)
    
    return {
        "message": "Error",
        "data": result.message
    }


@router.post("/strategies/{strategy_id}/delete")
async def delete(strategy_id: UUID):
    result = strategy_service.delete(id=strategy_id)
    
    if result.ok:
        return RedirectResponse(url="/strategies/", status_code=303)

    else:
        return {
            "message": "Error",
            "data": result.message
        }