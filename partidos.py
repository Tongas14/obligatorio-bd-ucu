from datetime import date, datetime, timedelta
from typing import Optional
import mysql.connector
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from comun import conectar_bd, ahora_bd, requiere_rol, mensaje_error_bd

router = APIRouter()

ESTADOS_PARTIDO = ["programado", "jugado", "postergado", "cancelado"]

# Goles de cada equipo: un gol normal suma al equipo del jugador, un autogol suma al rival
SQL_RESULTADOS = """
    SELECT g.id_partido,
           SUM(CASE WHEN (pp.id_equipo = p.id_equipo_local AND NOT g.autogol)
                      OR (pp.id_equipo = p.id_equipo_visitante AND g.autogol) THEN 1 ELSE 0 END) AS goles_local,
           SUM(CASE WHEN (pp.id_equipo = p.id_equipo_visitante AND NOT g.autogol)
                      OR (pp.id_equipo = p.id_equipo_local AND g.autogol) THEN 1 ELSE 0 END) AS goles_visitante
    FROM gol g
    JOIN partido p ON p.id_partido = g.id_partido
    JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
    GROUP BY g.id_partido
"""

SQL_LISTADO_PARTIDOS = f"""
    SELECT p.id_partido, p.id_torneo, t.nombre AS torneo, p.numero_fecha,
           p.id_equipo_local, el.nombre AS equipo_local,
           p.id_equipo_visitante, ev.nombre AS equipo_visitante,
           p.dia, p.id_turno,
           LEFT(tu.hora_inicio, 5) AS hora_inicio, LEFT(tu.hora_fin, 5) AS hora_fin,
           p.nombre_cancha, p.id_complejo, c.nombre AS complejo, p.estado,
           TIMESTAMP(p.dia, tu.hora_fin) AS fin_partido,
           COALESCE(r.goles_local, 0) AS goles_local,
           COALESCE(r.goles_visitante, 0) AS goles_visitante
    FROM partido p
    JOIN torneo t ON t.id_torneo = p.id_torneo
    JOIN equipo el ON el.id_equipo = p.id_equipo_local
    JOIN equipo ev ON ev.id_equipo = p.id_equipo_visitante
    JOIN turno tu ON tu.id_turno = p.id_turno
    JOIN complejo c ON c.id_complejo = p.id_complejo
    LEFT JOIN ({SQL_RESULTADOS}) r ON r.id_partido = p.id_partido
"""


class PartidoNuevo(BaseModel):
    id_torneo: int
    numero_fecha: int
    id_equipo_local: int
    id_equipo_visitante: int
    dia: date
    id_turno: int
    nombre_cancha: str
    id_complejo: int
    estado: str = "programado"


def formatear_partido(fila: dict, ahora: datetime) -> dict:
    fin = fila.pop("fin_partido")
    # La planilla se carga si ya se disputó, no está cancelado/postergado y no pasaron 48 h de jugado
    fila["planilla_editable"] = (
        fin <= ahora
        and fila["estado"] in ("programado", "jugado")
        and not (fila["estado"] == "jugado" and ahora > fin + timedelta(hours=48))
    )
    return fila


def fin_del_partido(cursor, dia: date, id_turno: int) -> Optional[datetime]:
    cursor.execute("SELECT hora_fin FROM turno WHERE id_turno = %s", (id_turno,))
    turno = cursor.fetchone()
    if not turno:
        return None
    return datetime.combine(dia, datetime.min.time()) + turno["hora_fin"]


def validar_partido(cursor, partido: PartidoNuevo, id_partido: int = 0) -> Optional[str]:
    if partido.estado not in ESTADOS_PARTIDO:
        return "El estado solo puede ser: programado, jugado, postergado o cancelado"
    if partido.numero_fecha < 1:
        return "El número de fecha debe ser 1 o mayor"
    if partido.id_equipo_local == partido.id_equipo_visitante:
        return "Un equipo no puede enfrentarse a sí mismo"

    cursor.execute("SELECT estado FROM torneo WHERE id_torneo = %s", (partido.id_torneo,))
    torneo = cursor.fetchone()
    if not torneo:
        return "El torneo no existe"
    if id_partido == 0 and torneo["estado"] == "finalizado":
        return "No se pueden programar partidos en un torneo finalizado"

    for id_equipo in (partido.id_equipo_local, partido.id_equipo_visitante):
        cursor.execute(
            "SELECT e.nombre, e.id_torneo, COUNT(ejt.ci_jugador) AS cantidad "
            "FROM equipo e LEFT JOIN equipo_jugador_torneo ejt ON ejt.id_equipo = e.id_equipo "
            "WHERE e.id_equipo = %s GROUP BY e.id_equipo",
            (id_equipo,),
        )
        equipo = cursor.fetchone()
        if not equipo:
            return f"El equipo {id_equipo} no existe"
        if equipo["id_torneo"] != partido.id_torneo:
            return f"El equipo {equipo['nombre']} no pertenece a esta edición del torneo"
        if equipo["cantidad"] < 5:
            return f"El equipo {equipo['nombre']} tiene menos de 5 jugadores en su plantel"

    cursor.execute(
        "SELECT 1 FROM cancha WHERE nombre_cancha = %s AND id_complejo = %s",
        (partido.nombre_cancha, partido.id_complejo),
    )
    if not cursor.fetchone():
        return "La cancha no existe en ese complejo"

    fin = fin_del_partido(cursor, partido.dia, partido.id_turno)
    if fin is None:
        return "El turno no existe"

    if partido.estado != "cancelado":
        cursor.execute(
            "SELECT id_partido FROM partido "
            "WHERE id_torneo = %s AND id_partido <> %s AND estado <> 'cancelado' "
            "AND ((id_equipo_local = %s AND id_equipo_visitante = %s) "
            "  OR (id_equipo_local = %s AND id_equipo_visitante = %s))",
            (partido.id_torneo, id_partido, partido.id_equipo_local, partido.id_equipo_visitante,
             partido.id_equipo_visitante, partido.id_equipo_local),
        )
        if cursor.fetchone():
            return "Estos equipos ya tienen un partido no cancelado en esta edición"

        cursor.execute(
            "SELECT id_partido FROM partido "
            "WHERE id_torneo = %s AND numero_fecha = %s AND id_partido <> %s AND estado <> 'cancelado' "
            "AND (id_equipo_local IN (%s, %s) OR id_equipo_visitante IN (%s, %s))",
            (partido.id_torneo, partido.numero_fecha, id_partido,
             partido.id_equipo_local, partido.id_equipo_visitante,
             partido.id_equipo_local, partido.id_equipo_visitante),
        )
        if cursor.fetchone():
            return "Uno de los equipos ya tiene un partido en esa fecha del torneo"

    if partido.estado not in ("cancelado", "postergado"):
        cursor.execute(
            "SELECT id_partido FROM partido "
            "WHERE nombre_cancha = %s AND id_complejo = %s AND dia = %s AND id_turno = %s "
            "AND id_partido <> %s AND estado NOT IN ('cancelado', 'postergado')",
            (partido.nombre_cancha, partido.id_complejo, partido.dia, partido.id_turno, id_partido),
        )
        if cursor.fetchone():
            return "La cancha ya tiene un partido asignado en ese día y turno"

    if partido.estado == "jugado" and fin > ahora_bd(cursor):
        return "Un partido solo puede marcarse como jugado si su día y turno ya pasaron"

    return None


@router.get("/partidos")
def listar_partidos(id_torneo: Optional[int] = None, rol: str = Depends(requiere_rol("administrador"))):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)
        ahora = ahora_bd(cursor)

        sql = SQL_LISTADO_PARTIDOS
        valores = ()
        if id_torneo is not None:
            sql += " WHERE p.id_torneo = %s"
            valores = (id_torneo,)
        sql += " ORDER BY p.id_torneo, p.numero_fecha, p.dia, tu.hora_inicio"
        cursor.execute(sql, valores)
        partidos = [formatear_partido(fila, ahora) for fila in cursor.fetchall()]

        cursor.close()
        conexion.close()
        return partidos

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.get("/partidos/opciones")
def opciones_partido(rol: str = Depends(requiere_rol("administrador"))):
    # Datos para armar los desplegables del formulario de partidos
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("SELECT id_torneo, nombre, año AS anio, semestre, estado FROM torneo ORDER BY año DESC, semestre DESC")
        torneos = cursor.fetchall()

        cursor.execute(
            "SELECT e.id_equipo, e.nombre, e.id_torneo, COUNT(ejt.ci_jugador) AS cantidad_jugadores "
            "FROM equipo e LEFT JOIN equipo_jugador_torneo ejt ON ejt.id_equipo = e.id_equipo "
            "GROUP BY e.id_equipo ORDER BY e.nombre"
        )
        equipos = cursor.fetchall()

        cursor.execute(
            "SELECT ca.nombre_cancha, ca.id_complejo, co.nombre AS complejo "
            "FROM cancha ca JOIN complejo co ON co.id_complejo = ca.id_complejo "
            "ORDER BY co.nombre, ca.nombre_cancha"
        )
        canchas = cursor.fetchall()

        cursor.execute(
            "SELECT id_turno, LEFT(hora_inicio, 5) AS hora_inicio, LEFT(hora_fin, 5) AS hora_fin "
            "FROM turno ORDER BY hora_inicio"
        )
        turnos = cursor.fetchall()

        cursor.close()
        conexion.close()
        return {"torneos": torneos, "equipos": equipos, "canchas": canchas, "turnos": turnos, "estados": ESTADOS_PARTIDO}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.get("/partidos/{id_partido}")
def obtener_partido(id_partido: int, rol: str = Depends(requiere_rol("administrador"))):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)
        ahora = ahora_bd(cursor)
        cursor.execute(SQL_LISTADO_PARTIDOS + " WHERE p.id_partido = %s", (id_partido,))
        fila = cursor.fetchone()
        cursor.close()
        conexion.close()

        if not fila:
            return {"error": "No existe ningún partido con ese ID"}
        return formatear_partido(fila, ahora)

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.post("/partidos")
def crear_partido(partido: PartidoNuevo, rol: str = Depends(requiere_rol("administrador"))):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        error = validar_partido(cursor, partido)
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        sql = (
            "INSERT INTO partido (id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante, "
            "dia, id_turno, nombre_cancha, id_complejo, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        valores = (partido.id_torneo, partido.numero_fecha, partido.id_equipo_local, partido.id_equipo_visitante,
                   partido.dia, partido.id_turno, partido.nombre_cancha, partido.id_complejo, partido.estado)
        cursor.execute(sql, valores)
        conexion.commit()
        id_nuevo = cursor.lastrowid

        cursor.close()
        conexion.close()
        return {"mensaje": "Partido dado de alta", "id_partido": id_nuevo}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.put("/partidos/{id_partido}")
def modificar_partido(id_partido: int, partido: PartidoNuevo, rol: str = Depends(requiere_rol("administrador"))):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            "SELECT p.*, TIMESTAMP(p.dia, t.hora_fin) AS fin_partido, "
            "EXISTS (SELECT 1 FROM planilla_partido pp WHERE pp.id_partido = p.id_partido) AS tiene_planilla "
            "FROM partido p JOIN turno t ON t.id_turno = p.id_turno WHERE p.id_partido = %s",
            (id_partido,),
        )
        actual = cursor.fetchone()
        error = None
        if not actual:
            error = "No existe ningún partido con ese ID"
        elif actual["estado"] == "jugado" and ahora_bd(cursor) > actual["fin_partido"] + timedelta(hours=48):
            error = "Pasaron más de 48 horas desde el partido, ya no se puede modificar"
        elif actual["tiene_planilla"] and (
            actual["id_torneo"] != partido.id_torneo
            or actual["id_equipo_local"] != partido.id_equipo_local
            or actual["id_equipo_visitante"] != partido.id_equipo_visitante
        ):
            error = "No se pueden cambiar los equipos de un partido con planilla cargada"
        elif actual["tiene_planilla"] and partido.estado in ("cancelado", "postergado"):
            error = "No se puede cancelar ni postergar un partido con planilla cargada"
        else:
            error = validar_partido(cursor, partido, id_partido)

        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        sql = (
            "UPDATE partido SET id_torneo=%s, numero_fecha=%s, id_equipo_local=%s, id_equipo_visitante=%s, "
            "dia=%s, id_turno=%s, nombre_cancha=%s, id_complejo=%s, estado=%s WHERE id_partido=%s"
        )
        valores = (partido.id_torneo, partido.numero_fecha, partido.id_equipo_local, partido.id_equipo_visitante,
                   partido.dia, partido.id_turno, partido.nombre_cancha, partido.id_complejo, partido.estado,
                   id_partido)
        cursor.execute(sql, valores)
        conexion.commit()

        cursor.close()
        conexion.close()
        return {"mensaje": "Partido modificado con éxito"}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.delete("/partidos/{id_partido}")
def eliminar_partido(id_partido: int, rol: str = Depends(requiere_rol("administrador"))):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("SELECT estado FROM partido WHERE id_partido = %s", (id_partido,))
        partido = cursor.fetchone()
        if not partido:
            cursor.close()
            conexion.close()
            return {"error": "No existe ningún partido con ese ID para borrar"}
        if partido["estado"] == "jugado":
            cursor.close()
            conexion.close()
            return {"error": "Un partido jugado no se puede eliminar"}

        # Un partido programado puede tener planilla cargada sin haberse cerrado; se borra en orden
        # (al borrar las tarjetas el trigger elimina las sanciones automáticas que generaron)
        cursor.execute("DELETE FROM tarjeta WHERE id_partido = %s", (id_partido,))
        cursor.execute("DELETE FROM gol WHERE id_partido = %s", (id_partido,))
        cursor.execute("DELETE FROM planilla_partido WHERE id_partido = %s", (id_partido,))
        cursor.execute("DELETE FROM partido WHERE id_partido = %s", (id_partido,))
        conexion.commit()

        cursor.close()
        conexion.close()
        return {"mensaje": "Partido eliminado con éxito"}

    except mysql.connector.Error as err:
        conexion.rollback()
        return {"error": mensaje_error_bd(err)}
