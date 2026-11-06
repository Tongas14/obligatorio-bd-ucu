import os
import hmac
import hashlib
import mysql.connector
from fastapi import Request, HTTPException, Response

USUARIOS_BD = {
    "administrador": ("app_admin", "admin123"),
    "planillero": ("app_planillero", "plani123"),
}

CLAVE_SESION = os.getenv("CLAVE_SESION", "clave-de-desarrollo-cambiar")
COOKIE_SESION = "sesion"


def conectar_bd(rol: str):
    usuario, clave = USUARIOS_BD[rol]
    conexion = mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=usuario,
        password=clave,
        database=os.getenv("DB_NAME", "torneo_ucu"),
    )
    return conexion


def ahora_bd(cursor):
    # Se usa la hora de MySQL para que Python y los triggers comparen contra el mismo reloj
    cursor.execute("SELECT NOW() AS ahora")
    return cursor.fetchone()["ahora"]


def _firma(valor: str) -> str:
    return hmac.new(CLAVE_SESION.encode(), valor.encode(), hashlib.sha256).hexdigest()


def guardar_sesion(response: Response, correo: str, rol: str):
    valor = f"{correo}|{rol}"
    response.set_cookie(COOKIE_SESION, f"{valor}|{_firma(valor)}", httponly=True, samesite="lax")


def borrar_sesion(response: Response):
    response.delete_cookie(COOKIE_SESION)


def rol_de_la_sesion(request: Request):
    cookie = request.cookies.get(COOKIE_SESION, "")
    partes = cookie.split("|")
    if len(partes) != 3:
        return None
    correo, rol, firma = partes
    if not hmac.compare_digest(firma, _firma(f"{correo}|{rol}")) or rol not in USUARIOS_BD:
        return None
    return rol


def requiere_rol(*roles_permitidos):
    def verificar(request: Request) -> str:
        rol = rol_de_la_sesion(request)
        if rol is None:
            raise HTTPException(status_code=401, detail="Debe iniciar sesión")
        if rol not in roles_permitidos:
            raise HTTPException(status_code=403, detail="No tiene permisos para esta sección")
        return rol
    return verificar


def mensaje_error_bd(err) -> str:
    # Los triggers devuelven SQLSTATE 45000 con un mensaje pensado para el usuario
    if getattr(err, "sqlstate", None) == "45000":
        return err.msg
    return f"Error en la base de datos: {err.msg}"
