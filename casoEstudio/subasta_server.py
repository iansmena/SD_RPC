import Pyro4

import time 

from datetime import datetime


@Pyro4.expose

class ServicioSubasta:
    def __init__(self):
        self.producto=1
    def mostrarProduc(self):
        productos=("Monitor Gamer", "Usado", 150.00)
        return productos
    def pujar(self,monto):
        valorI=150.00
        if monto<=valorI:
            print("No vale")
        elif monto>valorI+10:
            valorI = monto
            return "El nuevo valor es {0}".format(valorI)
    def cronometro(self, name):
        for segundo in range (10,-1):
            time.sleep(1)
        return "{0} ganó la subasta".format(name)
    
if __name__ == "__main__":
    daemon = Pyro4.Daemon()


    ns = Pyro4.locateNS()


    servicio = ServicioSubasta()
    uri = daemon.register(servicio)
    ns.register("subastas.central",uri)
    print("Servidor de subasta iniciado.")
    print(f"URI: {uri}")
    print("Servicio registrado como: subastas.central")
    print("Esperando pujas...")

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

