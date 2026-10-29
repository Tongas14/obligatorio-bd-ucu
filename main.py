from fastapi import FastAPI
import mysql.connector
import os

app = FastAPI(title="API Torneo Interfacultades UCU")

# Configuración de conexión a MySQL mediante sentencias SQL puras
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        user=os.getenv("DB_USER", "torneo_admin"),
        password=os.getenv("DB_PASSWORD", "admin123"),
        database=os.getenv("DB_NAME", "torneo_ucu")
    )

@app.get("/")
def read_root():
    return {"mensaje": "Servidor del Torneo corriendo correctamente"}

@app.get("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        conn.close()
        return {"status": "Conexión exitosa", "database": db_name[0]}
    except Exception as e:
        return {"status": "Error de conexión", "error": str(e)}