from fastapi import APIRouter, Depends

from comun import consultar, requiere_rol

router = APIRouter()

solo_administrador = requiere_rol("administrador")


# Goles de cada equipo en cada partido jugado de la edición.
# Un gol normal suma al equipo del jugador y un autogol suma al rival.
SQL_RESULTADOS_EDICION = """
    SELECT p.id_partido, p.id_equipo_local, p.id_equipo_visitante,
           SUM(CASE WHEN (pp.id_equipo = p.id_equipo_local AND NOT g.autogol)
                      OR (pp.id_equipo = p.id_equipo_visitante AND g.autogol) THEN 1 ELSE 0 END) AS goles_local,
           SUM(CASE WHEN (pp.id_equipo = p.id_equipo_visitante AND NOT g.autogol)
                      OR (pp.id_equipo = p.id_equipo_local AND g.autogol) THEN 1 ELSE 0 END) AS goles_visitante
    FROM partido p
    LEFT JOIN gol g ON g.id_partido = p.id_partido
    LEFT JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
    WHERE p.id_torneo = %s AND p.estado = 'jugado'
    GROUP BY p.id_partido, p.id_equipo_local, p.id_equipo_visitante
"""


@router.get("/consultas/posiciones")
def tabla_de_posiciones(id_torneo: int, rol: str = Depends(solo_administrador)):
    # 3 puntos por partido ganado, 1 por empate y 0 por derrota.
    # Se ordena por puntos, después por diferencia de goles y después por goles a favor.
    sql = f"""
        SELECT e.id_equipo, e.nombre AS equipo, f.nombre AS facultad,
               COUNT(x.id_equipo) AS pj,
               COALESCE(SUM(x.gf > x.gc), 0) AS pg,
               COALESCE(SUM(x.gf = x.gc), 0) AS pe,
               COALESCE(SUM(x.gf < x.gc), 0) AS pp,
               COALESCE(SUM(x.gf), 0) AS gf,
               COALESCE(SUM(x.gc), 0) AS gc,
               COALESCE(SUM(x.gf - x.gc), 0) AS dg,
               COALESCE(SUM((x.gf > x.gc) * 3 + (x.gf = x.gc)), 0) AS puntos
        FROM equipo e
        JOIN facultad f ON f.id_facultad = e.id_facultad
        LEFT JOIN (
            SELECT r.id_equipo_local AS id_equipo, r.goles_local AS gf, r.goles_visitante AS gc
            FROM ({SQL_RESULTADOS_EDICION}) r
            UNION ALL
            SELECT r.id_equipo_visitante, r.goles_visitante, r.goles_local
            FROM ({SQL_RESULTADOS_EDICION}) r
        ) x ON x.id_equipo = e.id_equipo
        WHERE e.id_torneo = %s
        GROUP BY e.id_equipo, e.nombre, f.nombre
        ORDER BY puntos DESC, dg DESC, gf DESC, e.nombre
    """
    return consultar(rol, sql, (id_torneo, id_torneo, id_torneo))


@router.get("/consultas/goleadores")
def tabla_de_goleadores(id_torneo: int, rol: str = Depends(solo_administrador)):
    # Los 10 jugadores con más goles. Los autogoles no se cuentan para el jugador.
    sql = """
        SELECT j.ci, j.nombre, j.apellido, e.nombre AS equipo, COUNT(*) AS goles
        FROM gol g
        JOIN partido p ON p.id_partido = g.id_partido
        JOIN jugador j ON j.ci = g.ci_jugador
        JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
        JOIN equipo e ON e.id_equipo = pp.id_equipo
        WHERE p.id_torneo = %s AND p.estado = 'jugado' AND NOT g.autogol
        GROUP BY j.ci, j.nombre, j.apellido, e.nombre
        ORDER BY goles DESC, j.apellido, j.nombre
        LIMIT 10
    """
    return consultar(rol, sql, (id_torneo,))


@router.get("/consultas/fair-play")
def tabla_de_fair_play(id_torneo: int, rol: str = Depends(solo_administrador)):
    # 1 punto por amarilla y 3 por roja. El mejor equipo es el de menor puntaje.
    sql = """
        SELECT e.id_equipo, e.nombre AS equipo,
               COALESCE(SUM(t.color = 'amarilla'), 0) AS amarillas,
               COALESCE(SUM(t.color = 'roja'), 0) AS rojas,
               COALESCE(SUM(CASE WHEN t.color = 'amarilla' THEN 1
                                 WHEN t.color = 'roja' THEN 3 ELSE 0 END), 0) AS puntos
        FROM equipo e
        LEFT JOIN planilla_partido pp ON pp.id_equipo = e.id_equipo
        LEFT JOIN tarjeta t ON t.id_partido = pp.id_partido AND t.ci_jugador = pp.ci_jugador
        WHERE e.id_torneo = %s
        GROUP BY e.id_equipo, e.nombre
        ORDER BY puntos, rojas, e.nombre
    """
    return consultar(rol, sql, (id_torneo,))


@router.get("/consultas/promedio-goles")
def promedio_de_goles(id_torneo: int, rol: str = Depends(solo_administrador)):
    # Promedio por fecha y, en la última fila (numero_fecha nulo), el de toda la edición
    sql = """
        SELECT p.numero_fecha,
               COUNT(DISTINCT p.id_partido) AS partidos,
               COUNT(g.id_gol) AS goles,
               ROUND(COUNT(g.id_gol) / COUNT(DISTINCT p.id_partido), 2) AS promedio
        FROM partido p
        LEFT JOIN gol g ON g.id_partido = p.id_partido
        WHERE p.id_torneo = %s AND p.estado = 'jugado'
        GROUP BY p.numero_fecha WITH ROLLUP
    """
    return consultar(rol, sql, (id_torneo,))


@router.get("/consultas/canchas-usadas")
def canchas_mas_utilizadas(id_torneo: int, rol: str = Depends(solo_administrador)):
    sql = """
        SELECT p.nombre_cancha, c.nombre AS complejo, COUNT(*) AS partidos
        FROM partido p
        JOIN complejo c ON c.id_complejo = p.id_complejo
        WHERE p.id_torneo = %s AND p.estado = 'jugado'
        GROUP BY p.nombre_cancha, p.id_complejo, c.nombre
        ORDER BY partidos DESC, c.nombre, p.nombre_cancha
    """
    return consultar(rol, sql, (id_torneo,))


@router.get("/consultas/turnos-usados")
def turnos_mas_utilizados(id_torneo: int, rol: str = Depends(solo_administrador)):
    sql = """
        SELECT p.id_turno, LEFT(tu.hora_inicio, 5) AS hora_inicio, LEFT(tu.hora_fin, 5) AS hora_fin,
               COUNT(*) AS partidos
        FROM partido p
        JOIN turno tu ON tu.id_turno = p.id_turno
        WHERE p.id_torneo = %s AND p.estado = 'jugado'
        GROUP BY p.id_turno, tu.hora_inicio, tu.hora_fin
        ORDER BY partidos DESC, tu.hora_inicio
    """
    return consultar(rol, sql, (id_torneo,))


@router.get("/consultas/jugadores-por-facultad")
def jugadores_por_facultad_y_tipo(rol: str = Depends(solo_administrador)):
    # Con ROLLUP: tipo nulo es el subtotal de la facultad y la última fila el total general
    sql = """
        SELECT f.nombre AS facultad, j.tipo, COUNT(*) AS cantidad
        FROM jugador j
        JOIN facultad f ON f.id_facultad = j.id_facultad
        GROUP BY f.nombre, j.tipo WITH ROLLUP
    """
    return consultar(rol, sql)


@router.get("/consultas/sin-planilla")
def inscriptos_sin_planilla(id_torneo: int, rol: str = Depends(solo_administrador)):
    # Jugadores de un plantel que no figuraron en ninguna planilla de la edición
    sql = """
        SELECT j.ci, j.nombre, j.apellido, j.tipo, e.nombre AS equipo, f.nombre AS facultad
        FROM equipo_jugador_torneo ejt
        JOIN jugador j ON j.ci = ejt.ci_jugador
        JOIN equipo e ON e.id_equipo = ejt.id_equipo
        JOIN facultad f ON f.id_facultad = j.id_facultad
        WHERE ejt.id_torneo = %s
          AND NOT EXISTS (
              SELECT 1 FROM planilla_partido pp
              JOIN partido p ON p.id_partido = pp.id_partido
              WHERE pp.ci_jugador = ejt.ci_jugador AND p.id_torneo = ejt.id_torneo)
        ORDER BY e.nombre, j.apellido, j.nombre
    """
    return consultar(rol, sql, (id_torneo,))


@router.get("/consultas/sanciones-por-equipo")
def sanciones_por_equipo_y_motivo(id_torneo: int, rol: str = Depends(solo_administrador)):
    sql = """
        SELECT e.nombre AS equipo, s.motivo, COUNT(*) AS cantidad,
               SUM(s.cantidad_fechas) AS fechas_de_suspension
        FROM sancion_jugador s
        JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = s.ci_jugador AND ejt.id_torneo = s.id_torneo
        JOIN equipo e ON e.id_equipo = ejt.id_equipo
        WHERE s.id_torneo = %s
        GROUP BY e.id_equipo, e.nombre, s.motivo
        ORDER BY cantidad DESC, e.nombre, s.motivo
    """
    return consultar(rol, sql, (id_torneo,))


@router.get("/consultas/porcentaje-partidos")
def porcentaje_de_partidos(id_torneo: int, rol: str = Depends(solo_administrador)):
    # Cuántos partidos hay en cada estado y qué porcentaje del total representan
    sql = """
        SELECT p.estado, COUNT(*) AS cantidad,
               ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM partido WHERE id_torneo = %s), 2) AS porcentaje
        FROM partido p
        WHERE p.id_torneo = %s
        GROUP BY p.estado
        ORDER BY cantidad DESC, p.estado
    """
    return consultar(rol, sql, (id_torneo, id_torneo))


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