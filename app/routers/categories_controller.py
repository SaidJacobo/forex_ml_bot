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

@router.get("/categories/", response_class=HTMLResponse)
async def categories(request: Request):
    result = ticker_service.get_all_categories()
    
    if result.ok:

        categories_vm = []
        for category in result.item:
            category_vm = CategoryVM.model_validate(category)
            category_vm.Tickers = [TickerVM.model_validate(ticker) for ticker in category.Tickers]
            
            categories_vm.append(category_vm)
        
        return templates.TemplateResponse("/tickers/categories.html", {"request": request, "categories": categories_vm})

    else:
        return {
            "message": "Error",
            "data": result.message
        }
        
        
@router.get('/categories/{category_id}/tickers')
def category_tickers(request: Request, category_id: UUID):
    result = ticker_service.get_tickers_by_category(category_id=category_id)

    if result.ok:
        tickers = [TickerVM.model_validate(ticker) for ticker in result.item]
        
        # Verifica el encabezado Accept
        if "application/json" in request.headers.get("Accept", ""):
            # Retorna JSON si se solicita
            return tickers  # FastAPI automáticamente serializa listas de Pydantic a JSON
        else:
            # Retorna HTML como antes
            return templates.TemplateResponse("/tickers/tickers.html", {"request": request, "tickers": tickers})
    else:
        error_response = {"message": "Error", "data": result.message}
        if "application/json" in request.headers.get("Accept", ""):
            return error_response  # Respuesta JSON en caso de error
        else:
            return templates.TemplateResponse("/error.html", {"request": request, "error": error_response})



@router.post("/categories/update_commissions")
async def update_commissions():
    result = ticker_service.create()
    return RedirectResponse(url="/categories/", status_code=303)



    
    
