import socket
import threading
import json
import sqlite3
import os
import time
from concurrent.futures import ThreadPoolExecutor
from werkzeug.security import generate_password_hash, check_password_hash

HOST = "127.0.0.1"
PUERTO = 5000
CANTIDAD_WORKERS = 4

# la base se guarda en la misma carpeta que este archivo
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tareas.db")

# pool de hilos: los workers que procesan las tareas
pool = ThreadPoolExecutor(max_workers=CANTIDAD_WORKERS, thread_name_prefix="worker")


def crear_tabla():
    conexion = sqlite3.connect(DB)
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL
        )
    """)
    conexion.commit()
    conexion.close()


# ---------------- tareas que ejecutan los workers ----------------

def registro(datos):
    usuario = datos.get("usuario")
    contrasena = datos.get("contraseña")
    if not usuario or not contrasena:
        return "Faltan datos"

    # se guarda el hash, nunca la contraseña en texto plano
    try:
        conexion = sqlite3.connect(DB)
        conexion.execute("INSERT INTO usuarios (usuario, contrasena) VALUES (?, ?)",
                         (usuario, generate_password_hash(contrasena)))
        conexion.commit()
        conexion.close()
    except sqlite3.IntegrityError:
        return "El usuario ya existe"
    return "Usuario registrado correctamente"


def login(datos):
    conexion = sqlite3.connect(DB)
    fila = conexion.execute("SELECT contrasena FROM usuarios WHERE usuario = ?",
                            (datos.get("usuario"),)).fetchone()
    conexion.close()

    # compara la contraseña ingresada con el hash guardado
    if fila and check_password_hash(fila[0], datos.get("contraseña", "")):
        return "Login exitoso"
    return "Usuario o contraseña incorrectos"


def sumar(datos):
    return sum(datos.get("numeros", []))


def contar_palabras(datos):
    return len(datos.get("texto", "").split())


def mayusculas(datos):
    return datos.get("texto", "").upper()


def tarea_lenta(datos):
    # simula una tarea pesada para ver que los workers trabajan en paralelo
    segundos = datos.get("segundos", 3)
    time.sleep(segundos)
    return f"Terminé después de {segundos} segundos"


TAREAS = {
    "registro": registro,
    "login": login,
    "sumar": sumar,
    "contar_palabras": contar_palabras,
    "mayusculas": mayusculas,
    "tarea_lenta": tarea_lenta,
}


def ejecutar_tarea(mensaje):
    # esto corre dentro de un hilo del pool
    nombre = mensaje.get("tarea")
    worker = threading.current_thread().name
    print(f"[{worker}] procesando tarea '{nombre}'")

    if nombre not in TAREAS:
        return {"estado": "error", "resultado": f"Tarea desconocida: {nombre}", "worker": worker}
    try:
        resultado = TAREAS[nombre](mensaje.get("datos", {}))
        return {"estado": "ok", "resultado": resultado, "worker": worker}
    except Exception as error:
        return {"estado": "error", "resultado": str(error), "worker": worker}


# ---------------- atención de clientes por socket ----------------

def atender_cliente(conexion, direccion):
    print(f"Cliente conectado: {direccion}")
    # cada mensaje es un JSON terminado en salto de línea
    archivo = conexion.makefile("r", encoding="utf-8")
    try:
        for linea in archivo:
            try:
                mensaje = json.loads(linea)
            except json.JSONDecodeError:
                respuesta = {"estado": "error", "resultado": "Mensaje inválido"}
            else:
                # se entrega la tarea al pool y se espera el resultado
                futuro = pool.submit(ejecutar_tarea, mensaje)
                respuesta = futuro.result()
            conexion.sendall((json.dumps(respuesta, ensure_ascii=False) + "\n").encode("utf-8"))
    except (ConnectionResetError, ConnectionAbortedError):
        pass
    finally:
        conexion.close()
        print(f"Cliente desconectado: {direccion}")


def main():
    crear_tabla()
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PUERTO))
    servidor.listen()
    print(f"Servidor escuchando en {HOST}:{PUERTO} con {CANTIDAD_WORKERS} workers")

    try:
        while True:
            conexion, direccion = servidor.accept()
            # un hilo por cliente para recibir; el trabajo lo hacen los workers del pool
            threading.Thread(target=atender_cliente, args=(conexion, direccion), daemon=True).start()
    except KeyboardInterrupt:
        print("\nApagando servidor")
    finally:
        servidor.close()
        pool.shutdown()


if __name__ == "__main__":
    main()
