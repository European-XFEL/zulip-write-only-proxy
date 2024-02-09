from pathlib import Path

import fastapi
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .. import models

router = fastapi.APIRouter()

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def root(request: fastapi.Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/client/create", tags=["Admin"], response_class=HTMLResponse)
async def create_client_interface(request: fastapi.Request):
    schema = models.ScopedClientCreate.model_json_schema()
    optional = schema["properties"]
    required = {field: optional.pop(field) for field in schema["required"]}
    return templates.TemplateResponse(
        "create.html", {"request": request, "required": required, "optional": optional}
    )


@router.get("/client/list", tags=["Admin"], response_class=HTMLResponse)
async def list_client_interface(request: fastapi.Request):
    return templates.TemplateResponse("list.html", {"request": request})
