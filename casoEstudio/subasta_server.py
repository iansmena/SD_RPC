import Pyro4
from datetime import datetime


@Pyro4.expose
class ServicioMensajes:
    def __init__(self):
        self.mensajes = []

    def verProductos(self):
        return list(self.mensajes)
    
    def pujar(self, usuario, contenido):
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

    ns.register("subastas.central", uri)

    print("Servidor de subastas iniciado.")
    print(f"URI: {uri}")
    print("Servicio registrado como: subastas.central")
    print("Esperando...")


    daemon.requestLoop()
