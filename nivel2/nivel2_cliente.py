"""Nivel 2 - Cliente del sistema de mensajeria.

Localiza el servicio practica.mensajeria con Pyro4.locateNS() y
permite enviar y consultar mensajes.
"""

import Pyro4
import Pyro4.errors

NOMBRE_SERVICIO = "practica.mensajeria"


def mostrar_menu():
    """Imprime el menu de opciones."""
    print("\n===== SISTEMA DE MENSAJERIA =====")
    print("1. Enviar mensaje")
    print("2. Recibir mensajes")
    print("3. Salir")


def enviar(servicio, usuario):
    """Pide un mensaje y lo envia al servidor."""
    mensaje = input("Escribe tu mensaje: ")
    try:
        print(servicio.enviar_mensaje(usuario, mensaje))
    except ValueError as error:
        print(f"Error: {error}")


def recibir(servicio):
    """Obtiene el historial del servidor y lo imprime."""
    mensajes = servicio.recibir_mensajes()
    print("\n--- HISTORIAL DE MENSAJES ---")
    if not mensajes:
        print("No hay mensajes disponibles.")
    for mensaje in mensajes:
        print(mensaje)


def main():
    """Localiza el servicio en el Name Server y ejecuta el menu."""
    try:
        with Pyro4.locateNS() as ns:
            uri = ns.lookup(NOMBRE_SERVICIO)

        with Pyro4.Proxy(uri) as servicio:
            usuario = input("Ingresa tu nombre: ").strip() or "Anonimo"

            while True:
                mostrar_menu()
                opcion = input("Selecciona una opcion: ").strip()

                if opcion == "1":
                    enviar(servicio, usuario)
                elif opcion == "2":
                    recibir(servicio)
                elif opcion == "3":
                    print("Desconectando...")
                    break
                else:
                    print("Opcion no valida.")

    except Pyro4.errors.NamingError:
        print("No se encontro el Name Server o el servicio.")
    except Pyro4.errors.PyroError as error:
        print(f"Error de comunicacion con Pyro4: {error}")


if __name__ == "__main__":
    main()
