from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import date
import mysql.connector
from typing import List

import partidos
import planillas
import sanciones
import consultas
import paginas
from comun import conectar_bd, guardar_sesion, borrar_sesion

app = FastAPI(title="Torneo Interfacultades UCU - Backend")

app.include_router(partidos.router)
app.include_router(planillas.router)
app.include_router(sanciones.router)
app.include_router(consultas.router)
app.include_router(paginas.router)
app.mount("/static", StaticFiles(directory="static"), name="static")

class LoginDatos(BaseModel):
    correo: str
    contraseña: str

class JugadorNuevo(BaseModel):
    ci: str
    nombre: str
    apellido: str
    email: str
    fecha_nacimiento: date
    id_facultad: int
    tipo: str

class TorneoNuevo(BaseModel):
    id_torneo: int
    nombre: str
    año: int
    semestre: int
    fecha_inicio: date
    fecha_fin: date
    estado: str

@app.post("/login")
def iniciar_sesion(datos: LoginDatos, response: Response):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor(dictionary=True)
        
        sql = "SELECT rol FROM login WHERE correo = %s AND contraseña = %s"
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


@app.post("/jugadores")
def crear_jugador(jugador: JugadorNuevo):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        
        sql = "INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        valores = (jugador.ci, jugador.nombre, jugador.apellido, jugador.email, jugador.fecha_nacimiento, jugador.id_facultad, jugador.tipo)
        
        cursor.execute(sql, valores)
        conexion.commit()
        
        cursor.close()
        conexion.close()
        
        return {"mensaje": f"Jugador {jugador.nombre} dado de alta"}
        
    except mysql.connector.Error as err:
        return {"error": f"No se pudo guardar el jugador: {err}"}

@app.put("/jugadores/{ci}")
def modificar_jugador(ci: str, jugador: JugadorNuevo):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        
        sql = "UPDATE jugador SET nombre=%s, apellido=%s, email=%s, fecha_nacimiento=%s, id_facultad=%s, tipo=%s WHERE ci=%s"
        valores = (jugador.nombre, jugador.apellido, jugador.email, jugador.fecha_nacimiento, jugador.id_facultad, jugador.tipo, ci)
        
        cursor.execute(sql, valores)
        conexion.commit()
        
        filas_afectadas = cursor.rowcount
        
        cursor.close()
        conexion.close()
        
        if filas_afectadas == 0:
            return {"error": "No existe ningún jugador con esa CI"}
            
        return {"mensaje": "Jugador modificado con exito"}
        
    except mysql.connector.Error as err:
        return {"error": f"No se pudo modificar: {err}"}

@app.delete("/jugadores/{ci}")
def eliminar_jugador(ci: str):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        
        sql = "DELETE FROM jugador WHERE ci = %s"
        cursor.execute(sql, (ci,))
        conexion.commit()
        
        filas_afectadas = cursor.rowcount
        
        cursor.close()
        conexion.close()
        
        if filas_afectadas == 0:
            return {"error": "No existe ningún jugador con esa CI para borrar"}
            
        return {"mensaje": "Jugador eliminado con exito"}
        
    except mysql.connector.Error as err:
        return {"error": f"No se pudo eliminar: {err}"}

@app.post("/torneos")
def crear_torneo(torneo: TorneoNuevo):
    if torneo.estado not in ["inscripción", "en curso", "finalizado"]:
        return {"error": "El estado solo puede ser: inscripción, en curso o finalizado"}

    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        
        sql = "INSERT INTO torneo (id_torneo, nombre, año, semestre, fecha_inicio, fecha_fin, estado) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        valores = (torneo.id_torneo, torneo.nombre, torneo.año, torneo.semestre, torneo.fecha_inicio, torneo.fecha_fin, torneo.estado)
        
        cursor.execute(sql, valores)
        conexion.commit()
        
        cursor.close()
        conexion.close()
        
        return {"mensaje": f"Torneo {torneo.nombre} dado de alta"}
        
    except mysql.connector.Error as err:
        return {"error": f"No se pudo guardar en la base de datos: {err}"}

@app.put("/torneos/{id_torneo}")
def modificar_torneo(id_torneo: int, torneo: TorneoNuevo):
    if torneo.estado not in ["inscripción", "en curso", "finalizado"]:
        return {"error": "El estado solo puede ser: inscripción, en curso o finalizado"}

    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        
        sql = "UPDATE torneo SET nombre=%s, año=%s, semestre=%s, fecha_inicio=%s, fecha_fin=%s, estado=%s WHERE id_torneo=%s"
        valores = (torneo.nombre, torneo.año, torneo.semestre, torneo.fecha_inicio, torneo.fecha_fin, torneo.estado, id_torneo)
        
        cursor.execute(sql, valores)
        conexion.commit()
        
        filas_afectadas = cursor.rowcount
        
        cursor.close()
        conexion.close()
        
        if filas_afectadas == 0:
            return {"error": "No existe ningún torneo con ese ID"}
            
        return {"mensaje": "Torneo modificado con exito"}
        
    except mysql.connector.Error as err:
        return {"error": f"No se pudo modificar: {err}"}

@app.delete("/torneos/{id_torneo}")
def eliminar_torneo(id_torneo: int):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        
        sql = "DELETE FROM torneo WHERE id_torneo = %s"
        cursor.execute(sql, (id_torneo,))
        conexion.commit()
        
        filas_afectadas = cursor.rowcount
        
        cursor.close()
        conexion.close()
        
        if filas_afectadas == 0:
            return {"error": "No existe ningún torneo con ese ID para borrar"}
            
        return {"mensaje": "Torneo eliminado con exito"}
        
    except mysql.connector.Error as err:
        return {"error": f"No se pudo eliminar: {err}"}

class JugadorPlantel(BaseModel):
    ci: str
    dorsal: int

class EquipoNuevo(BaseModel):
    id_equipo: int
    nombre: str
    id_torneo: int
    id_facultad: int
    ci_capitan: str
    jugadores: List[JugadorPlantel]

@app.post("/equipos")
def crear_equipo(equipo: EquipoNuevo):
    if len(equipo.jugadores) < 5 or len(equipo.jugadores) > 10:
        return {"error": "El equipo debe tener entre 5 y 10 jugadores"}

    cis_jugadores = [j.ci for j in equipo.jugadores]
    if equipo.ci_capitan not in cis_jugadores:
        return {"error": "El capitán tiene que ser uno de los jugadores inscriptos"}

    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor(dictionary=True)
        
        cursor.execute("SELECT estado FROM torneo WHERE id_torneo = %s", (equipo.id_torneo,))
        torneo = cursor.fetchone()
        if not torneo or torneo['estado'] != "inscripción":
            return {"error": "Solo se pueden anotar equipos si el torneo está en 'inscripción'"}

        cantidad_docentes_func = 0
        
        for j in equipo.jugadores:
            cursor.execute("SELECT id_facultad, tipo FROM jugador WHERE ci = %s", (j.ci,))
            datos_j = cursor.fetchone()
            
            if not datos_j:
                return {"error": f"El jugador con CI {j.ci} no existe en el sistema"}
                
            if datos_j['id_facultad'] != equipo.id_facultad:
                return {"error": f"El jugador {j.ci} no pertenece a la facultad del equipo"}
                
            if datos_j['tipo'] in ['docente', 'funcionario']:
                cantidad_docentes_func += 1
                
            cursor.execute("SELECT id_equipo FROM equipo_jugador_torneo WHERE ci_jugador = %s AND id_torneo = %s", (j.ci, equipo.id_torneo))
            if cursor.fetchone():
                return {"error": f"El jugador {j.ci} ya está anotado en otro equipo en este torneo"}

        if cantidad_docentes_func > 2:
            return {"error": "No puede haber más de 2 docentes o funcionarios por equipo"}

        sql_equipo = "INSERT INTO equipo (id_equipo, nombre, id_torneo, id_facultad, ci_capitan) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql_equipo, (equipo.id_equipo, equipo.nombre, equipo.id_torneo, equipo.id_facultad, equipo.ci_capitan))

        for j in equipo.jugadores:
            sql_plantel = "INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, dorsal) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql_plantel, (equipo.id_equipo, j.ci, equipo.id_torneo, j.dorsal))

        conexion.commit() 
        
        cursor.close()
        conexion.close()
        return {"mensaje": f"Equipo '{equipo.nombre}' inscripto con éxito con {len(equipo.jugadores)} jugadores."}

    except mysql.connector.Error as err:
        conexion.rollback() 
        return {"error": f"Error al guardar en la base de datos: {err}"}

class FacultadNueva(BaseModel):
    id_facultad: int
    nombre: str

class ComplejoNuevo(BaseModel):
    id_complejo: int
    nombre: str
    direccion: str
    ciudad: str

class CanchaNueva(BaseModel):
    nombre: str
    id_complejo: int
    tipo_suelo: str
    techada: bool

@app.post("/facultades")
def crear_facultad(facultad: FacultadNueva):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        sql = "INSERT INTO facultad (id_facultad, nombre) VALUES (%s, %s)"
        cursor.execute(sql, (facultad.id_facultad, facultad.nombre))
        conexion.commit()
        cursor.close()
        conexion.close()
        return {"mensaje": f"Facultad '{facultad.nombre}' dada de alta"}
    except mysql.connector.Error as err:
        return {"error": f"Error al guardar: {err}"}

@app.put("/facultades/{id_facultad}")
def modificar_facultad(id_facultad: int, facultad: FacultadNueva):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        sql = "UPDATE facultad SET nombre = %s WHERE id_facultad = %s"
        cursor.execute(sql, (facultad.nombre, id_facultad))
        conexion.commit()
        filas = cursor.rowcount
        cursor.close()
        conexion.close()
        if filas == 0:
            return {"error": "Facultad no encontrada"}
        return {"mensaje": "Facultad modificada con éxito"}
    except mysql.connector.Error as err:
        return {"error": f"Error al modificar: {err}"}

@app.delete("/facultades/{id_facultad}")
def eliminar_facultad(id_facultad: int):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        sql = "DELETE FROM facultad WHERE id_facultad = %s"
        cursor.execute(sql, (id_facultad,))
        conexion.commit()
        filas = cursor.rowcount
        cursor.close()
        conexion.close()
        if filas == 0:
            return {"error": "Facultad no encontrada"}
        return {"mensaje": "Facultad eliminada con éxito"}
    except mysql.connector.Error as err:
        return {"error": f"Error al eliminar: {err}"}

@app.post("/complejos")
def crear_complejo(complejo: ComplejoNuevo):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        sql = "INSERT INTO complejo (id_complejo, nombre, direccion, ciudad) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (complejo.id_complejo, complejo.nombre, complejo.direccion, complejo.ciudad))
        conexion.commit()
        cursor.close()
        conexion.close()
        return {"mensaje": f"Complejo '{complejo.nombre}' dado de alta"}
    except mysql.connector.Error as err:
        return {"error": f"Error al guardar: {err}"}

@app.put("/complejos/{id_complejo}")
def modificar_complejo(id_complejo: int, complejo: ComplejoNuevo):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        sql = "UPDATE complejo SET nombre=%s, direccion=%s, ciudad=%s WHERE id_complejo=%s"
        cursor.execute(sql, (complejo.nombre, complejo.direccion, complejo.ciudad, id_complejo))
        conexion.commit()
        filas = cursor.rowcount
        cursor.close()
        conexion.close()
        if filas == 0:
            return {"error": "Complejo no encontrado"}
        return {"mensaje": "Complejo modificado con éxito"}
    except mysql.connector.Error as err:
        return {"error": f"Error al modificar: {err}"}

@app.delete("/complejos/{id_complejo}")
def eliminar_complejo(id_complejo: int):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        sql = "DELETE FROM complejo WHERE id_complejo = %s"
        cursor.execute(sql, (id_complejo,))
        conexion.commit()
        filas = cursor.rowcount
        cursor.close()
        conexion.close()
        if filas == 0:
            return {"error": "Complejo no encontrado"}
        return {"mensaje": "Complejo eliminado con éxito"}
    except mysql.connector.Error as err:
        return {"error": f"Error al eliminar: {err}"}

@app.post("/canchas")
def crear_cancha(cancha: CanchaNueva):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        sql = "INSERT INTO cancha (nombre, id_complejo, tipo_suelo, techada) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (cancha.nombre, cancha.id_complejo, cancha.tipo_suelo, cancha.techada))
        conexion.commit()
        cursor.close()
        conexion.close()
        return {"mensaje": f"Cancha '{cancha.nombre}' dada de alta"}
    except mysql.connector.Error as err:
        return {"error": f"Error al guardar: {err}"}

@app.put("/canchas/{nombre_cancha}")
def modificar_cancha(nombre_cancha: str, cancha: CanchaNueva):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        sql = "UPDATE cancha SET id_complejo=%s, tipo_suelo=%s, techada=%s WHERE nombre=%s"
        cursor.execute(sql, (cancha.id_complejo, cancha.tipo_suelo, cancha.techada, nombre_cancha))
        conexion.commit()
        filas = cursor.rowcount
        cursor.close()
        conexion.close()
        if filas == 0:
            return {"error": "Cancha no encontrada"}
        return {"mensaje": "Cancha modificada con éxito"}
    except mysql.connector.Error as err:
        return {"error": f"Error al modificar: {err}"}

@app.delete("/canchas/{nombre_cancha}")
def eliminar_cancha(nombre_cancha: str):
    try:
        conexion = conectar_bd("administrador")
        cursor = conexion.cursor()
        sql = "DELETE FROM cancha WHERE nombre = %s"
        cursor.execute(sql, (nombre_cancha,))
        conexion.commit()
        filas = cursor.rowcount
        cursor.close()
        conexion.close()
        if filas == 0:
            return {"error": "Cancha no encontrada"}
        return {"mensaje": "Cancha eliminada con éxito"}
    except mysql.connector.Error as err:
        return {"error": f"Error al eliminar: {err}"}