from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import mysql.connector

import maestros
import equipos
import partidos
import planillas
import sanciones
import consultas
import paginas
from comun import conectar_bd, guardar_sesion, borrar_sesion

app = FastAPI(title="Torneo Interfacultades UCU - Backend")

app.include_router(maestros.router)
app.include_router(equipos.router)
app.include_router(partidos.router)
app.include_router(planillas.router)
app.include_router(sanciones.router)
app.include_router(consultas.router)
app.include_router(paginas.router)
app.mount("/static", StaticFiles(directory="static"), name="static")


class LoginDatos(BaseModel):
    correo: str
    contraseña: str


@app.post("/login")
def iniciar_sesion(datos: LoginDatos, response: Response):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor(dictionary=True)

        # La contraseña se guarda como hash SHA-256
        sql = "SELECT rol FROM login WHERE correo = %s AND contraseña = SHA2(%s, 256)"
        cursor.execute(sql, (datos.correo, datos.contraseña))
        usuario_encontrado = cursor.fetchone()

        cursor.close()
        conexion.close()

        if usuario_encontrado:
            guardar_sesion(response, datos.correo, usuario_encontrado['rol'])
            return {"mensaje": "Login exitoso", "rol": usuario_encontrado['rol']}
        else:
            return {"error": "Correo o contraseña incorrectos"}

    except mysql.connector.Error as err:
        return {"error": f"Error conectando a la base: {err}"}


@app.post("/logout")
def cerrar_sesion(response: Response):
    borrar_sesion(response)
    return {"mensaje": "Sesión cerrada"}
