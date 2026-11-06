from datetime import timedelta
from typing import List, Optional
import mysql.connector
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from comun import conectar_bd, ahora_bd, requiere_rol, mensaje_error_bd
from partidos import SQL_LISTADO_PARTIDOS, formatear_partido

router = APIRouter()

puede_cargar_planillas = requiere_rol("administrador", "planillero")

MINUTO_MAXIMO = 60


class JugadorPlanilla(BaseModel):
    ci: str
    id_equipo: int


class PlanillaNueva(BaseModel):
    jugadores: List[JugadorPlanilla]


class GolNuevo(BaseModel):
    ci_jugador: str
    minuto: int
    autogol: bool = False


class TarjetaNueva(BaseModel):
    ci_jugador: str
    minuto: int
    color: str


def validar_carga_partido(cursor, id_partido: int):
    # Devuelve (partido, error)
    cursor.execute(
        "SELECT p.*, TIMESTAMP(p.dia, t.hora_fin) AS fin_partido "
        "FROM partido p JOIN turno t ON t.id_turno = p.id_turno WHERE p.id_partido = %s",
        (id_partido,),
    )
    partido = cursor.fetchone()
    if not partido:
        return None, "El partido no existe"
    if partido["estado"] in ("cancelado", "postergado"):
        return partido, "No se puede cargar la planilla de un partido cancelado o postergado"
    ahora = ahora_bd(cursor)
    if partido["fin_partido"] > ahora:
        return partido, "El partido todavía no se disputó"
    if partido["estado"] == "jugado" and ahora > partido["fin_partido"] + timedelta(hours=48):
        return partido, "Pasaron más de 48 horas desde el partido, ya no se puede corregir"
    return partido, None


def jugador_suspendido(cursor, ci: str, id_torneo: int, numero_fecha: int) -> bool:
    cursor.execute(
        "SELECT 1 FROM sancion_jugador WHERE ci_jugador = %s AND id_torneo = %s "
        "AND %s BETWEEN numero_fecha_inicio AND numero_fecha_inicio + cantidad_fechas - 1",
        (ci, id_torneo, numero_fecha),
    )
    return cursor.fetchone() is not None


def jugador_en_planilla(cursor, id_partido: int, ci: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM planilla_partido WHERE id_partido = %s AND ci_jugador = %s",
        (id_partido, ci),
    )
    return cursor.fetchone() is not None


def validar_minuto(minuto: int) -> Optional[str]:
    if minuto < 0 or minuto > MINUTO_MAXIMO:
        return f"El minuto debe estar entre 0 y {MINUTO_MAXIMO}"
    return None


@router.get("/planillas/partidos")
def partidos_para_planilla(rol: str = Depends(puede_cargar_planillas)):
    # Partidos ya disputados que no están cancelados ni postergados
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)
        ahora = ahora_bd(cursor)
        cursor.execute(
            SQL_LISTADO_PARTIDOS
            + " WHERE p.estado IN ('programado', 'jugado') AND TIMESTAMP(p.dia, tu.hora_fin) <= NOW()"
            + " ORDER BY p.dia DESC, tu.hora_inicio DESC"
        )
        partidos = [formatear_partido(fila, ahora) for fila in cursor.fetchall()]
        cursor.close()
        conexion.close()
        return partidos

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.get("/planillas/{id_partido}")
def obtener_planilla(id_partido: int, rol: str = Depends(puede_cargar_planillas)):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)
        ahora = ahora_bd(cursor)

        cursor.execute(SQL_LISTADO_PARTIDOS + " WHERE p.id_partido = %s", (id_partido,))
        fila = cursor.fetchone()
        if not fila:
            cursor.close()
            conexion.close()
            return {"error": "El partido no existe"}
        partido = formatear_partido(fila, ahora)

        equipos = []
        for id_equipo, nombre in ((partido["id_equipo_local"], partido["equipo_local"]),
                                  (partido["id_equipo_visitante"], partido["equipo_visitante"])):
            cursor.execute(
                "SELECT j.ci, j.nombre, j.apellido, j.tipo, ejt.numero_camiseta, "
                "EXISTS (SELECT 1 FROM planilla_partido pp WHERE pp.id_partido = %s AND pp.ci_jugador = j.ci) AS en_planilla, "
                "EXISTS (SELECT 1 FROM sancion_jugador s WHERE s.ci_jugador = j.ci AND s.id_torneo = %s "
                "        AND %s BETWEEN s.numero_fecha_inicio AND s.numero_fecha_inicio + s.cantidad_fechas - 1) AS suspendido "
                "FROM equipo_jugador_torneo ejt JOIN jugador j ON j.ci = ejt.ci_jugador "
                "WHERE ejt.id_equipo = %s ORDER BY ejt.numero_camiseta, j.apellido",
                (id_partido, partido["id_torneo"], partido["numero_fecha"], id_equipo),
            )
            equipos.append({"id_equipo": id_equipo, "nombre": nombre, "jugadores": cursor.fetchall()})

        cursor.execute(
            "SELECT g.id_gol, g.ci_jugador, j.nombre, j.apellido, g.minuto, g.autogol, pp.id_equipo "
            "FROM gol g JOIN jugador j ON j.ci = g.ci_jugador "
            "JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador "
            "WHERE g.id_partido = %s ORDER BY g.minuto",
            (id_partido,),
        )
        goles = cursor.fetchall()

        cursor.execute(
            "SELECT t.id_tarjeta, t.ci_jugador, j.nombre, j.apellido, t.minuto, t.color, pp.id_equipo "
            "FROM tarjeta t JOIN jugador j ON j.ci = t.ci_jugador "
            "JOIN planilla_partido pp ON pp.id_partido = t.id_partido AND pp.ci_jugador = t.ci_jugador "
            "WHERE t.id_partido = %s ORDER BY t.minuto",
            (id_partido,),
        )
        tarjetas = cursor.fetchall()

        cursor.close()
        conexion.close()
        return {"partido": partido, "equipos": equipos, "goles": goles, "tarjetas": tarjetas}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.put("/planillas/{id_partido}")
def guardar_planilla(id_partido: int, planilla: PlanillaNueva, rol: str = Depends(puede_cargar_planillas)):
    # Reemplaza la planilla por la lista recibida y marca el partido como jugado
    conexion = None
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        partido, error = validar_carga_partido(cursor, id_partido)
        if not error and not planilla.jugadores:
            error = "La planilla debe tener al menos un jugador"

        cis = [j.ci for j in planilla.jugadores]
        if not error and len(cis) != len(set(cis)):
            error = "Hay jugadores repetidos en la planilla"

        if not error:
            for j in planilla.jugadores:
                if j.id_equipo not in (partido["id_equipo_local"], partido["id_equipo_visitante"]):
                    error = f"El equipo {j.id_equipo} no juega este partido"
                    break
                cursor.execute(
                    "SELECT 1 FROM equipo_jugador_torneo WHERE id_equipo = %s AND ci_jugador = %s",
                    (j.id_equipo, j.ci),
                )
                if not cursor.fetchone():
                    error = f"El jugador {j.ci} no pertenece al plantel de ninguno de los dos equipos"
                    break
                if jugador_suspendido(cursor, j.ci, partido["id_torneo"], partido["numero_fecha"]):
                    error = f"El jugador {j.ci} está suspendido para esta fecha"
                    break

        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        cursor.execute("SELECT ci_jugador, id_equipo FROM planilla_partido WHERE id_partido = %s", (id_partido,))
        actuales = {f["ci_jugador"]: f["id_equipo"] for f in cursor.fetchall()}
        nuevos = {j.ci: j.id_equipo for j in planilla.jugadores}

        for ci in actuales:
            if ci not in nuevos:
                cursor.execute(
                    "SELECT (SELECT COUNT(*) FROM gol WHERE id_partido = %s AND ci_jugador = %s) "
                    "     + (SELECT COUNT(*) FROM tarjeta WHERE id_partido = %s AND ci_jugador = %s) AS eventos",
                    (id_partido, ci, id_partido, ci),
                )
                if cursor.fetchone()["eventos"] > 0:
                    cursor.close()
                    conexion.close()
                    return {"error": f"El jugador {ci} tiene goles o tarjetas en el partido, elimínelos primero"}
                cursor.execute("DELETE FROM planilla_partido WHERE id_partido = %s AND ci_jugador = %s", (id_partido, ci))

        for ci, id_equipo in nuevos.items():
            if ci not in actuales:
                cursor.execute(
                    "INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (%s, %s, %s)",
                    (id_partido, ci, id_equipo),
                )

        if partido["estado"] == "programado":
            cursor.execute("UPDATE partido SET estado = 'jugado' WHERE id_partido = %s", (id_partido,))

        conexion.commit()
        cursor.close()
        conexion.close()
        return {"mensaje": f"Planilla guardada con {len(nuevos)} jugadores"}

    except mysql.connector.Error as err:
        if conexion:
            conexion.rollback()
        return {"error": mensaje_error_bd(err)}


@router.post("/planillas/{id_partido}/goles")
def registrar_gol(id_partido: int, gol: GolNuevo, rol: str = Depends(puede_cargar_planillas)):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        partido, error = validar_carga_partido(cursor, id_partido)
        if not error:
            error = validar_minuto(gol.minuto)
        if not error and not jugador_en_planilla(cursor, id_partido, gol.ci_jugador):
            error = "Solo pueden convertir goles los jugadores que figuran en la planilla"
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        cursor.execute(
            "INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (%s, %s, %s, %s)",
            (id_partido, gol.ci_jugador, gol.minuto, gol.autogol),
        )
        conexion.commit()
        id_gol = cursor.lastrowid

        cursor.close()
        conexion.close()
        return {"mensaje": "Autogol registrado" if gol.autogol else "Gol registrado", "id_gol": id_gol}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.delete("/planillas/{id_partido}/goles/{id_gol}")
def eliminar_gol(id_partido: int, id_gol: int, rol: str = Depends(puede_cargar_planillas)):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        partido, error = validar_carga_partido(cursor, id_partido)
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        cursor.execute("DELETE FROM gol WHERE id_gol = %s AND id_partido = %s", (id_gol, id_partido))
        conexion.commit()
        filas = cursor.rowcount

        cursor.close()
        conexion.close()
        if filas == 0:
            return {"error": "El gol no existe en este partido"}
        return {"mensaje": "Gol eliminado"}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.post("/planillas/{id_partido}/tarjetas")
def registrar_tarjeta(id_partido: int, tarjeta: TarjetaNueva, rol: str = Depends(puede_cargar_planillas)):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        partido, error = validar_carga_partido(cursor, id_partido)
        if not error and tarjeta.color not in ("amarilla", "roja"):
            error = "El color de la tarjeta solo puede ser amarilla o roja"
        if not error:
            error = validar_minuto(tarjeta.minuto)
        if not error and not jugador_en_planilla(cursor, id_partido, tarjeta.ci_jugador):
            error = "Solo pueden recibir tarjetas los jugadores que figuran en la planilla"
        if not error:
            cursor.execute(
                "SELECT COUNT(*) AS cantidad FROM tarjeta WHERE id_partido = %s AND ci_jugador = %s AND color = %s",
                (id_partido, tarjeta.ci_jugador, tarjeta.color),
            )
            cantidad = cursor.fetchone()["cantidad"]
            if tarjeta.color == "roja" and cantidad >= 1:
                error = "El jugador ya tiene una tarjeta roja en este partido"
            elif tarjeta.color == "amarilla" and cantidad >= 2:
                error = "El jugador ya tiene 2 tarjetas amarillas en este partido"
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        # La sanción automática la genera el trigger trg_tarjeta_ai
        cursor.execute(
            "INSERT INTO tarjeta (id_partido, ci_jugador, minuto, color) VALUES (%s, %s, %s, %s)",
            (id_partido, tarjeta.ci_jugador, tarjeta.minuto, tarjeta.color),
        )
        id_tarjeta = cursor.lastrowid
        conexion.commit()

        cursor.execute(
            "SELECT motivo, numero_fecha_inicio FROM sancion_jugador WHERE id_tarjeta_origen = %s",
            (id_tarjeta,),
        )
        sancion = cursor.fetchone()

        cursor.close()
        conexion.close()

        mensaje = f"Tarjeta {tarjeta.color} registrada"
        if sancion:
            mensaje += (f". Se generó una sanción automática ({sancion['motivo']}): "
                        f"suspendido en la fecha {sancion['numero_fecha_inicio']}")
        return {"mensaje": mensaje, "id_tarjeta": id_tarjeta}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.delete("/planillas/{id_partido}/tarjetas/{id_tarjeta}")
def eliminar_tarjeta(id_partido: int, id_tarjeta: int, rol: str = Depends(puede_cargar_planillas)):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        partido, error = validar_carga_partido(cursor, id_partido)
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        # El trigger trg_tarjeta_bd borra la sanción que había generado
        cursor.execute("DELETE FROM tarjeta WHERE id_tarjeta = %s AND id_partido = %s", (id_tarjeta, id_partido))
        conexion.commit()
        filas = cursor.rowcount

        cursor.close()
        conexion.close()
        if filas == 0:
            return {"error": "La tarjeta no existe en este partido"}
        return {"mensaje": "Tarjeta eliminada"}

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}
