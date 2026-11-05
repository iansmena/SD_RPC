"""Caso de estudio - Cliente del sistema de subastas.

Localiza subastas.central en el Name Server, publica un objeto
ReceptorSubasta en su propio daemon para recibir callbacks del servidor
y permite ofertar, consultar el estado y ver el historial.

Ejecucion (con el Name Server y el servidor ya iniciados):
    python3 subasta_client.py
"""

import argparse
import threading

import Pyro4
import Pyro4.errors

from subasta_excepciones import (OfertaInvalida, SubastaCerrada,
                                 registrar_excepciones)

NOMBRE_SERVICIO = "PYRONAME:subastas.central"


class ReceptorSubasta(object):
    """Objeto del cliente que el servidor invoca cuando hay novedades."""

    def __init__(self, usuario):
        """Guarda el nombre del usuario y prepara el aviso de cierre."""
        self._usuario = usuario
        self.finalizada = threading.Event()

    @Pyro4.expose
    @Pyro4.callback
    def nuevo_precio(self, usuario, monto):
        """Muestra el nuevo precio mas alto enviado por el servidor."""
        quien = "Tu oferta" if usuario == self._usuario else usuario
        print(f"\n  [AVISO] {quien} lidera con ${monto:.2f}")

    @Pyro4.expose
    @Pyro4.callback
    def subasta_finalizada(self, ganador, monto):
        """Muestra el resultado final y marca la subasta como cerrada."""
        if ganador is None:
            print("\n  [AVISO] La subasta termino sin ofertas.")
        elif ganador == self._usuario:
            print(f"\n  [AVISO] Ganaste la subasta con ${monto:.2f}")
        else:
            print(f"\n  [AVISO] Subasta finalizada. Gano {ganador} "
                  f"con ${monto:.2f}")
        print("  Presiona Enter para salir.")
        self.finalizada.set()


def leer_nombre():
    """Pide el nombre del usuario hasta que no este vacio."""
    while True:
        nombre = input("Ingresa tu nombre: ").strip()
        if nombre:
            return nombre
        print("Nombre invalido.")


def mostrar_estado(estado):
    """Imprime el estado de la subasta recibido del servidor."""
    lider = estado["ganador"] or "sin ofertas"
    print(f"\nProducto: {estado['producto']} ({estado['descripcion']})")
    print(f"Precio base: ${estado['precio_base']:.2f}")
    print(f"Precio actual: ${estado['precio_actual']:.2f} | Lider: {lider}")
    print(f"Tiempo restante: {estado['segundos_restantes']} s | "
          f"Participantes: {estado['participantes']}")


def mostrar_historial(historial):
    """Imprime las ofertas aceptadas por el servidor."""
    print("\n--- HISTORIAL DE OFERTAS ---")
    if not historial:
        print("Todavia no hay ofertas.")
    for hora, usuario, monto in historial:
        print(f"[{hora}] {usuario}: ${monto:.2f}")


def ofertar(subasta, usuario):
    """Pide un monto, lo envia y muestra si el servidor lo rechaza."""
    texto = input("Monto de tu oferta: ").strip()
    try:
        monto = float(texto)
    except ValueError:
        print("Ingresa un valor numerico valido.")
        return
    try:
        precio = subasta.ofertar(usuario, monto)
        print(f"Oferta aceptada. Precio actual: ${precio:.2f}")
    except (OfertaInvalida, SubastaCerrada) as error:
        print(f"Oferta rechazada: {error}")


def mostrar_menu():
    """Imprime el menu de opciones."""
    print("\n===== SISTEMA DE SUBASTAS =====")
    print("1. Ofertar")
    print("2. Ver estado")
    print("3. Ver historial")
    print("4. Salir")


def iniciar_receptor(usuario, host):
    """Publica el receptor en un daemon local atendido en segundo plano."""
    receptor = ReceptorSubasta(usuario)
    daemon = Pyro4.Daemon(host=host)
    daemon.register(receptor)
    threading.Thread(target=daemon.requestLoop, daemon=True).start()
    return receptor, daemon


def ejecutar_menu(subasta, usuario, receptor):
    """Atiende el menu hasta que el usuario salga o cierre la subasta."""
    while not receptor.finalizada.is_set():
        mostrar_menu()
        opcion = input("Selecciona una opcion: ").strip()
        if receptor.finalizada.is_set():
            break
        if opcion == "1":
            ofertar(subasta, usuario)
        elif opcion == "2":
            mostrar_estado(subasta.obtener_estado())
        elif opcion == "3":
            mostrar_historial(subasta.obtener_historial())
        elif opcion == "4":
            break
        else:
            print("Opcion no valida.")


def main():
    """Se une a la subasta, recibe avisos y ejecuta el menu."""
    parser = argparse.ArgumentParser(description="Cliente de subastas")
    parser.add_argument("--host", default="localhost",
                        help="IP del cliente para recibir callbacks")
    args = parser.parse_args()

    registrar_excepciones()
    usuario = leer_nombre()
    receptor, daemon = iniciar_receptor(usuario, args.host)

    try:
        with Pyro4.Proxy(NOMBRE_SERVICIO) as subasta:
            mostrar_estado(subasta.registrar_cliente(usuario, receptor))
            try:
                ejecutar_menu(subasta, usuario, receptor)
            finally:
                subasta.retirar_cliente(usuario)
        print("Desconectando...")
    except OfertaInvalida as error:
        print(f"Error: {error}")
    except Pyro4.errors.NamingError:
        print("No se encontro el Name Server o el servicio.")
    except Pyro4.errors.PyroError as error:
        print(f"Error de comunicacion con Pyro4: {error}")
    finally:
        daemon.shutdown()


if __name__ == "__main__":
    main()
