from fastapi import APIRouter

from app.domains.crm.api.customer_users import router as customer_users_router
from app.domains.crm.api.customers import router as customers_router

router = APIRouter()
router.include_router(customers_router)
router.include_router(customer_users_router)

__all__ = ["router"]
