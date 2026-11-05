"""Nivel 2 - Servidor del sistema de mensajeria.

Registra ServicioMensajes en el Name Server bajo el nombre
practica.mensajeria para que los clientes lo localicen sin conocer
su IP ni su puerto.
"""

import threading
from datetime import datetime

import Pyro4
import Pyro4.errors

NOMBRE_SERVICIO = "practica.mensajeria"


@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class ServicioMensajes(object):
    """Servicio remoto que guarda y comparte mensajes entre clientes.

    Se usa una sola instancia para todos los clientes, por eso la lista
    de mensajes se protege con un Lock ante accesos concurrentes.
    """

    def __init__(self):
        """Inicializa el estado interno y el Lock que lo protege."""
        self._mensajes = []
        self._lock = threading.Lock()

    def enviar_mensaje(self, usuario, contenido):
        """Guarda un mensaje con fecha y autor.

        Lanza ValueError si el contenido esta vacio.
        """
        if not isinstance(contenido, str) or not contenido.strip():
            raise ValueError("El mensaje no puede estar vacio.")

        fecha = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        mensaje = f"[{fecha}] {usuario}: {contenido.strip()}"

        with self._lock:
            self._mensajes.append(mensaje)

        print(f"Mensaje recibido: {mensaje}")
        return "Mensaje enviado correctamente."

    def recibir_mensajes(self):
        """Devuelve una copia del historial de mensajes."""
        with self._lock:
            return list(self._mensajes)


def main():
    """Crea el daemon, registra el servicio en el Name Server y lo atiende."""
    daemon = Pyro4.Daemon()
    uri = daemon.register(ServicioMensajes)

    with Pyro4.locateNS() as ns:
        ns.register(NOMBRE_SERVICIO, uri)

    print("Servidor de mensajeria iniciado.")
    print(f"URI: {uri}")
    print(f"Servicio registrado como: {NOMBRE_SERVICIO}")
    print("Esperando mensajes...")

    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        try:
            with Pyro4.locateNS() as ns:
                ns.remove(NOMBRE_SERVICIO)
        except Pyro4.errors.NamingError:
            pass
        daemon.close()


if __name__ == "__main__":
    main()
