#!/usr/bin/env python3
"""
Nivel 4 - Cliente: Procesamiento Concurrente y Callback Asincrono (Pyro4).

Demuestra tres escenarios contra el servicio ``practica.procesador``:

1. Linea base sincrona: una llamada normal bloquea al cliente.
2. Llamadas asincronas con ``Pyro4.asyncproxy`` + futures:
   se lanzan varios trabajos a la vez, el cliente sigue con otras tareas
   y luego recupera los resultados con ``future.value``. Tambien se usa
   ``future.then()`` para encadenar una accion al terminar, y se muestra
   como una excepcion remota llega a traves del future.
3. Callback de servidor a cliente: el cliente publica su propio objeto
   ``ReceptorResultados`` en un daemon local, llama a un metodo oneway y
   el servidor le avisa cuando termina.

Ejecucion (con el Name Server y el servidor ya iniciados):
    python3 nivel4_cliente.py
"""

import argparse
import threading
import time

import Pyro4
import Pyro4.errors

NOMBRE_SERVICIO = "PYRONAME:practica.procesador"

# Trabajos de ejemplo: (identificador, limite hasta donde contar primos).
TRABAJOS = [("T1", 600_000), ("T2", 900_000), ("T3", 1_200_000)]


def otra_tarea_local(paso):
    """Simula trabajo util que el cliente hace mientras espera."""
    time.sleep(0.5)
    print("    [cliente] ...haciendo otra tarea local (paso {})".format(paso))


def mostrar(resultado):
    """Imprime un resultado devuelto por el servidor."""
    print("    [resultado] {trabajo_id}: {primos:,} primos hasta {limite:,} "
          "en {segundos}s (hilo {hilo_servidor})".format(**resultado))


def avisar_t3(resultado):
    """Accion encadenada con future.then(); devuelve el valor recibido."""
    print("    [then] T3 listo, aviso inmediato: {:,} primos".format(
        resultado["primos"]))
    return resultado


# ----------------------------------------------------------------------
# Escenario 1: llamada sincrona (para comparar)
# ----------------------------------------------------------------------
def demo_sincrona(uri):
    """Una llamada normal: el cliente queda bloqueado hasta la respuesta."""
    print("\n=== 1) Llamada SINCRONA (bloqueante) ===")
    with Pyro4.Proxy(uri) as servicio:
        inicio = time.perf_counter()
        resultado = servicio.procesar("S1", TRABAJOS[0][1])
        mostrar(resultado)
        print("    El cliente estuvo bloqueado {:.2f}s sin hacer nada.".format(
            time.perf_counter() - inicio))


# ----------------------------------------------------------------------
# Escenario 2: asyncproxy + futures
# ----------------------------------------------------------------------
def demo_asincrona(uri):
    """Lanza varios trabajos en paralelo y los recupera con futures."""
    print("\n=== 2) Llamadas ASINCRONAS con Pyro4.asyncproxy + futures ===")
    servicio = Pyro4.Proxy(uri)
    # Pone el proxy en modo asincrono. En Pyro4 4.x la funcion modifica el
    # proxy en el lugar y devuelve None, por eso no se reasigna.
    Pyro4.asyncproxy(servicio)

    inicio = time.perf_counter()

    # Cada llamada vuelve AL INSTANTE con un FutureResult. Internamente
    # Pyro4 usa un hilo y una copia del proxy por llamada, por eso los
    # trabajos se procesan en paralelo en el servidor.
    futuros = {}
    for trabajo_id, limite in TRABAJOS:
        futuros[trabajo_id] = servicio.procesar(trabajo_id, limite)
        print("    [cliente] {} enviado (sin esperar)".format(trabajo_id))

    # then(): encadena una funcion que se ejecuta apenas llega el resultado.
    # Su valor de retorno pasa a ser el nuevo valor del future, por eso
    # avisar_t3() devuelve el resultado intacto.
    futuros["T3"].then(avisar_t3)

    # Mientras el servidor trabaja, el cliente sigue con lo suyo.
    paso = 1
    while not all(f.ready for f in futuros.values()):
        otra_tarea_local(paso)
        listos = [t for t, f in futuros.items() if f.ready]
        print("    [cliente] listos hasta ahora: {}".format(
            listos or "ninguno"))
        paso += 1

    # .value devuelve el resultado (o relanza la excepcion remota).
    for trabajo_id in futuros:
        mostrar(futuros[trabajo_id].value)
    print("    Tiempo total con los 3 trabajos concurrentes: {:.2f}s".format(
        time.perf_counter() - inicio))

    # Manejo de errores: la excepcion del servidor viaja dentro del future.
    print("\n    Probando un trabajo invalido (limite negativo)...")
    futuro_malo = servicio.procesar("TX", -5)
    try:
        futuro_malo.value
    except ValueError as error:
        print("    [cliente] El servidor rechazo el trabajo: {}".format(error))

    servicio._pyroRelease()


# ----------------------------------------------------------------------
# Escenario 3: callback de servidor a cliente
# ----------------------------------------------------------------------
class ReceptorResultados(object):
    """Objeto del cliente que el servidor invoca al terminar un trabajo.

    El cliente actua tambien como servidor: este objeto se registra en un
    daemon local y su proxy se envia al servidor como argumento.
    """

    def __init__(self, pendientes):
        self._lock = threading.Lock()
        self._pendientes = set(pendientes)
        self.todos_listos = threading.Event()

    def _marcar(self, trabajo_id):
        """Marca un trabajo como recibido y avisa si ya no quedan."""
        with self._lock:
            self._pendientes.discard(trabajo_id)
            if not self._pendientes:
                self.todos_listos.set()

    @Pyro4.expose
    @Pyro4.callback
    def trabajo_terminado(self, resultado):
        """Llamado por el servidor con el resultado de un trabajo."""
        print("    [callback] El servidor aviso que termino {}".format(
            resultado["trabajo_id"]))
        mostrar(resultado)
        self._marcar(resultado["trabajo_id"])

    @Pyro4.expose
    @Pyro4.callback
    def trabajo_fallido(self, trabajo_id, mensaje):
        """Llamado por el servidor si el trabajo no se pudo completar."""
        print("    [callback] {} fallo en el servidor: {}".format(
            trabajo_id, mensaje))
        self._marcar(trabajo_id)


def demo_callback(uri, host):
    """Envia trabajos oneway y espera los avisos del servidor."""
    print("\n=== 3) CALLBACK: el servidor llama de vuelta al cliente ===")
    trabajos = TRABAJOS[:2] + [("TX", 0)]  # TX es invalido a proposito
    receptor = ReceptorResultados(t for t, _ in trabajos)

    # Daemon propio del cliente, atendido en un hilo de fondo.
    daemon = Pyro4.Daemon(host=host)
    daemon.register(receptor)
    hilo_daemon = threading.Thread(target=daemon.requestLoop, daemon=True)
    hilo_daemon.start()

    with Pyro4.Proxy(uri) as servicio:
        for trabajo_id, limite in trabajos:
            # oneway: vuelve inmediatamente. Al pasar ``receptor`` (objeto
            # registrado en un daemon) Pyro4 lo convierte en un proxy.
            servicio.procesar_con_callback(trabajo_id, limite, receptor)
            print("    [cliente] {} enviado con callback".format(trabajo_id))

    # El cliente sigue trabajando hasta que lleguen todos los avisos.
    paso = 1
    while not receptor.todos_listos.wait(timeout=0.01):
        otra_tarea_local(paso)
        paso += 1
        if paso > 120:  # proteccion: no esperar para siempre (~60 s)
            print("    [cliente] Tiempo de espera agotado.")
            break

    daemon.shutdown()
    hilo_daemon.join(timeout=2)
    daemon.close()


def main():
    """Ejecuta los tres escenarios en orden."""
    parser = argparse.ArgumentParser(description="Cliente Nivel 4 (Pyro4)")
    parser.add_argument("--host", default="localhost",
                        help="IP del cliente para recibir callbacks")
    args = parser.parse_args()

    try:
        demo_sincrona(NOMBRE_SERVICIO)
        demo_asincrona(NOMBRE_SERVICIO)
        demo_callback(NOMBRE_SERVICIO, args.host)
        with Pyro4.Proxy(NOMBRE_SERVICIO) as servicio:
            print("\nEstado del servidor: {}".format(servicio.estado()))
    except Pyro4.errors.NamingError:
        print("No se encontro el Name Server o el servicio. "
              "Inicie primero 'python3 -m Pyro4.naming' y el servidor.")
    except Pyro4.errors.CommunicationError as error:
        print("Error de comunicacion con el servidor: {}".format(error))


if __name__ == "__main__":
    main()
