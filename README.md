# Torneo Interfacultades de Fútbol 5 - UCU

Sistema para gestionar el torneo: equipos, partidos, planillas, sanciones y reportes.
Backend en Python (FastAPI, sin ORM), base de datos MySQL 8 y pantallas en HTML.

## Cómo correrlo con Docker (recomendado)

Requisito: tener Docker Desktop instalado y abierto.

1. Clonar el repositorio y entrar a la carpeta.
2. Levantar los servicios:

   ```bash
   docker compose up -d --build
   ```

3. La primera vez MySQL ejecuta `base_de_datos/esquema.sql` (estructura, datos de prueba,
   triggers y usuarios). Tarda unos segundos; se puede seguir con:

   ```bash
   docker compose logs -f db
   ```

   Está listo cuando aparece "MySQL init process done" y después "ready for connections"
   con "port: 3306" (antes aparecen otros "ready for connections" del arranque inicial).
4. Abrir http://localhost:8000 e ingresar con un usuario de la tabla `login`.

Servicios:

| Servicio | Dirección | Detalle |
|---|---|---|
| App | http://localhost:8000 | Pantallas y API |
| API documentada | http://localhost:8000/docs | Swagger de FastAPI |
| MySQL | localhost:3307 | root / root123, base `torneo_ucu` |

Para apagar:

```bash
docker compose down
```

El script SQL solo corre cuando la base está vacía. Para volver a crearla desde cero
(se pierden los datos cargados):

```bash
docker compose down -v
docker compose up -d --build
```

## Cómo correrlo sin Docker

Todos los comandos se ejecutan desde la carpeta raíz del repositorio.

1. Tener MySQL 8 corriendo y el cliente `mysql` en el PATH. Crear la base y ejecutar el
   script con root (se usa `source` porque funciona igual en PowerShell, cmd y bash):

   ```bash
   mysql -u root -p -e "CREATE DATABASE torneo_ucu"
   mysql -u root -p torneo_ucu -e "source base_de_datos/esquema.sql"
   ```

2. Instalar las dependencias de Python (3.10 o superior):

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Indicar dónde está la base y levantar la app. En PowerShell:

   ```powershell
   $env:DB_HOST = "127.0.0.1"; $env:DB_PORT = "3306"; python -m uvicorn main:app --port 8000
   ```

   En Linux o macOS:

   ```bash
   DB_HOST=127.0.0.1 DB_PORT=3306 python -m uvicorn main:app --port 8000
   ```

4. Abrir http://localhost:8000.

La app usa la hora de MySQL para las reglas de horarios (partido jugado, 48 horas), así que
la base tiene que estar en la zona horaria de Uruguay. En Docker eso ya está configurado
con `TZ=America/Montevideo`.

## Usuarios y permisos

Para ingresar a la app tiene que haber al menos un usuario en la tabla `login`
(correo, contraseña y rol `administrador` o `planillero`).

La app se conecta a MySQL con un usuario distinto según el rol de quien inició sesión:

| Rol | Usuario MySQL | Permisos |
|---|---|---|
| administrador | app_admin | Todo sobre `torneo_ucu` |
| planillero | app_planillero | SELECT, INSERT, UPDATE; DELETE solo en planilla, goles y tarjetas |

El planillero solo puede entrar a la pantalla de planillas (http://localhost:8000/planillero).

## Pantallas

- `/login`: ingreso.
- `/admin/partidos`: ABM de partidos.
- `/planillero`: planilla, goles y tarjetas de cada partido.
- `/admin/sanciones`: sanciones disciplinarias (las de roja y amarillas son automáticas).
- `/admin/consultas`: suspendidos por fecha, partidos con más tarjetas y planillas pendientes.

## Estructura

```
base_de_datos/esquema.sql   estructura, datos de prueba, triggers y usuarios de MySQL
main.py                     app FastAPI, login y ABM de jugadores, torneos, equipos, etc.
comun.py                    conexión a la base por rol y sesión
partidos.py                 ABM de partidos
planillas.py                planillas, goles y tarjetas
sanciones.py                sanciones disciplinarias
consultas.py                consultas propias
paginas.py                  rutas de las pantallas con control de rol
static/                     HTML, CSS y JS de las pantallas
```
