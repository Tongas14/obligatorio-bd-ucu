SET NAMES utf8mb4;
USE torneo_ucu;

CREATE TABLE login (
    correo VARCHAR(100) PRIMARY KEY,
    contraseña VARCHAR(255) NOT NULL,
    rol ENUM('administrador', 'planillero') NOT NULL
);

CREATE TABLE facultad (
    id_facultad INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE jugador (
    ci VARCHAR(15) PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    fecha_nacimiento DATE NOT NULL,
    id_facultad INT NOT NULL,
    tipo ENUM('grado', 'posgrado', 'docente', 'funcionario') NOT NULL,
    CHECK (email LIKE '%_@_%._%'),
    FOREIGN KEY (id_facultad) REFERENCES facultad(id_facultad)
);

CREATE TABLE torneo (
    id_torneo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    año INT NOT NULL,
    semestre INT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado ENUM('inscripción', 'en curso', 'finalizado') NOT NULL,
    UNIQUE (año, semestre),
    CHECK (semestre IN (1, 2)),
    CHECK (año BETWEEN 2000 AND 2100),
    CHECK (fecha_fin > fecha_inicio)
);

CREATE TABLE equipo (
    id_equipo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    id_torneo INT NOT NULL,
    id_facultad INT NOT NULL,
    ci_capitan VARCHAR(15) NOT NULL,
    UNIQUE (nombre, id_torneo),
    FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
    FOREIGN KEY (id_facultad) REFERENCES facultad(id_facultad),
    FOREIGN KEY (ci_capitan) REFERENCES jugador(ci)
);

-- UNIQUE (ci_jugador, id_torneo): un jugador no integra más de un equipo en la misma edición
CREATE TABLE equipo_jugador_torneo (
    id_equipo INT,
    ci_jugador VARCHAR(15),
    id_torneo INT,
    numero_camiseta INT NOT NULL,
    PRIMARY KEY (id_equipo, ci_jugador, id_torneo),
    UNIQUE (ci_jugador, id_torneo),
    UNIQUE (id_equipo, numero_camiseta),
    CHECK (numero_camiseta BETWEEN 1 AND 99),
    FOREIGN KEY (id_equipo) REFERENCES equipo(id_equipo),
    FOREIGN KEY (ci_jugador) REFERENCES jugador(ci),
    FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo)
);

CREATE TABLE complejo (
    id_complejo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    direccion VARCHAR(200) NOT NULL,
    departamento VARCHAR(100) NOT NULL
);

CREATE TABLE cancha (
    nombre_cancha VARCHAR(50),
    id_complejo INT,
    superficie ENUM('sintético', 'parquet') NOT NULL,
    techada BOOLEAN NOT NULL,
    PRIMARY KEY (nombre_cancha, id_complejo),
    FOREIGN KEY (id_complejo) REFERENCES complejo(id_complejo)
);

CREATE TABLE turno (
    id_turno INT PRIMARY KEY,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL
);

CREATE TABLE partido (
    id_partido INT AUTO_INCREMENT PRIMARY KEY,
    id_torneo INT NOT NULL,
    numero_fecha INT NOT NULL,
    id_equipo_local INT NOT NULL,
    id_equipo_visitante INT NOT NULL,
    dia DATE NOT NULL,
    id_turno INT NOT NULL,
    nombre_cancha VARCHAR(50) NOT NULL,
    id_complejo INT NOT NULL,
    estado ENUM('programado', 'jugado', 'postergado', 'cancelado') NOT NULL,
    CHECK (id_equipo_local <> id_equipo_visitante),
    CHECK (numero_fecha >= 1),
    FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
    FOREIGN KEY (id_equipo_local) REFERENCES equipo(id_equipo),
    FOREIGN KEY (id_equipo_visitante) REFERENCES equipo(id_equipo),
    FOREIGN KEY (id_turno) REFERENCES turno(id_turno),
    FOREIGN KEY (nombre_cancha, id_complejo) REFERENCES cancha(nombre_cancha, id_complejo)
);

CREATE TABLE planilla_partido (
    id_partido INT,
    ci_jugador VARCHAR(15),
    id_equipo INT NOT NULL,
    PRIMARY KEY (id_partido, ci_jugador),
    FOREIGN KEY (id_partido) REFERENCES partido(id_partido),
    FOREIGN KEY (ci_jugador) REFERENCES jugador(ci),
    FOREIGN KEY (id_equipo) REFERENCES equipo(id_equipo)
);

CREATE TABLE gol (
    id_gol INT AUTO_INCREMENT PRIMARY KEY,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    minuto INT NOT NULL,
    autogol BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (minuto BETWEEN 0 AND 60),
    FOREIGN KEY (id_partido) REFERENCES partido(id_partido),
    FOREIGN KEY (ci_jugador) REFERENCES jugador(ci)
);

CREATE TABLE tarjeta (
    id_tarjeta INT AUTO_INCREMENT PRIMARY KEY,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    minuto INT NOT NULL,
    color ENUM('amarilla', 'roja') NOT NULL,
    CHECK (minuto BETWEEN 0 AND 60),
    FOREIGN KEY (id_partido) REFERENCES partido(id_partido),
    FOREIGN KEY (ci_jugador) REFERENCES jugador(ci)
);

-- id_tarjeta_origen: tarjeta que generó la sanción automática (NULL en las disciplinarias)
CREATE TABLE sancion_jugador (
    id_sancion INT AUTO_INCREMENT PRIMARY KEY,
    ci_jugador VARCHAR(15) NOT NULL,
    id_torneo INT NOT NULL,
    motivo ENUM('roja', 'acumulación de amarillas', 'disciplinaria') NOT NULL,
    numero_fecha_inicio INT NOT NULL,
    cantidad_fechas INT NOT NULL,
    id_tarjeta_origen INT NULL,
    CHECK (numero_fecha_inicio >= 1),
    CHECK (cantidad_fechas >= 1),
    FOREIGN KEY (ci_jugador) REFERENCES jugador(ci),
    FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
    FOREIGN KEY (id_tarjeta_origen) REFERENCES tarjeta(id_tarjeta)
);



-- Las contraseñas se guardan como hash SHA-256, no en texto plano
INSERT INTO login VALUES
    ('admin@ucu.edu.uy', SHA2('admin2026', 256), 'administrador'),
    ('planillero@ucu.edu.uy', SHA2('planillero2026', 256), 'planillero');

INSERT INTO facultad VALUES
    (1, 'Ingenieria'), (2, 'Ciencias Empresariales'), (3, 'Derecho');

INSERT INTO jugador VALUES
    ('401001', 'Emiliano', 'Guzman', 'eguzman0@ucu.edu.uy', '1998-04-24', 1, 'grado'),
    ('401002', 'Matias', 'Perez', 'mperez1@ucu.edu.uy', '2006-02-13', 1, 'grado'),
    ('401003', 'Emiliano', 'Gomez', 'egomez2@ucu.edu.uy', '2003-05-23', 1, 'grado'),
    ('401004', 'Facundo', 'Perez', 'fperez3@ucu.edu.uy', '2006-08-19', 1, 'grado'),
    ('401005', 'Federico', 'Guzman', 'fguzman4@ucu.edu.uy', '2002-07-06', 1, 'grado'),
    ('401006', 'Facundo', 'Methol', 'fmethol5@ucu.edu.uy', '2002-12-25', 1, 'posgrado'),
    ('401007', 'Juan', 'Techera', 'jtechera6@ucu.edu.uy', '1982-06-23', 1, 'docente'),
    ('402001', 'Emiliano', 'Techera', 'etechera7@ucu.edu.uy', '2003-07-11', 2, 'grado'),
    ('402002', 'Santiago', 'Rios', 'srios8@ucu.edu.uy', '2002-01-28', 2, 'grado'),
    ('402003', 'Santiago', 'Ferreira', 'sferreira9@ucu.edu.uy', '2005-04-23', 2, 'grado'),
    ('402004', 'Facundo', 'Guzman', 'fguzman10@ucu.edu.uy', '1998-12-21', 2, 'grado'),
    ('402005', 'Ariel', 'Guzman', 'aguzman11@ucu.edu.uy', '2002-12-01', 2, 'posgrado'),
    ('402006', 'Ignacio', 'Ferreira', 'iferreira12@ucu.edu.uy', '1998-04-11', 2, 'posgrado'),
    ('402007', 'Martin', 'Ferreira', 'mferreira13@ucu.edu.uy', '1987-01-07', 2, 'funcionario'),
    ('403001', 'Mauricio', 'Lopez', 'mlopez14@ucu.edu.uy', '2003-07-16', 3, 'grado'),
    ('403002', 'Pablo', 'Pereyra', 'ppereyra15@ucu.edu.uy', '2006-12-20', 3, 'grado'),
    ('403003', 'Bruno', 'Fernandez', 'bfernandez16@ucu.edu.uy', '2005-03-07', 3, 'grado'),
    ('403004', 'Emiliano', 'Cabrera', 'ecabrera17@ucu.edu.uy', '2003-05-27', 3, 'grado'),
    ('403005', 'Joaquin', 'Gomez', 'jgomez18@ucu.edu.uy', '2003-09-27', 3, 'posgrado'),
    ('403006', 'Matias', 'Olivera', 'molivera19@ucu.edu.uy', '1989-03-16', 3, 'docente'),
    ('403007', 'Gaston', 'Castro', 'gcastro20@ucu.edu.uy', '1984-03-17', 3, 'funcionario'),
    ('404001', 'Nicolas', 'Rodriguez', 'nrodriguez21@ucu.edu.uy', '2003-11-20', 1, 'grado'),
    ('404002', 'Agustin', 'Ferreira', 'aferreira22@ucu.edu.uy', '2005-10-23', 1, 'grado'),
    ('404003', 'Sebastian', 'Pereyra', 'spereyra23@ucu.edu.uy', '2004-12-09', 1, 'grado'),
    ('404004', 'Diego', 'Rodriguez', 'drodriguez24@ucu.edu.uy', '2006-02-19', 1, 'grado'),
    ('404005', 'Santiago', 'Cabrera', 'scabrera25@ucu.edu.uy', '2006-03-18', 1, 'grado'),
    ('404006', 'Facundo', 'Bravo', 'fbravo26@ucu.edu.uy', '2003-08-01', 1, 'grado'),
    ('404007', 'Diego', 'Sosa', 'dsosa27@ucu.edu.uy', '2000-02-23', 1, 'posgrado'),
    ('405001', 'Juan', 'Cabrera', 'jcabrera28@ucu.edu.uy', '2005-11-13', 2, 'grado'),
    ('405002', 'Emiliano', 'Perez', 'eperez29@ucu.edu.uy', '2001-03-07', 2, 'grado'),
    ('405003', 'Joaquin', 'Silva', 'jsilva30@ucu.edu.uy', '2003-04-07', 2, 'grado'),
    ('405004', 'Federico', 'Castro', 'fcastro31@ucu.edu.uy', '2001-05-02', 2, 'grado'),
    ('405005', 'Diego', 'Castro', 'dcastro32@ucu.edu.uy', '2001-08-07', 2, 'posgrado'),
    ('405006', 'Ariel', 'Rodriguez', 'arodriguez33@ucu.edu.uy', '1983-11-06', 2, 'docente'),
    ('405007', 'Emiliano', 'Varela', 'evarela34@ucu.edu.uy', '1983-11-09', 2, 'funcionario'),
    ('406001', 'Nicolas', 'Pereyra', 'npereyra35@ucu.edu.uy', '2005-01-10', 3, 'grado'),
    ('406002', 'Pablo', 'Varela', 'pvarela36@ucu.edu.uy', '2006-08-02', 3, 'grado'),
    ('406003', 'Alexis', 'Rodriguez', 'arodriguez37@ucu.edu.uy', '1999-04-19', 3, 'grado'),
    ('406004', 'Diego', 'Rios', 'drios38@ucu.edu.uy', '1999-02-13', 3, 'grado'),
    ('406005', 'Juan', 'Silva', 'jsilva39@ucu.edu.uy', '2000-01-05', 3, 'grado'),
    ('406006', 'Emiliano', 'Lopez', 'elopez40@ucu.edu.uy', '2001-05-15', 3, 'posgrado'),
    ('406007', 'Juan', 'Ferreira', 'jferreira41@ucu.edu.uy', '1990-04-06', 3, 'docente');

INSERT INTO torneo VALUES
    (1, 'Interfacultades', 2026, 2, '2026-08-15', '2026-11-20', 'en curso');

-- El capitán es el primer jugador del plantel de cada equipo
INSERT INTO equipo VALUES
    (1, 'Sistemas', 1, 1, '401001'), (2, 'Economia', 1, 2, '402001'),
    (3, 'Leyes', 1, 3, '403001'), (4, 'Mecanica', 1, 1, '404001'),
    (5, 'Contadores', 1, 2, '405001'), (6, 'Notarios', 1, 3, '406001');

-- 7 jugadores por equipo
INSERT INTO equipo_jugador_torneo VALUES
    (1, '401001', 1, 1), (1, '401002', 1, 2), (1, '401003', 1, 3), (1, '401004', 1, 4),
    (1, '401005', 1, 5), (1, '401006', 1, 6), (1, '401007', 1, 7), (2, '402001', 1, 1),
    (2, '402002', 1, 2), (2, '402003', 1, 3), (2, '402004', 1, 4), (2, '402005', 1, 5),
    (2, '402006', 1, 6), (2, '402007', 1, 7), (3, '403001', 1, 1), (3, '403002', 1, 2),
    (3, '403003', 1, 3), (3, '403004', 1, 4), (3, '403005', 1, 5), (3, '403006', 1, 6),
    (3, '403007', 1, 7), (4, '404001', 1, 1), (4, '404002', 1, 2), (4, '404003', 1, 3),
    (4, '404004', 1, 4), (4, '404005', 1, 5), (4, '404006', 1, 6), (4, '404007', 1, 7),
    (5, '405001', 1, 1), (5, '405002', 1, 2), (5, '405003', 1, 3), (5, '405004', 1, 4),
    (5, '405005', 1, 5), (5, '405006', 1, 6), (5, '405007', 1, 7), (6, '406001', 1, 1),
    (6, '406002', 1, 2), (6, '406003', 1, 3), (6, '406004', 1, 4), (6, '406005', 1, 5),
    (6, '406006', 1, 6), (6, '406007', 1, 7);

INSERT INTO complejo VALUES
    (1, 'UCU Deportes', 'Av. 8 de Octubre 2738', 'Montevideo'),
    (2, 'Complejo Malvín', 'Av. Rivera 4000', 'Montevideo');

INSERT INTO cancha VALUES
    ('Cancha 1', 1, 'sintético', TRUE), ('Cancha 2', 1, 'parquet', FALSE),
    ('Cancha A', 2, 'sintético', FALSE);

INSERT INTO turno VALUES
    (1, '18:00', '19:00'), (2, '19:00', '20:00'),
    (3, '20:00', '21:00'), (4, '21:00', '22:00'),
    (5, '22:00', '23:00');

-- Liga a una rueda: 6 equipos, 15 partidos en 5 fechas.
-- Fechas 1 a 3 jugadas, fecha 4 con un postergado, un cancelado y un jugado,
-- fecha 5 todavía programada.
INSERT INTO partido VALUES
    (1, 1, 1, 1, 2, '2026-09-01', 1, 'Cancha 1', 1, 'jugado'),
    (2, 1, 1, 3, 6, '2026-09-01', 1, 'Cancha 2', 1, 'jugado'),
    (3, 1, 1, 4, 5, '2026-09-01', 2, 'Cancha 1', 1, 'jugado'),
    (4, 1, 2, 1, 3, '2026-09-08', 1, 'Cancha 1', 1, 'jugado'),
    (5, 1, 2, 2, 4, '2026-09-08', 2, 'Cancha 1', 1, 'jugado'),
    (6, 1, 2, 5, 6, '2026-09-08', 3, 'Cancha A', 2, 'jugado'),
    (7, 1, 3, 1, 4, '2026-09-15', 1, 'Cancha 1', 1, 'jugado'),
    (8, 1, 3, 3, 5, '2026-09-15', 2, 'Cancha 2', 1, 'jugado'),
    (9, 1, 3, 2, 6, '2026-09-15', 3, 'Cancha 1', 1, 'jugado'),
    (10, 1, 4, 1, 5, '2026-09-22', 1, 'Cancha 1', 1, 'postergado'),
    (11, 1, 4, 4, 6, '2026-09-22', 1, 'Cancha 2', 1, 'cancelado'),
    (12, 1, 4, 2, 3, '2026-09-22', 2, 'Cancha 1', 1, 'jugado'),
    (13, 1, 5, 1, 6, '2026-11-10', 1, 'Cancha 1', 1, 'programado'),
    (14, 1, 5, 2, 5, '2026-11-10', 1, 'Cancha 2', 1, 'programado'),
    (15, 1, 5, 3, 4, CURDATE() - INTERVAL 1 DAY, 1, 'Cancha A', 2, 'programado');

-- Planillas: 5 jugadores por equipo en cada partido jugado.
-- Los suspendidos no figuran y entra el suplente.
INSERT INTO planilla_partido VALUES
    (1, '401001', 1), (1, '401002', 1), (1, '401003', 1), (1, '401004', 1), (1, '401005', 1),
    (1, '402001', 2), (1, '402002', 2), (1, '402003', 2), (1, '402004', 2), (1, '402005', 2),
    (2, '403001', 3), (2, '403002', 3), (2, '403003', 3), (2, '403004', 3), (2, '403005', 3),
    (2, '406001', 6), (2, '406002', 6), (2, '406003', 6), (2, '406004', 6), (2, '406005', 6),
    (3, '404001', 4), (3, '404002', 4), (3, '404003', 4), (3, '404004', 4), (3, '404005', 4),
    (3, '405001', 5), (3, '405002', 5), (3, '405003', 5), (3, '405004', 5), (3, '405005', 5),
    (4, '401001', 1), (4, '401003', 1), (4, '401004', 1), (4, '401005', 1), (4, '401006', 1),
    (4, '403001', 3), (4, '403002', 3), (4, '403003', 3), (4, '403004', 3), (4, '403005', 3),
    (5, '402001', 2), (5, '402002', 2), (5, '402003', 2), (5, '402004', 2), (5, '402005', 2),
    (5, '404001', 4), (5, '404002', 4), (5, '404003', 4), (5, '404004', 4), (5, '404005', 4),
    (6, '405001', 5), (6, '405002', 5), (6, '405003', 5), (6, '405004', 5), (6, '405005', 5),
    (6, '406001', 6), (6, '406002', 6), (6, '406003', 6), (6, '406004', 6), (6, '406005', 6),
    (7, '401001', 1), (7, '401002', 1), (7, '401004', 1), (7, '401005', 1), (7, '401006', 1),
    (7, '404001', 4), (7, '404002', 4), (7, '404003', 4), (7, '404004', 4), (7, '404005', 4),
    (8, '403001', 3), (8, '403002', 3), (8, '403003', 3), (8, '403004', 3), (8, '403005', 3),
    (8, '405001', 5), (8, '405002', 5), (8, '405003', 5), (8, '405004', 5), (8, '405005', 5),
    (9, '402001', 2), (9, '402002', 2), (9, '402003', 2), (9, '402004', 2), (9, '402005', 2),
    (9, '406001', 6), (9, '406002', 6), (9, '406003', 6), (9, '406004', 6), (9, '406005', 6),
    (12, '402001', 2), (12, '402002', 2), (12, '402003', 2), (12, '402004', 2), (12, '402005', 2),
    (12, '403001', 3), (12, '403002', 3), (12, '403003', 3), (12, '403004', 3), (12, '403005', 3);

INSERT INTO gol VALUES
    (1, 1, '401005', 29, 0), (2, 1, '401005', 39, 0), (3, 1, '401004', 43, 0),
    (4, 1, '402002', 53, 0), (5, 2, '403002', 17, 0), (6, 2, '403004', 19, 0),
    (7, 2, '406005', 31, 0), (8, 2, '406002', 49, 0), (9, 3, '404004', 27, 1),
    (10, 4, '401004', 28, 0), (11, 4, '401005', 51, 0), (12, 5, '402003', 10, 0),
    (13, 5, '404001', 20, 0), (14, 6, '405002', 1, 0), (15, 6, '405003', 3, 0),
    (16, 6, '405005', 6, 0), (17, 6, '405003', 13, 0), (18, 6, '406005', 15, 0),
    (19, 6, '406005', 17, 0), (20, 7, '401004', 27, 0), (21, 8, '403002', 11, 0),
    (22, 8, '403003', 18, 0), (23, 8, '405003', 52, 0), (24, 8, '405001', 53, 0),
    (25, 8, '405005', 59, 0), (26, 12, '402001', 14, 0), (27, 12, '403001', 39, 0),
    (28, 12, '403001', 49, 0);

INSERT INTO tarjeta VALUES
    (1, 1, '401002', 27, 'roja'), (2, 2, '406005', 41, 'amarilla'), (3, 3, '404003', 35, 'amarilla'),
    (4, 3, '405004', 8, 'amarilla'), (5, 3, '404002', 31, 'amarilla'), (6, 4, '403002', 45, 'amarilla'),
    (7, 4, '401001', 17, 'amarilla'), (8, 4, '401003', 25, 'roja'), (9, 5, '402001', 44, 'amarilla'),
    (10, 5, '404001', 29, 'amarilla'), (11, 6, '406005', 8, 'amarilla'), (12, 7, '404003', 58, 'amarilla'),
    (13, 8, '403001', 52, 'amarilla'), (14, 9, '406003', 9, 'amarilla'), (15, 9, '406005', 27, 'amarilla'),
    (16, 12, '402004', 12, 'amarilla'), (17, 12, '402005', 38, 'amarilla');

-- Las sanciones se cargan a mano porque los triggers que las generan se crean
-- más abajo, después de estos datos. Cada roja y cada 3era amarilla suspende la fecha siguiente.
INSERT INTO sancion_jugador VALUES
    (1, '406003', 1, 'disciplinaria', 4, 2, NULL),
    (2, '404002', 1, 'disciplinaria', 5, 1, NULL),
    (3, '401002', 1, 'roja', 2, 1, 1),
    (4, '401003', 1, 'roja', 3, 1, 8),
    (5, '406005', 1, 'acumulación de amarillas', 4, 1, 15);


-- Reglas de planteles, partidos, planillas y sanciones.
-- Van después de los datos de prueba para que las reglas de inscripción y de 48 horas no los bloqueen.

DELIMITER //

-- Un alta o cambio en un plantel solo se permite en inscripción, con jugadores de la
-- facultad del equipo, hasta 10 jugadores y hasta 2 docentes o funcionarios
CREATE PROCEDURE sp_validar_plantel(IN p_id_equipo INT, IN p_ci VARCHAR(15), IN p_id_torneo INT)
BEGIN
    DECLARE v_id_torneo INT;
    DECLARE v_id_facultad INT;

    SELECT id_torneo, id_facultad INTO v_id_torneo, v_id_facultad FROM equipo WHERE id_equipo = p_id_equipo;

    IF v_id_torneo <> p_id_torneo THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El torneo del plantel no coincide con el del equipo';
    END IF;
    IF (SELECT estado FROM torneo WHERE id_torneo = p_id_torneo) <> 'inscripción' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El plantel solo se puede modificar en etapa de inscripción';
    END IF;
    IF (SELECT id_facultad FROM jugador WHERE ci = p_ci) <> v_id_facultad THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador no pertenece a la facultad del equipo';
    END IF;
    IF (SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo = p_id_equipo AND ci_jugador <> p_ci) >= 10 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El plantel no puede tener más de 10 jugadores';
    END IF;
    IF (SELECT tipo FROM jugador WHERE ci = p_ci) IN ('docente', 'funcionario') AND (
        SELECT COUNT(*) FROM equipo_jugador_torneo ejt JOIN jugador j ON j.ci = ejt.ci_jugador
        WHERE ejt.id_equipo = p_id_equipo AND ejt.ci_jugador <> p_ci AND j.tipo IN ('docente', 'funcionario')
    ) >= 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El plantel no puede tener más de 2 docentes o funcionarios';
    END IF;
END//

CREATE TRIGGER trg_plantel_bi BEFORE INSERT ON equipo_jugador_torneo
FOR EACH ROW
BEGIN
    CALL sp_validar_plantel(NEW.id_equipo, NEW.ci_jugador, NEW.id_torneo);
END//

CREATE TRIGGER trg_plantel_bu BEFORE UPDATE ON equipo_jugador_torneo
FOR EACH ROW
BEGIN
    CALL sp_validar_plantel(NEW.id_equipo, NEW.ci_jugador, NEW.id_torneo);
END//

CREATE TRIGGER trg_plantel_bd BEFORE DELETE ON equipo_jugador_torneo
FOR EACH ROW
BEGIN
    IF (SELECT estado FROM torneo WHERE id_torneo = OLD.id_torneo) <> 'inscripción' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El plantel solo se puede modificar en etapa de inscripción';
    END IF;
END//

-- Momento en que termina un partido (día + hora de fin del turno)
CREATE FUNCTION fn_fin_partido(p_dia DATE, p_id_turno INT) RETURNS DATETIME
READS SQL DATA
BEGIN
    DECLARE v_hora_fin TIME;
    SELECT hora_fin INTO v_hora_fin FROM turno WHERE id_turno = p_id_turno;
    RETURN TIMESTAMP(p_dia, v_hora_fin);
END//

-- Un jugador está suspendido en una fecha si alguna sanción la abarca:
-- desde numero_fecha_inicio hasta numero_fecha_inicio + cantidad_fechas - 1
CREATE FUNCTION fn_jugador_suspendido(p_ci VARCHAR(15), p_id_torneo INT, p_numero_fecha INT) RETURNS BOOLEAN
READS SQL DATA
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM sancion_jugador
        WHERE ci_jugador = p_ci
          AND id_torneo = p_id_torneo
          AND p_numero_fecha BETWEEN numero_fecha_inicio AND numero_fecha_inicio + cantidad_fechas - 1
    );
END//

CREATE PROCEDURE sp_validar_partido(
    IN p_id_partido INT, IN p_id_torneo INT, IN p_numero_fecha INT,
    IN p_local INT, IN p_visitante INT, IN p_dia DATE, IN p_id_turno INT,
    IN p_nombre_cancha VARCHAR(50), IN p_id_complejo INT, IN p_estado VARCHAR(20))
BEGIN
    IF p_local = p_visitante THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Un equipo no puede enfrentarse a sí mismo';
    END IF;

    IF (SELECT COUNT(*) FROM equipo WHERE id_equipo IN (p_local, p_visitante) AND id_torneo = p_id_torneo) <> 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ambos equipos deben pertenecer a la edición del torneo del partido';
    END IF;

    IF (SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo = p_local) < 5
       OR (SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo = p_visitante) < 5 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ambos equipos deben tener al menos 5 jugadores en su plantel';
    END IF;

    IF p_estado <> 'cancelado' THEN
        IF EXISTS (
            SELECT 1 FROM partido
            WHERE id_torneo = p_id_torneo AND id_partido <> p_id_partido AND estado <> 'cancelado'
              AND ((id_equipo_local = p_local AND id_equipo_visitante = p_visitante)
                OR (id_equipo_local = p_visitante AND id_equipo_visitante = p_local))
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Estos equipos ya tienen un partido no cancelado en esta edición';
        END IF;

        IF EXISTS (
            SELECT 1 FROM partido
            WHERE id_torneo = p_id_torneo AND numero_fecha = p_numero_fecha
              AND id_partido <> p_id_partido AND estado <> 'cancelado'
              AND (id_equipo_local IN (p_local, p_visitante) OR id_equipo_visitante IN (p_local, p_visitante))
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Uno de los equipos ya tiene un partido en esa fecha del torneo';
        END IF;
    END IF;

    IF p_estado NOT IN ('cancelado', 'postergado') AND EXISTS (
        SELECT 1 FROM partido
        WHERE nombre_cancha = p_nombre_cancha AND id_complejo = p_id_complejo
          AND dia = p_dia AND id_turno = p_id_turno
          AND id_partido <> p_id_partido AND estado NOT IN ('cancelado', 'postergado')
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La cancha ya tiene un partido asignado en ese día y turno';
    END IF;

    IF p_estado = 'jugado' AND fn_fin_partido(p_dia, p_id_turno) > NOW() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Un partido solo puede marcarse como jugado si su día y turno ya pasaron';
    END IF;
END//

-- Controla que se pueda cargar o corregir la planilla, goles o tarjetas de un partido
CREATE PROCEDURE sp_validar_carga_partido(IN p_id_partido INT)
BEGIN
    DECLARE v_estado VARCHAR(20);
    DECLARE v_fin DATETIME;

    SELECT estado, fn_fin_partido(dia, id_turno) INTO v_estado, v_fin
    FROM partido WHERE id_partido = p_id_partido;

    IF v_estado IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El partido no existe';
    END IF;
    IF v_estado IN ('cancelado', 'postergado') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No se puede cargar la planilla de un partido cancelado o postergado';
    END IF;
    IF v_fin > NOW() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El partido todavía no se disputó';
    END IF;
    IF v_estado = 'jugado' AND NOW() > v_fin + INTERVAL 48 HOUR THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Pasaron más de 48 horas desde el partido, ya no se puede corregir';
    END IF;
END//

CREATE PROCEDURE sp_validar_jugador_en_planilla(IN p_id_partido INT, IN p_ci VARCHAR(15))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM planilla_partido WHERE id_partido = p_id_partido AND ci_jugador = p_ci) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador no figura en la planilla del partido';
    END IF;
END//

CREATE PROCEDURE sp_validar_planilla(IN p_id_partido INT, IN p_ci VARCHAR(15), IN p_id_equipo INT)
BEGIN
    DECLARE v_id_torneo INT;
    DECLARE v_numero_fecha INT;

    CALL sp_validar_carga_partido(p_id_partido);

    SELECT id_torneo, numero_fecha INTO v_id_torneo, v_numero_fecha
    FROM partido
    WHERE id_partido = p_id_partido AND p_id_equipo IN (id_equipo_local, id_equipo_visitante);

    IF v_id_torneo IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El equipo no juega este partido';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM equipo_jugador_torneo WHERE id_equipo = p_id_equipo AND ci_jugador = p_ci) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador no pertenece al plantel de su equipo';
    END IF;
    IF fn_jugador_suspendido(p_ci, v_id_torneo, v_numero_fecha) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador está suspendido para esta fecha';
    END IF;
END//

CREATE TRIGGER trg_partido_bi BEFORE INSERT ON partido
FOR EACH ROW
BEGIN
    CALL sp_validar_partido(0, NEW.id_torneo, NEW.numero_fecha, NEW.id_equipo_local, NEW.id_equipo_visitante,
                            NEW.dia, NEW.id_turno, NEW.nombre_cancha, NEW.id_complejo, NEW.estado);
END//

CREATE TRIGGER trg_partido_bu BEFORE UPDATE ON partido
FOR EACH ROW
BEGIN
    IF OLD.estado = 'jugado' AND NOW() > fn_fin_partido(OLD.dia, OLD.id_turno) + INTERVAL 48 HOUR THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Pasaron más de 48 horas desde el partido, ya no se puede modificar';
    END IF;
    IF (OLD.id_torneo <> NEW.id_torneo OR OLD.id_equipo_local <> NEW.id_equipo_local
        OR OLD.id_equipo_visitante <> NEW.id_equipo_visitante)
       AND EXISTS (SELECT 1 FROM planilla_partido WHERE id_partido = OLD.id_partido) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No se pueden cambiar los equipos de un partido con planilla cargada';
    END IF;
    IF NEW.estado IN ('cancelado', 'postergado')
       AND EXISTS (SELECT 1 FROM planilla_partido WHERE id_partido = OLD.id_partido) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No se puede cancelar ni postergar un partido con planilla cargada';
    END IF;
    CALL sp_validar_partido(NEW.id_partido, NEW.id_torneo, NEW.numero_fecha, NEW.id_equipo_local, NEW.id_equipo_visitante,
                            NEW.dia, NEW.id_turno, NEW.nombre_cancha, NEW.id_complejo, NEW.estado);
END//

CREATE TRIGGER trg_partido_bd BEFORE DELETE ON partido
FOR EACH ROW
BEGIN
    IF OLD.estado = 'jugado' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Un partido jugado no se puede eliminar';
    END IF;
END//

CREATE TRIGGER trg_planilla_bi BEFORE INSERT ON planilla_partido
FOR EACH ROW
BEGIN
    CALL sp_validar_planilla(NEW.id_partido, NEW.ci_jugador, NEW.id_equipo);
END//

CREATE TRIGGER trg_planilla_bu BEFORE UPDATE ON planilla_partido
FOR EACH ROW
BEGIN
    CALL sp_validar_planilla(NEW.id_partido, NEW.ci_jugador, NEW.id_equipo);
END//

CREATE TRIGGER trg_planilla_bd BEFORE DELETE ON planilla_partido
FOR EACH ROW
BEGIN
    CALL sp_validar_carga_partido(OLD.id_partido);
    IF EXISTS (SELECT 1 FROM gol WHERE id_partido = OLD.id_partido AND ci_jugador = OLD.ci_jugador)
       OR EXISTS (SELECT 1 FROM tarjeta WHERE id_partido = OLD.id_partido AND ci_jugador = OLD.ci_jugador) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador tiene goles o tarjetas en el partido, elimínelos primero';
    END IF;
END//

CREATE TRIGGER trg_gol_bi BEFORE INSERT ON gol
FOR EACH ROW
BEGIN
    CALL sp_validar_carga_partido(NEW.id_partido);
    CALL sp_validar_jugador_en_planilla(NEW.id_partido, NEW.ci_jugador);
END//

CREATE TRIGGER trg_gol_bu BEFORE UPDATE ON gol
FOR EACH ROW
BEGIN
    CALL sp_validar_carga_partido(OLD.id_partido);
    CALL sp_validar_carga_partido(NEW.id_partido);
    CALL sp_validar_jugador_en_planilla(NEW.id_partido, NEW.ci_jugador);
END//

CREATE TRIGGER trg_gol_bd BEFORE DELETE ON gol
FOR EACH ROW
BEGIN
    CALL sp_validar_carga_partido(OLD.id_partido);
END//

CREATE TRIGGER trg_tarjeta_bi BEFORE INSERT ON tarjeta
FOR EACH ROW
BEGIN
    CALL sp_validar_carga_partido(NEW.id_partido);
    CALL sp_validar_jugador_en_planilla(NEW.id_partido, NEW.ci_jugador);
    IF NEW.color = 'roja' AND EXISTS (
        SELECT 1 FROM tarjeta WHERE id_partido = NEW.id_partido AND ci_jugador = NEW.ci_jugador AND color = 'roja'
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador ya tiene una tarjeta roja en este partido';
    END IF;
    IF NEW.color = 'amarilla' AND (
        SELECT COUNT(*) FROM tarjeta WHERE id_partido = NEW.id_partido AND ci_jugador = NEW.ci_jugador AND color = 'amarilla'
    ) >= 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador ya tiene 2 tarjetas amarillas en este partido';
    END IF;
END//

-- Las tarjetas no se modifican, se eliminan y se vuelven a cargar (así las sanciones quedan bien)
CREATE TRIGGER trg_tarjeta_bu BEFORE UPDATE ON tarjeta
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Para corregir una tarjeta elimínela y vuelva a cargarla';
END//

-- Roja o 3 amarillas en la edición: 1 fecha de suspensión, en la fecha siguiente
CREATE TRIGGER trg_tarjeta_ai AFTER INSERT ON tarjeta
FOR EACH ROW
BEGIN
    DECLARE v_id_torneo INT;
    DECLARE v_numero_fecha INT;
    DECLARE v_amarillas INT;

    SELECT id_torneo, numero_fecha INTO v_id_torneo, v_numero_fecha
    FROM partido WHERE id_partido = NEW.id_partido;

    IF NEW.color = 'roja' THEN
        INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas, id_tarjeta_origen)
        VALUES (NEW.ci_jugador, v_id_torneo, 'roja', v_numero_fecha + 1, 1, NEW.id_tarjeta);
    ELSE
        SELECT COUNT(*) INTO v_amarillas
        FROM tarjeta t JOIN partido p ON p.id_partido = t.id_partido
        WHERE t.ci_jugador = NEW.ci_jugador AND p.id_torneo = v_id_torneo AND t.color = 'amarilla';

        IF v_amarillas % 3 = 0 THEN
            INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas, id_tarjeta_origen)
            VALUES (NEW.ci_jugador, v_id_torneo, 'acumulación de amarillas', v_numero_fecha + 1, 1, NEW.id_tarjeta);
        END IF;
    END IF;
END//

-- Al eliminar una tarjeta se elimina la sanción que generó. Si era amarilla,
-- se dejan solo las sanciones por acumulación que siguen correspondiendo (una cada 3)
CREATE TRIGGER trg_tarjeta_bd BEFORE DELETE ON tarjeta
FOR EACH ROW
BEGIN
    DECLARE v_id_torneo INT;
    DECLARE v_amarillas INT;
    DECLARE v_sanciones INT;

    CALL sp_validar_carga_partido(OLD.id_partido);
    DELETE FROM sancion_jugador WHERE id_tarjeta_origen = OLD.id_tarjeta;

    IF OLD.color = 'amarilla' THEN
        SELECT id_torneo INTO v_id_torneo FROM partido WHERE id_partido = OLD.id_partido;

        SELECT COUNT(*) INTO v_amarillas
        FROM tarjeta t JOIN partido p ON p.id_partido = t.id_partido
        WHERE t.ci_jugador = OLD.ci_jugador AND p.id_torneo = v_id_torneo
          AND t.color = 'amarilla' AND t.id_tarjeta <> OLD.id_tarjeta;

        SELECT COUNT(*) INTO v_sanciones
        FROM sancion_jugador
        WHERE ci_jugador = OLD.ci_jugador AND id_torneo = v_id_torneo AND motivo = 'acumulación de amarillas';

        IF v_sanciones > FLOOR(v_amarillas / 3) THEN
            DELETE FROM sancion_jugador
            WHERE ci_jugador = OLD.ci_jugador AND id_torneo = v_id_torneo AND motivo = 'acumulación de amarillas'
            ORDER BY id_sancion DESC
            LIMIT 1;
        END IF;
    END IF;
END//

-- Una sanción disciplinaria no puede abarcar fechas en las que el jugador ya figura en una planilla
CREATE PROCEDURE sp_validar_sancion(IN p_ci VARCHAR(15), IN p_id_torneo INT, IN p_motivo VARCHAR(30),
                                    IN p_inicio INT, IN p_cantidad INT)
BEGIN
    IF p_motivo = 'disciplinaria' THEN
        IF NOT EXISTS (SELECT 1 FROM equipo_jugador_torneo WHERE ci_jugador = p_ci AND id_torneo = p_id_torneo) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador no está inscripto en ningún equipo de esa edición';
        END IF;
        IF EXISTS (
            SELECT 1 FROM planilla_partido pp JOIN partido p ON p.id_partido = pp.id_partido
            WHERE pp.ci_jugador = p_ci AND p.id_torneo = p_id_torneo
              AND p.numero_fecha BETWEEN p_inicio AND p_inicio + p_cantidad - 1
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El jugador ya figura en una planilla de una fecha que abarca la sanción';
        END IF;
    END IF;
END//

CREATE TRIGGER trg_sancion_bi BEFORE INSERT ON sancion_jugador
FOR EACH ROW
BEGIN
    CALL sp_validar_sancion(NEW.ci_jugador, NEW.id_torneo, NEW.motivo, NEW.numero_fecha_inicio, NEW.cantidad_fechas);
END//

CREATE TRIGGER trg_sancion_bu BEFORE UPDATE ON sancion_jugador
FOR EACH ROW
BEGIN
    CALL sp_validar_sancion(NEW.ci_jugador, NEW.id_torneo, NEW.motivo, NEW.numero_fecha_inicio, NEW.cantidad_fechas);
END//

DELIMITER ;


CREATE USER 'app_admin'@'%' IDENTIFIED BY 'admin123';

GRANT ALL PRIVILEGES ON torneo_ucu.* TO 'app_admin'@'%';

CREATE USER 'app_planillero'@'%' IDENTIFIED BY 'plani123';

-- El planillero lee todo, pero solo escribe planillas, goles y tarjetas.
-- UPDATE en partido es para marcarlo como jugado al guardar la planilla.
-- Las sanciones automáticas las crean los triggers, que corren con permisos de root.
GRANT SELECT ON torneo_ucu.* TO 'app_planillero'@'%';
GRANT INSERT, UPDATE, DELETE ON torneo_ucu.planilla_partido TO 'app_planillero'@'%';
GRANT INSERT, UPDATE, DELETE ON torneo_ucu.gol TO 'app_planillero'@'%';
GRANT INSERT, UPDATE, DELETE ON torneo_ucu.tarjeta TO 'app_planillero'@'%';
GRANT UPDATE ON torneo_ucu.partido TO 'app_planillero'@'%';