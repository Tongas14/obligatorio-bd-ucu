from typing import Optional
import mysql.connector
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from comun import conectar_bd, requiere_rol, mensaje_error_bd

router = APIRouter()

solo_administrador = requiere_rol("administrador")


class SancionNueva(BaseModel):
    ci_jugador: str
    id_torneo: int
    numero_fecha_inicio: int
    cantidad_fechas: int


def validar_sancion(cursor, sancion: SancionNueva) -> Optional[str]:
    if sancion.numero_fecha_inicio < 1:
        return "La fecha de inicio debe ser 1 o mayor"
    if sancion.cantidad_fechas < 1:
        return "La sanción debe ser de al menos 1 fecha"

    cursor.execute(
        "SELECT 1 FROM equipo_jugador_torneo WHERE ci_jugador = %s AND id_torneo = %s",
        (sancion.ci_jugador, sancion.id_torneo),
    )
    if not cursor.fetchone():
        return "El jugador no está inscripto en ningún equipo de esa edición"

    # El jugador no puede figurar en planillas de las fechas que abarca la sanción
    ultima_fecha = sancion.numero_fecha_inicio + sancion.cantidad_fechas - 1
    cursor.execute(
        "SELECT p.numero_fecha FROM planilla_partido pp JOIN partido p ON p.id_partido = pp.id_partido "
        "WHERE pp.ci_jugador = %s AND p.id_torneo = %s AND p.numero_fecha BETWEEN %s AND %s "
        "ORDER BY p.numero_fecha LIMIT 1",
        (sancion.ci_jugador, sancion.id_torneo, sancion.numero_fecha_inicio, ultima_fecha),
    )
    conflicto = cursor.fetchone()
    if conflicto:
        return (f"El jugador ya figura en la planilla de la fecha {conflicto['numero_fecha']}, "
                f"que queda dentro de la sanción")
    return None


@router.get("/sanciones")
def listar_sanciones(id_torneo: Optional[int] = None, rol: str = Depends(solo_administrador)):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        sql = (
            "SELECT s.id_sancion, s.ci_jugador, j.nombre, j.apellido, s.id_torneo, t.nombre AS torneo, "
            "e.nombre AS equipo, s.motivo, s.numero_fecha_inicio, s.cantidad_fechas, "
            "s.numero_fecha_inicio + s.cantidad_fechas - 1 AS numero_fecha_fin, s.id_tarjeta_origen "
            "FROM sancion_jugador s "
            "JOIN jugador j ON j.ci = s.ci_jugador "
            "JOIN torneo t ON t.id_torneo = s.id_torneo "
            "LEFT JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = s.ci_jugador AND ejt.id_torneo = s.id_torneo "
            "LEFT JOIN equipo e ON e.id_equipo = ejt.id_equipo"
        )
        valores = ()
        if id_torneo is not None:
            sql += " WHERE s.id_torneo = %s"
            valores = (id_torneo,)
        sql += " ORDER BY s.id_torneo, s.numero_fecha_inicio, j.apellido"
        cursor.execute(sql, valores)
        sanciones = cursor.fetchall()

        cursor.close()
        conexion.close()
        return sanciones

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.get("/sanciones/jugadores")
def jugadores_sancionables(id_torneo: int, rol: str = Depends(solo_administrador)):
    # Jugadores inscriptos en algún equipo de la edición, para el formulario de sanciones
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT j.ci, j.nombre, j.apellido, e.nombre AS equipo "
            "FROM equipo_jugador_torneo ejt "
            "JOIN jugador j ON j.ci = ejt.ci_jugador "
            "JOIN equipo e ON e.id_equipo = ejt.id_equipo "
            "WHERE ejt.id_torneo = %s ORDER BY e.nombre, j.apellido",
            (id_torneo,),
        )
        jugadores = cursor.fetchall()
        cursor.close()
        conexion.close()
        return jugadores

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.post("/sanciones")
def crear_sancion(sancion: SancionNueva, rol: str = Depends(solo_administrador)):
    # Por el ABM solo se cargan sanciones disciplinarias; las de roja y amarillas son automáticas
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        error = validar_sancion(cursor, sancion)
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        cursor.execute(
            "INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas) "
            "VALUES (%s, %s, 'disciplinaria', %s, %s)",
            (sancion.ci_jugador, sancion.id_torneo, sancion.numero_fecha_inicio, sancion.cantidad_fechas),
        )
        conexion.commit()
        id_sancion = cursor.lastrowid

        cursor.close()
        conexion.close()
        return {"mensaje": "Sanción disciplinaria dada de alta", "id_sancion": id_sancion}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.put("/sanciones/{id_sancion}")
def modificar_sancion(id_sancion: int, sancion: SancionNueva, rol: str = Depends(solo_administrador)):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("SELECT motivo FROM sancion_jugador WHERE id_sancion = %s", (id_sancion,))
        actual = cursor.fetchone()
        if not actual:
            error = "No existe ninguna sanción con ese ID"
        elif actual["motivo"] != "disciplinaria":
            error = "Las sanciones automáticas se corrigen eliminando o cargando tarjetas en la planilla"
        else:
            error = validar_sancion(cursor, sancion)
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        cursor.execute(
            "UPDATE sancion_jugador SET ci_jugador=%s, id_torneo=%s, numero_fecha_inicio=%s, cantidad_fechas=%s "
            "WHERE id_sancion=%s",
            (sancion.ci_jugador, sancion.id_torneo, sancion.numero_fecha_inicio, sancion.cantidad_fechas, id_sancion),
        )
        conexion.commit()

        cursor.close()
        conexion.close()
        return {"mensaje": "Sanción modificada con éxito"}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.delete("/sanciones/{id_sancion}")
def eliminar_sancion(id_sancion: int, rol: str = Depends(solo_administrador)):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("SELECT motivo FROM sancion_jugador WHERE id_sancion = %s", (id_sancion,))
        actual = cursor.fetchone()
        if not actual:
            error = "No existe ninguna sanción con ese ID para borrar"
        elif actual["motivo"] != "disciplinaria":
            error = "Las sanciones automáticas se corrigen eliminando o cargando tarjetas en la planilla"
        else:
            error = None
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        cursor.execute("DELETE FROM sancion_jugador WHERE id_sancion = %s", (id_sancion,))
        conexion.commit()

        cursor.close()
        conexion.close()
        return {"mensaje": "Sanción eliminada con éxito"}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}
