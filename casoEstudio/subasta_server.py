import Pyro4
from datetime import datetime


@Pyro4.expose
class ServicioMensajes:
    def __init__(self):
        self.mensajes = []

    def enviar_mensaje(self, usuario, contenido):
        if not contenido.strip():
            return "Error: El mensaje no puede estar vacio."

        fecha = datetime.now()
        mensaje = f"[{fecha}] {usuario}: {contenido}"

        self.mensajes.append(mensaje)
        print(f"Mensaje recibido: {mensaje}")

        return "Mensaje enviado correctamente."

    def recibir_mensajes(self):
        # Devuelve una copia de los mensajes almacenados
        return list(self.mensajes)


if __name__ == "__main__":
    daemon = Pyro4.Daemon()


    ns = Pyro4.locateNS()


    servicio = ServicioMensajes()
    uri = daemon.register(servicio)


    ns.register("practica.mensajeria", uri)

    print("Servidor de mensajeria iniciado.")
    print(f"URI: {uri}")
    print("Servicio registrado como: practica.mensajeria")
    print("Esperando mensajes...")


    daemon.requestLoop()
