"""Caso de estudio - Servidor central del sistema de subastas.

Publica ServicioSubasta en el Name Server como subastas.central. La
subasta inicia con un precio base y un tiempo limite; acepta ofertas
concurrentes de varios clientes sin condiciones de carrera y notifica
por callback a todos los clientes registrados cada vez que cambia el
precio mas alto y cuando la subasta finaliza.

Ejecucion (con el Name Server ya iniciado):
    python3 subasta_server.py --producto "Monitor Gamer" --precio-base 150
"""

import argparse
import queue
import threading
import time
from datetime import datetime

import Pyro4
import Pyro4.errors

from subasta_excepciones import (OfertaInvalida, SubastaCerrada,
                                 registrar_excepciones)

NOMBRE_SERVICIO = "subastas.central"
TIEMPO_ESPERA_CALLBACK = 3


@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class ServicioSubasta(object):
    """Subasta de un producto compartida por todos los clientes.

    Se usa una unica instancia para todos los clientes. Toda lectura o
    escritura del estado ocurre dentro de un Lock, de modo que la
    validacion de una oferta y su aceptacion son una sola operacion
    atomica aunque lleguen ofertas simultaneas desde distintos hilos.
    """

    def __init__(self, producto, descripcion, precio_base, duracion):
        """Configura la subasta e inicia el cronometro y el notificador."""
        self._lock = threading.Lock()
        self._producto = producto
        self._descripcion = descripcion
        self._precio_base = float(precio_base)
        self._precio_actual = float(precio_base)
        self._ganador = None
        self._historial = []
        self._clientes = {}
        self._abierta = True
        self._cierre = time.time() + duracion
        self._eventos = queue.Queue()

        threading.Thread(target=self._notificar_clientes,
                         daemon=True).start()
        cronometro = threading.Timer(duracion, self._finalizar)
        cronometro.daemon = True
        cronometro.start()

    @staticmethod
    def _validar_usuario(usuario):
        """Lanza OfertaInvalida si el usuario no es un texto no vacio."""
        if not isinstance(usuario, str) or not usuario.strip():
            raise OfertaInvalida("El nombre de usuario no puede estar vacio.")
        return usuario.strip()

    @staticmethod
    def _validar_monto(monto):
        """Lanza OfertaInvalida si el monto no es un numero positivo."""
        if isinstance(monto, bool) or not isinstance(monto, (int, float)):
            raise OfertaInvalida("El monto debe ser un numero.")
        if monto <= 0:
            raise OfertaInvalida("El monto debe ser mayor a 0.")
        return float(monto)

    def _segundos_restantes(self):
        """Devuelve los segundos que faltan para el cierre (minimo 0)."""
        return max(0, round(self._cierre - time.time()))

    def _estado_actual(self):
        """Arma el diccionario de estado; se llama con el Lock tomado."""
        return {
            "producto": self._producto,
            "descripcion": self._descripcion,
            "precio_base": self._precio_base,
            "precio_actual": self._precio_actual,
            "ganador": self._ganador,
            "abierta": self._abierta,
            "segundos_restantes": self._segundos_restantes(),
            "participantes": len(self._clientes),
        }

    def registrar_cliente(self, usuario, receptor):
        """Registra el callback de un cliente y devuelve el estado actual.

        receptor llega como un proxy hacia el objeto que el cliente
        publico en su propio daemon.
        """
        usuario = self._validar_usuario(usuario)
        receptor._pyroTimeout = TIEMPO_ESPERA_CALLBACK
        with self._lock:
            self._clientes[usuario] = receptor
            print(f"[servidor] {usuario} se unio a la subasta.")
            return self._estado_actual()

    def retirar_cliente(self, usuario):
        """Elimina el callback de un cliente que abandona la subasta."""
        with self._lock:
            if self._clientes.pop(usuario, None) is not None:
                print(f"[servidor] {usuario} salio de la subasta.")

    def ofertar(self, usuario, monto):
        """Valida y registra una oferta; devuelve el nuevo precio actual.

        Lanza SubastaCerrada si el tiempo termino y OfertaInvalida si los
        datos son erroneos o el monto no supera el precio actual.
        """
        usuario = self._validar_usuario(usuario)
        monto = self._validar_monto(monto)

        with self._lock:
            if not self._abierta:
                raise SubastaCerrada("La subasta ya finalizo.")
            if monto <= self._precio_actual:
                raise OfertaInvalida(
                    f"La oferta debe superar ${self._precio_actual:.2f}.")

            self._precio_actual = monto
            self._ganador = usuario
            hora = datetime.now().strftime("%H:%M:%S")
            self._historial.append((hora, usuario, monto))
            print(f"[servidor] {hora} nueva oferta de {usuario}: "
                  f"${monto:.2f}")
            self._eventos.put(("nuevo_precio", usuario, monto))
            return self._precio_actual

    def obtener_estado(self):
        """Devuelve el estado actual de la subasta."""
        with self._lock:
            return self._estado_actual()

    def obtener_historial(self):
        """Devuelve las ofertas aceptadas como (hora, usuario, monto)."""
        with self._lock:
            return list(self._historial)

    def _finalizar(self):
        """Cierra la subasta al cumplirse el tiempo y avisa a los clientes."""
        with self._lock:
            self._abierta = False
            ganador, precio = self._ganador, self._precio_actual
        if ganador:
            print(f"[servidor] Subasta finalizada. Ganador: {ganador} "
                  f"con ${precio:.2f}")
        else:
            print("[servidor] Subasta finalizada sin ofertas.")
        self._eventos.put(("subasta_finalizada", ganador, precio))

    def _notificar_clientes(self):
        """Entrega los eventos de la cola a todos los clientes, en orden.

        Un solo hilo envia las notificaciones, asi el cliente que oferta
        no espera a que se avise a los demas y los avisos llegan en el
        mismo orden en que se aceptaron las ofertas. Los clientes que no
        responden se eliminan para no degradar el servicio.
        """
        while True:
            metodo, usuario, monto = self._eventos.get()
            with self._lock:
                destinatarios = list(self._clientes.items())

            for nombre, receptor in destinatarios:
                try:
                    getattr(receptor, metodo)(usuario, monto)
                except Pyro4.errors.CommunicationError:
                    print(f"[servidor] {nombre} no responde; se elimina.")
                    self.retirar_cliente(nombre)


def leer_argumentos():
    """Lee los parametros de la subasta desde la linea de comandos."""
    parser = argparse.ArgumentParser(description="Servidor de subastas")
    parser.add_argument("--producto", default="Monitor Gamer")
    parser.add_argument("--descripcion", default="Usado, 27 pulgadas")
    parser.add_argument("--precio-base", type=float, default=150.0)
    parser.add_argument("--duracion", type=int, default=120,
                        help="tiempo limite en segundos")
    parser.add_argument("--host", default="localhost")
    return parser.parse_args()


def main():
    """Crea la subasta, la registra en el Name Server y atiende ofertas."""
    args = leer_argumentos()
    registrar_excepciones()

    subasta = ServicioSubasta(args.producto, args.descripcion,
                              args.precio_base, args.duracion)
    daemon = Pyro4.Daemon(host=args.host)
    uri = daemon.register(subasta)

    with Pyro4.locateNS() as ns:
        ns.register(NOMBRE_SERVICIO, uri)

    print("Servidor de subastas iniciado.")
    print(f"Servicio registrado como: {NOMBRE_SERVICIO}")
    print(f"Producto: {args.producto} | Precio base: ${args.precio_base:.2f}"
          f" | Duracion: {args.duracion} s")

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
