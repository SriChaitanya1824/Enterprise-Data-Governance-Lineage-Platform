from fastapi import APIRouter

from app.api import catalog, governance, identity, lineage, reporting

router = APIRouter()
for module in [identity, catalog, lineage, governance, reporting]:
    router.include_router(module.router)
