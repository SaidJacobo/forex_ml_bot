from typing import List, Optional
from fastapi import APIRouter
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from backbone.services.ticker_service import TickerService


class TickerVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id:UUID
    CategoryId:UUID
    Name: str
    Commission: float

class CategoriesVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id:UUID
    Name: str
    Tickers: Optional[List[TickerVM]] = None  # Relación con Tickers

    

router = APIRouter()

templates = Jinja2Templates(directory="./templates")

ticker_service = TickerService()

@router.get("/categories/", response_class=HTMLResponse)
async def categories(request: Request):
    result = ticker_service.get_all()
    
    if result.ok:

        categories_vm = []
        for category in result.item:
            category_vm = CategoriesVM.model_validate(category)
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
    
    print('id de la categoria:', category_id)
    result = ticker_service.get_tickers_by_category(category_id=category_id)

    if result.ok:
        tickers = [TickerVM.model_validate(ticker) for ticker in result.item]
        print(tickers)
        return templates.TemplateResponse("/tickers/tickers.html", {"request": request, "tickers": tickers})
    else:
        return {
            "message": "Error",
            "data": result.message
        }



@router.post("/categories/update_commissions")
async def update_commissions():
    
    result = ticker_service.create()
    
    return RedirectResponse(url="/tickers/", status_code=303)

    
    
