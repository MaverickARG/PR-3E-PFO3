import socket
import json

HOST = "127.0.0.1"
PUERTO = 5000


def enviar_tarea(conexion, archivo, tarea, datos):
    # se envía la tarea como JSON terminado en salto de línea
    mensaje = {"tarea": tarea, "datos": datos}
    conexion.sendall((json.dumps(mensaje, ensure_ascii=False) + "\n").encode("utf-8"))

    # se espera la respuesta del servidor
    respuesta = json.loads(archivo.readline())
    print(f"[{respuesta['estado']}] {respuesta['resultado']} (atendido por {respuesta.get('worker', '-')})")


def pedir_usuario():
    usuario = input("Usuario: ")
    contrasena = input("Contraseña: ")
    return {"usuario": usuario, "contraseña": contrasena}


def pedir_numeros():
    texto = input("Números separados por espacio: ")
    try:
        return {"numeros": [float(n) for n in texto.split()]}
    except ValueError:
        print("Solo se pueden ingresar números")
        return None


def main():
    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        conexion.connect((HOST, PUERTO))
    except ConnectionRefusedError:
        print("No se pudo conectar. ¿Está corriendo el servidor?")
        return
    archivo = conexion.makefile("r", encoding="utf-8")
    print(f"Conectado a {HOST}:{PUERTO}")

    while True:
        print("\n1. Registrarse\n2. Iniciar sesión\n3. Sumar números\n4. Contar palabras"
              "\n5. Pasar a mayúsculas\n6. Tarea lenta\n7. Salir")
        opcion = input("Seleccione una opción: ")
        print()

        if opcion == "1":
            enviar_tarea(conexion, archivo, "registro", pedir_usuario())
        elif opcion == "2":
            enviar_tarea(conexion, archivo, "login", pedir_usuario())
        elif opcion == "3":
            datos = pedir_numeros()
            if datos:
                enviar_tarea(conexion, archivo, "sumar", datos)
        elif opcion == "4":
            enviar_tarea(conexion, archivo, "contar_palabras", {"texto": input("Texto: ")})
        elif opcion == "5":
            enviar_tarea(conexion, archivo, "mayusculas", {"texto": input("Texto: ")})
        elif opcion == "6":
            enviar_tarea(conexion, archivo, "tarea_lenta", {"segundos": 3})
        elif opcion == "7":
            break
        else:
            print("Opción inválida")

    conexion.close()


if __name__ == "__main__":
    main()
