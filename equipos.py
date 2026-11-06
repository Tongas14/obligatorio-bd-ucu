from typing import List, Optional
import mysql.connector
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from comun import conectar_bd, requiere_rol, mensaje_error_bd

router = APIRouter()

solo_administrador = requiere_rol("administrador")


class JugadorPlantel(BaseModel):
    ci: str
    numero_camiseta: int


class EquipoNuevo(BaseModel):
    nombre: str
    id_torneo: int
    id_facultad: int
    ci_capitan: str
    jugadores: List[JugadorPlantel]


def validar_equipo(cursor, equipo: EquipoNuevo, id_equipo: int = 0) -> Optional[str]:
    if not equipo.nombre.strip() or len(equipo.nombre) > 100:
        return "El nombre es obligatorio y admite hasta 100 caracteres"
    if not 5 <= len(equipo.jugadores) <= 10:
        return "El plantel debe tener entre 5 y 10 jugadores"

    cis = [j.ci for j in equipo.jugadores]
    camisetas = [j.numero_camiseta for j in equipo.jugadores]
    if len(set(cis)) != len(cis):
        return "Hay jugadores repetidos en el plantel"
    if len(set(camisetas)) != len(camisetas):
        return "Hay números de camiseta repetidos"
    if any(not 1 <= n <= 99 for n in camisetas):
        return "Los números de camiseta van del 1 al 99"
    if equipo.ci_capitan not in cis:
        return "El capitán tiene que ser uno de los jugadores del plantel"

    cursor.execute("SELECT estado FROM torneo WHERE id_torneo = %s", (equipo.id_torneo,))
    torneo = cursor.fetchone()
    if not torneo:
        return "El torneo no existe"
    if torneo["estado"] != "inscripción":
        return "El plantel solo se puede modificar en etapa de inscripción"

    cursor.execute("SELECT 1 FROM facultad WHERE id_facultad = %s", (equipo.id_facultad,))
    if not cursor.fetchone():
        return "La facultad no existe"

    docentes_o_funcionarios = 0
    for ci in cis:
        cursor.execute("SELECT id_facultad, tipo FROM jugador WHERE ci = %s", (ci,))
        jugador = cursor.fetchone()
        if not jugador:
            return f"El jugador con CI {ci} no existe"
        if jugador["id_facultad"] != equipo.id_facultad:
            return f"El jugador {ci} no pertenece a la facultad del equipo"
        if jugador["tipo"] in ("docente", "funcionario"):
            docentes_o_funcionarios += 1

        cursor.execute(
            "SELECT e.nombre FROM equipo_jugador_torneo ejt JOIN equipo e ON e.id_equipo = ejt.id_equipo "
            "WHERE ejt.ci_jugador = %s AND ejt.id_torneo = %s AND ejt.id_equipo <> %s",
            (ci, equipo.id_torneo, id_equipo),
        )
        otro = cursor.fetchone()
        if otro:
            return f"El jugador {ci} ya integra el equipo {otro['nombre']} en esta edición"

    if docentes_o_funcionarios > 2:
        return "El plantel admite como máximo 2 docentes o funcionarios"
    return None


def guardar_plantel(cursor, id_equipo: int, equipo: EquipoNuevo):
    cursor.execute("DELETE FROM equipo_jugador_torneo WHERE id_equipo = %s", (id_equipo,))
    for j in equipo.jugadores:
        cursor.execute(
            "INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES (%s, %s, %s, %s)",
            (id_equipo, j.ci, equipo.id_torneo, j.numero_camiseta),
        )


@router.get("/equipos")
def listar_equipos(id_torneo: Optional[int] = None, rol: str = Depends(solo_administrador)):
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        filtro = " WHERE e.id_torneo = %s" if id_torneo is not None else ""
        valores = (id_torneo,) if id_torneo is not None else ()
        cursor.execute(
            "SELECT e.id_equipo, e.nombre, e.id_torneo, t.nombre AS torneo, t.estado AS estado_torneo, "
            "e.id_facultad, f.nombre AS facultad, e.ci_capitan, CONCAT(c.nombre, ' ', c.apellido) AS capitan "
            "FROM equipo e JOIN torneo t ON t.id_torneo = e.id_torneo "
            "JOIN facultad f ON f.id_facultad = e.id_facultad JOIN jugador c ON c.ci = e.ci_capitan"
            + filtro + " ORDER BY t.año DESC, t.semestre DESC, e.nombre",
            valores,
        )
        equipos = cursor.fetchall()

        cursor.execute(
            "SELECT ejt.id_equipo, j.ci, j.nombre, j.apellido, j.tipo, ejt.numero_camiseta "
            "FROM equipo_jugador_torneo ejt JOIN jugador j ON j.ci = ejt.ci_jugador "
            "JOIN equipo e ON e.id_equipo = ejt.id_equipo"
            + filtro + " ORDER BY ejt.numero_camiseta",
            valores,
        )
        planteles = cursor.fetchall()
        for e in equipos:
            e["jugadores"] = [j for j in planteles if j["id_equipo"] == e["id_equipo"]]

        cursor.close()
        conexion.close()
        return equipos

    except mysql.connector.Error as err:
        return {"error": mensaje_error_bd(err)}


@router.post("/equipos")
def crear_equipo(equipo: EquipoNuevo, rol: str = Depends(solo_administrador)):
    conexion = None
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        error = validar_equipo(cursor, equipo)
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        cursor.execute(
            "INSERT INTO equipo (nombre, id_torneo, id_facultad, ci_capitan) VALUES (%s, %s, %s, %s)",
            (equipo.nombre, equipo.id_torneo, equipo.id_facultad, equipo.ci_capitan),
        )
        id_equipo = cursor.lastrowid
        guardar_plantel(cursor, id_equipo, equipo)
        conexion.commit()

        cursor.close()
        conexion.close()
        return {"mensaje": f"Equipo {equipo.nombre} inscripto con {len(equipo.jugadores)} jugadores", "id_equipo": id_equipo}

    except mysql.connector.Error as err:
        if conexion:
            conexion.rollback()
        return {"error": mensaje_error_bd(err)}


@router.put("/equipos/{id_equipo}")
def modificar_equipo(id_equipo: int, equipo: EquipoNuevo, rol: str = Depends(solo_administrador)):
    conexion = None
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("SELECT id_torneo FROM equipo WHERE id_equipo = %s", (id_equipo,))
        actual = cursor.fetchone()
        if not actual:
            error = "No existe ningún equipo con ese ID"
        elif actual["id_torneo"] != equipo.id_torneo:
            error = "No se puede cambiar el torneo de un equipo"
        else:
            error = validar_equipo(cursor, equipo, id_equipo)
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        cursor.execute(
            "UPDATE equipo SET nombre=%s, id_facultad=%s, ci_capitan=%s WHERE id_equipo=%s",
            (equipo.nombre, equipo.id_facultad, equipo.ci_capitan, id_equipo),
        )
        guardar_plantel(cursor, id_equipo, equipo)
        conexion.commit()

        cursor.close()
        conexion.close()
        return {"mensaje": "Equipo modificado con éxito"}

    except mysql.connector.Error as err:
        if conexion:
            conexion.rollback()
        return {"error": mensaje_error_bd(err)}


@router.delete("/equipos/{id_equipo}")
def eliminar_equipo(id_equipo: int, rol: str = Depends(solo_administrador)):
    conexion = None
    try:
        conexion = conectar_bd(rol)
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            "SELECT t.estado FROM equipo e JOIN torneo t ON t.id_torneo = e.id_torneo WHERE e.id_equipo = %s",
            (id_equipo,),
        )
        equipo = cursor.fetchone()
        if not equipo:
            error = "No existe ningún equipo con ese ID"
        elif equipo["estado"] != "inscripción":
            error = "Solo se pueden eliminar equipos en etapa de inscripción"
        else:
            error = None
        if error:
            cursor.close()
            conexion.close()
            return {"error": error}

        cursor.execute("DELETE FROM equipo_jugador_torneo WHERE id_equipo = %s", (id_equipo,))
        cursor.execute("DELETE FROM equipo WHERE id_equipo = %s", (id_equipo,))
        conexion.commit()

        cursor.close()
        conexion.close()
        return {"mensaje": "Equipo eliminado con éxito"}

    except mysql.connector.Error as err:
        if conexion:
            conexion.rollback()
        return {"error": mensaje_error_bd(err)}
