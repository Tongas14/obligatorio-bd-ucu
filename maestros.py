import re
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from comun import consultar, modificar, requiere_rol

router = APIRouter()

solo_administrador = requiere_rol("administrador")

TIPOS_JUGADOR = ["grado", "posgrado", "docente", "funcionario"]
ESTADOS_TORNEO = ["inscripción", "en curso", "finalizado"]
SUPERFICIES = ["sintético", "parquet"]


class JugadorNuevo(BaseModel):
    ci: str
    nombre: str
    apellido: str
    email: str
    fecha_nacimiento: date
    id_facultad: int
    tipo: str


class FacultadNueva(BaseModel):
    nombre: str


class TorneoNuevo(BaseModel):
    nombre: str
    año: int
    semestre: int
    fecha_inicio: date
    fecha_fin: date
    estado: str


class ComplejoNuevo(BaseModel):
    nombre: str
    direccion: str
    departamento: str


class CanchaNueva(BaseModel):
    nombre_cancha: str
    id_complejo: int
    superficie: str
    techada: bool


def texto_valido(valor: str, campo: str, largo: int) -> Optional[str]:
    if not valor.strip():
        return f"El campo {campo} es obligatorio"
    if len(valor) > largo:
        return f"El campo {campo} admite hasta {largo} caracteres"
    return None


def validar_jugador(jugador: JugadorNuevo) -> Optional[str]:
    if not re.fullmatch(r"[0-9A-Za-z]{1,15}", jugador.ci):
        return "La CI solo admite letras y números, hasta 15 caracteres"
    error = texto_valido(jugador.nombre, "nombre", 50) or texto_valido(jugador.apellido, "apellido", 50)
    if error:
        return error
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", jugador.email) or len(jugador.email) > 100:
        return "El email no es válido"
    if not date(1900, 1, 1) < jugador.fecha_nacimiento < date.today():
        return "La fecha de nacimiento no es válida"
    if jugador.tipo not in TIPOS_JUGADOR:
        return "El tipo solo puede ser: grado, posgrado, docente o funcionario"
    return None


def validar_torneo(torneo: TorneoNuevo) -> Optional[str]:
    error = texto_valido(torneo.nombre, "nombre", 100)
    if error:
        return error
    if not 2000 <= torneo.año <= 2100:
        return "El año debe estar entre 2000 y 2100"
    if torneo.semestre not in (1, 2):
        return "El semestre solo puede ser 1 o 2"
    if torneo.fecha_fin <= torneo.fecha_inicio:
        return "La fecha de fin debe ser posterior a la de inicio"
    if torneo.estado not in ESTADOS_TORNEO:
        return "El estado solo puede ser: inscripción, en curso o finalizado"
    return None


def validar_complejo(complejo: ComplejoNuevo) -> Optional[str]:
    return (texto_valido(complejo.nombre, "nombre", 100)
            or texto_valido(complejo.direccion, "dirección", 200)
            or texto_valido(complejo.departamento, "departamento", 100))


def validar_cancha(cancha: CanchaNueva) -> Optional[str]:
    error = texto_valido(cancha.nombre_cancha, "nombre", 50)
    if error:
        return error
    if cancha.superficie not in SUPERFICIES:
        return "La superficie solo puede ser sintético o parquet"
    return None


# Jugadores

@router.get("/jugadores")
def listar_jugadores(rol: str = Depends(solo_administrador)):
    return consultar(rol,
        "SELECT j.ci, j.nombre, j.apellido, j.email, j.fecha_nacimiento, j.id_facultad, f.nombre AS facultad, j.tipo "
        "FROM jugador j JOIN facultad f ON f.id_facultad = j.id_facultad ORDER BY j.apellido, j.nombre")


@router.post("/jugadores")
def crear_jugador(jugador: JugadorNuevo, rol: str = Depends(solo_administrador)):
    error = validar_jugador(jugador)
    if error:
        return {"error": error}
    return modificar(rol,
        "INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (jugador.ci, jugador.nombre, jugador.apellido, jugador.email, jugador.fecha_nacimiento,
         jugador.id_facultad, jugador.tipo),
        f"Jugador {jugador.nombre} {jugador.apellido} dado de alta")


@router.put("/jugadores/{ci}")
def modificar_jugador(ci: str, jugador: JugadorNuevo, rol: str = Depends(solo_administrador)):
    jugador.ci = ci
    error = validar_jugador(jugador)
    if error:
        return {"error": error}
    return modificar(rol,
        "UPDATE jugador SET nombre=%s, apellido=%s, email=%s, fecha_nacimiento=%s, id_facultad=%s, tipo=%s WHERE ci=%s",
        (jugador.nombre, jugador.apellido, jugador.email, jugador.fecha_nacimiento, jugador.id_facultad,
         jugador.tipo, ci),
        "Jugador modificado con éxito", "No existe ningún jugador con esa CI")


@router.delete("/jugadores/{ci}")
def eliminar_jugador(ci: str, rol: str = Depends(solo_administrador)):
    return modificar(rol, "DELETE FROM jugador WHERE ci = %s", (ci,),
                     "Jugador eliminado con éxito", "No existe ningún jugador con esa CI")


# Facultades

@router.get("/facultades")
def listar_facultades(rol: str = Depends(solo_administrador)):
    return consultar(rol, "SELECT id_facultad, nombre FROM facultad ORDER BY nombre")


@router.post("/facultades")
def crear_facultad(facultad: FacultadNueva, rol: str = Depends(solo_administrador)):
    error = texto_valido(facultad.nombre, "nombre", 100)
    if error:
        return {"error": error}
    return modificar(rol, "INSERT INTO facultad (nombre) VALUES (%s)", (facultad.nombre,),
                     f"Facultad {facultad.nombre} dada de alta")


@router.put("/facultades/{id_facultad}")
def modificar_facultad(id_facultad: int, facultad: FacultadNueva, rol: str = Depends(solo_administrador)):
    error = texto_valido(facultad.nombre, "nombre", 100)
    if error:
        return {"error": error}
    return modificar(rol, "UPDATE facultad SET nombre = %s WHERE id_facultad = %s", (facultad.nombre, id_facultad),
                     "Facultad modificada con éxito", "Facultad no encontrada")


@router.delete("/facultades/{id_facultad}")
def eliminar_facultad(id_facultad: int, rol: str = Depends(solo_administrador)):
    return modificar(rol, "DELETE FROM facultad WHERE id_facultad = %s", (id_facultad,),
                     "Facultad eliminada con éxito", "Facultad no encontrada")


# Torneos

@router.get("/torneos")
def listar_torneos(rol: str = Depends(solo_administrador)):
    return consultar(rol,
        "SELECT id_torneo, nombre, año AS anio, semestre, fecha_inicio, fecha_fin, estado "
        "FROM torneo ORDER BY año DESC, semestre DESC")


@router.post("/torneos")
def crear_torneo(torneo: TorneoNuevo, rol: str = Depends(solo_administrador)):
    error = validar_torneo(torneo)
    if error:
        return {"error": error}
    return modificar(rol,
        "INSERT INTO torneo (nombre, año, semestre, fecha_inicio, fecha_fin, estado) VALUES (%s, %s, %s, %s, %s, %s)",
        (torneo.nombre, torneo.año, torneo.semestre, torneo.fecha_inicio, torneo.fecha_fin, torneo.estado),
        f"Torneo {torneo.nombre} dado de alta")


@router.put("/torneos/{id_torneo}")
def modificar_torneo(id_torneo: int, torneo: TorneoNuevo, rol: str = Depends(solo_administrador)):
    error = validar_torneo(torneo)
    if error:
        return {"error": error}
    return modificar(rol,
        "UPDATE torneo SET nombre=%s, año=%s, semestre=%s, fecha_inicio=%s, fecha_fin=%s, estado=%s WHERE id_torneo=%s",
        (torneo.nombre, torneo.año, torneo.semestre, torneo.fecha_inicio, torneo.fecha_fin, torneo.estado, id_torneo),
        "Torneo modificado con éxito", "No existe ningún torneo con ese ID")


@router.delete("/torneos/{id_torneo}")
def eliminar_torneo(id_torneo: int, rol: str = Depends(solo_administrador)):
    return modificar(rol, "DELETE FROM torneo WHERE id_torneo = %s", (id_torneo,),
                     "Torneo eliminado con éxito", "No existe ningún torneo con ese ID")


# Complejos

@router.get("/complejos")
def listar_complejos(rol: str = Depends(solo_administrador)):
    return consultar(rol, "SELECT id_complejo, nombre, direccion, departamento FROM complejo ORDER BY nombre")


@router.post("/complejos")
def crear_complejo(complejo: ComplejoNuevo, rol: str = Depends(solo_administrador)):
    error = validar_complejo(complejo)
    if error:
        return {"error": error}
    return modificar(rol, "INSERT INTO complejo (nombre, direccion, departamento) VALUES (%s, %s, %s)",
                     (complejo.nombre, complejo.direccion, complejo.departamento),
                     f"Complejo {complejo.nombre} dado de alta")


@router.put("/complejos/{id_complejo}")
def modificar_complejo(id_complejo: int, complejo: ComplejoNuevo, rol: str = Depends(solo_administrador)):
    error = validar_complejo(complejo)
    if error:
        return {"error": error}
    return modificar(rol, "UPDATE complejo SET nombre=%s, direccion=%s, departamento=%s WHERE id_complejo=%s",
                     (complejo.nombre, complejo.direccion, complejo.departamento, id_complejo),
                     "Complejo modificado con éxito", "Complejo no encontrado")


@router.delete("/complejos/{id_complejo}")
def eliminar_complejo(id_complejo: int, rol: str = Depends(solo_administrador)):
    return modificar(rol, "DELETE FROM complejo WHERE id_complejo = %s", (id_complejo,),
                     "Complejo eliminado con éxito", "Complejo no encontrado")


# Canchas (se identifican por complejo + nombre)

@router.get("/canchas")
def listar_canchas(rol: str = Depends(solo_administrador)):
    return consultar(rol,
        "SELECT ca.nombre_cancha, ca.id_complejo, co.nombre AS complejo, ca.superficie, ca.techada "
        "FROM cancha ca JOIN complejo co ON co.id_complejo = ca.id_complejo ORDER BY co.nombre, ca.nombre_cancha")


@router.post("/canchas")
def crear_cancha(cancha: CanchaNueva, rol: str = Depends(solo_administrador)):
    error = validar_cancha(cancha)
    if error:
        return {"error": error}
    return modificar(rol, "INSERT INTO cancha (nombre_cancha, id_complejo, superficie, techada) VALUES (%s, %s, %s, %s)",
                     (cancha.nombre_cancha, cancha.id_complejo, cancha.superficie, cancha.techada),
                     f"Cancha {cancha.nombre_cancha} dada de alta")


@router.put("/canchas/{id_complejo}/{nombre_cancha}")
def modificar_cancha(id_complejo: int, nombre_cancha: str, cancha: CanchaNueva, rol: str = Depends(solo_administrador)):
    cancha.nombre_cancha = nombre_cancha
    error = validar_cancha(cancha)
    if error:
        return {"error": error}
    return modificar(rol, "UPDATE cancha SET superficie=%s, techada=%s WHERE id_complejo=%s AND nombre_cancha=%s",
                     (cancha.superficie, cancha.techada, id_complejo, nombre_cancha),
                     "Cancha modificada con éxito", "Cancha no encontrada")


@router.delete("/canchas/{id_complejo}/{nombre_cancha}")
def eliminar_cancha(id_complejo: int, nombre_cancha: str, rol: str = Depends(solo_administrador)):
    return modificar(rol, "DELETE FROM cancha WHERE id_complejo = %s AND nombre_cancha = %s", (id_complejo, nombre_cancha),
                     "Cancha eliminada con éxito", "Cancha no encontrada")
