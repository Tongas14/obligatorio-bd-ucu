from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from comun import rol_de_la_sesion

router = APIRouter()

PAGINA_SIN_PERMISO = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<link rel="stylesheet" href="/static/estilos.css"><title>Sin permisos</title></head>
<body><main><h1>Sin permisos</h1><p>Su usuario no tiene acceso a esta sección.</p>
<p><a href="/">Volver al inicio</a></p></main></body></html>"""


def pagina_protegida(request: Request, archivo: str, *roles_permitidos):
    # Se controla el rol también al pedir la página, para que no alcance con escribir la URL a mano
    rol = rol_de_la_sesion(request)
    if rol is None:
        return RedirectResponse("/login")
    if rol not in roles_permitidos:
        return HTMLResponse(PAGINA_SIN_PERMISO, status_code=403)
    return FileResponse(f"static/{archivo}")


@router.get("/", include_in_schema=False)
def inicio(request: Request):
    rol = rol_de_la_sesion(request)
    if rol == "administrador":
        return RedirectResponse("/admin/partidos")
    if rol == "planillero":
        return RedirectResponse("/planillero")
    return RedirectResponse("/login")


@router.get("/sesion", include_in_schema=False)
def sesion_actual(request: Request):
    return {"rol": rol_de_la_sesion(request)}


@router.get("/login", include_in_schema=False)
def pagina_login():
    return FileResponse("static/login.html")


@router.get("/admin/partidos", include_in_schema=False)
def pagina_partidos(request: Request):
    return pagina_protegida(request, "partidos.html", "administrador")


@router.get("/admin/sanciones", include_in_schema=False)
def pagina_sanciones(request: Request):
    return pagina_protegida(request, "sanciones.html", "administrador")


@router.get("/admin/consultas", include_in_schema=False)
def pagina_consultas(request: Request):
    return pagina_protegida(request, "consultas.html", "administrador")


@router.get("/planillero", include_in_schema=False)
def pagina_planillero(request: Request):
    return pagina_protegida(request, "planillero.html", "administrador", "planillero")
