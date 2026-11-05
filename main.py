from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date
import mysql.connector

app = FastAPI(title="Torneo Interfacultades UCU - Backend")

class JugadorNuevo(BaseModel):
    ci: str
    nombre: str
    apellido: str
    email: str
    fecha_nacimiento: date
    id_facultad: int
    tipo: str

def conectar_bd(rol: str):
    if rol == "administrador":
        usuario = "app_admin"
        clave = "admin123"
    elif rol == "planillero":
        usuario = "app_planillero"
        clave = "plani123"
    else:
        usuario = "lol"
        clave = "lol"

    try:
        conexion = mysql.connector.connect(
            host="db",
            user=usuario,
            password=clave,
            database="torneo_ucu"
        )
        return conexion
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.post("/jugadores")
def crear_jugador(jugador: JugadorNuevo):
    conexion = conectar_bd("administrador")
    cursor = conexion.cursor()
    
    try:
        sql = "INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        valores = (jugador.ci, jugador.nombre, jugador.apellido, jugador.email, jugador.fecha_nacimiento, jugador.id_facultad, jugador.tipo)
        
        cursor.execute(sql, valores)
        conexion.commit()
        
        return {"mensaje": f"Jugador {jugador.nombre} {jugador.apellido} dado de alta con exito"}
        
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=str(err))
        
    finally:
        cursor.close()
        conexion.close()