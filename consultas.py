from fastapi import APIRouter, Depends

from comun import consultar, requiere_rol

router = APIRouter()

solo_administrador = requiere_rol("administrador")


@router.get("/consultas/suspendidos")
def suspendidos_por_fecha(id_torneo: int, numero_fecha: int, rol: str = Depends(solo_administrador)):
    # Jugadores que no pueden figurar en ninguna planilla de esa fecha
    sql = """
        SELECT j.ci, j.nombre, j.apellido, e.nombre AS equipo, s.motivo,
               s.numero_fecha_inicio, s.numero_fecha_inicio + s.cantidad_fechas - 1 AS numero_fecha_fin
        FROM sancion_jugador s
        JOIN jugador j ON j.ci = s.ci_jugador
        LEFT JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = s.ci_jugador AND ejt.id_torneo = s.id_torneo
        LEFT JOIN equipo e ON e.id_equipo = ejt.id_equipo
        WHERE s.id_torneo = %s
          AND %s BETWEEN s.numero_fecha_inicio AND s.numero_fecha_inicio + s.cantidad_fechas - 1
        ORDER BY e.nombre, j.apellido
    """
    return consultar(rol, sql, (id_torneo, numero_fecha))


@router.get("/consultas/partidos-mas-tarjetas")
def partidos_mas_tarjetas(id_torneo: int, rol: str = Depends(solo_administrador)):
    # Los 10 partidos con más tarjetas de la edición
    sql = """
        SELECT p.id_partido, p.numero_fecha, p.dia, el.nombre AS equipo_local, ev.nombre AS equipo_visitante,
               SUM(t.color = 'amarilla') AS amarillas,
               SUM(t.color = 'roja') AS rojas,
               COUNT(*) AS total_tarjetas
        FROM tarjeta t
        JOIN partido p ON p.id_partido = t.id_partido
        JOIN equipo el ON el.id_equipo = p.id_equipo_local
        JOIN equipo ev ON ev.id_equipo = p.id_equipo_visitante
        WHERE p.id_torneo = %s
        GROUP BY p.id_partido, p.numero_fecha, p.dia, el.nombre, ev.nombre
        ORDER BY total_tarjetas DESC, rojas DESC
        LIMIT 10
    """
    return consultar(rol, sql, (id_torneo,))


@router.get("/consultas/planillas-pendientes")
def planillas_pendientes(rol: str = Depends(solo_administrador)):
    # Partidos que ya se disputaron pero todavía no tienen planilla cargada
    sql = """
        SELECT p.id_partido, t.nombre AS torneo, p.numero_fecha, p.dia, LEFT(tu.hora_inicio, 5) AS hora_inicio,
               el.nombre AS equipo_local, ev.nombre AS equipo_visitante, p.estado
        FROM partido p
        JOIN torneo t ON t.id_torneo = p.id_torneo
        JOIN turno tu ON tu.id_turno = p.id_turno
        JOIN equipo el ON el.id_equipo = p.id_equipo_local
        JOIN equipo ev ON ev.id_equipo = p.id_equipo_visitante
        WHERE p.estado IN ('programado', 'jugado')
          AND TIMESTAMP(p.dia, tu.hora_fin) <= NOW()
          AND NOT EXISTS (SELECT 1 FROM planilla_partido pp WHERE pp.id_partido = p.id_partido)
        ORDER BY p.dia, tu.hora_inicio
    """
    return consultar(rol, sql)
