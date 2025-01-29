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
@router.get("/portfolio", response_class=HTMLResponse)
async def form_page(request: Request):
    # result = strategy_service.get_all()
    
    # if result.ok:
        # strategies = [StrategyVM.model_validate(strategy) for strategy in result.item]
    return templates.TemplateResponse("/portfolio/index.html", {"request": request})
    # else:
    #     print(result)
    #     return {
    #         "message": "Error",
    #         "data": result.message
    #     }


