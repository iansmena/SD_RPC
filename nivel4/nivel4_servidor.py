#!/usr/bin/env python3
"""
Nivel 4 - Servidor: Procesamiento Concurrente y Callback Asincrono (Pyro4).

Expone el servicio remoto ``ProcesadorDatos`` y lo registra en el Name Server
bajo el nombre ``practica.procesador``.

El servicio simula una tarea pesada real (contar numeros primos hasta un
limite usando division por tentativa) y ofrece dos formas de usarla:

1. ``procesar(trabajo_id, limite)``
   Llamada normal que devuelve el resultado. El cliente la invoca mediante
   ``Pyro4.asyncproxy`` para no bloquearse y recupera el valor con un
   *future* (``FutureResult``).

2. ``procesar_con_callback(trabajo_id, limite, receptor)``
   Llamada ``@Pyro4.oneway``: el servidor responde de inmediato y, al
   terminar el trabajo, invoca ``receptor.trabajo_terminado(resultado)``
   en el cliente (callback de servidor a cliente).

Ejecucion (con el Name Server ya iniciado):
    python3 nivel4_servidor.py
"""

import argparse
import math
import threading
import time

import Pyro4
import Pyro4.errors

# Nombre logico con el que el servicio se publica en el Name Server.
NOMBRE_SERVICIO = "practica.procesador"

# Limites para validar la entrada y no degradar el servidor.
LIMITE_MINIMO = 2
LIMITE_MAXIMO = 5_000_000


def es_primo(numero):
    """Devuelve True si ``numero`` es primo (division por tentativa).

    Es intencionalmente costoso en CPU para simular una tarea pesada.
    """
    if numero < 2:
        return False
    if numero % 2 == 0:
        return numero == 2
    # Solo se prueban divisores impares hasta la raiz cuadrada.
    for divisor in range(3, math.isqrt(numero) + 1, 2):
        if numero % divisor == 0:
            return False
    return True


@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class ProcesadorDatos(object):
    """Servicio remoto de procesamiento intensivo de datos.

    Se usa ``instance_mode="single"``: una unica instancia atiende a todos
    los clientes. Por eso el estado compartido (contador de trabajos) se
    protege con un ``threading.Lock``, ya que el servidor de Pyro4 atiende
    cada llamada en un hilo distinto de su pool.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._trabajos_completados = 0
        self._trabajos_en_curso = 0

    # ------------------------------------------------------------------
    # Logica interna (no se expone porque empieza con guion bajo)
    # ------------------------------------------------------------------
    def _validar(self, trabajo_id, limite):
        """Valida los parametros; lanza ValueError con un mensaje claro."""
        if not isinstance(trabajo_id, str) or not trabajo_id.strip():
            raise ValueError("trabajo_id debe ser un texto no vacio")
        # bool es subclase de int, por eso se excluye explicitamente.
        if not isinstance(limite, int) or isinstance(limite, bool):
            raise ValueError("limite debe ser un numero entero")
        if not LIMITE_MINIMO <= limite <= LIMITE_MAXIMO:
            raise ValueError(
                "limite fuera de rango [{}, {}]".format(LIMITE_MINIMO,
                                                        LIMITE_MAXIMO))

    def _ejecutar(self, trabajo_id, limite):
        """Realiza el trabajo pesado y devuelve un diccionario serializable."""
        self._validar(trabajo_id, limite)
        hilo = threading.current_thread().name

        with self._lock:
            self._trabajos_en_curso += 1
        print("[servidor] INICIO  {:<8} limite={:<9,} hilo={}".format(
            trabajo_id, limite, hilo))

        inicio = time.perf_counter()
        try:
            total_primos = sum(1 for n in range(limite + 1) if es_primo(n))
        finally:
            # El contador se ajusta aunque el calculo falle.
            with self._lock:
                self._trabajos_en_curso -= 1
        duracion = time.perf_counter() - inicio

        with self._lock:
            self._trabajos_completados += 1

        print("[servidor] FIN     {:<8} primos={:<8,} {:.2f}s".format(
            trabajo_id, total_primos, duracion))

        # Solo tipos simples: el serializador por defecto (serpent) los
        # transmite sin problemas.
        return {
            "trabajo_id": trabajo_id,
            "limite": limite,
            "primos": total_primos,
            "segundos": round(duracion, 3),
            "hilo_servidor": hilo,
        }

    # ------------------------------------------------------------------
    # Metodos remotos
    # ------------------------------------------------------------------
    def procesar(self, trabajo_id, limite):
        """Procesa el trabajo y devuelve el resultado.

        Desde el servidor es una llamada normal; la asincronia la decide el
        cliente al envolver su proxy con ``Pyro4.asyncproxy``.
        """
        return self._ejecutar(trabajo_id, limite)

    @Pyro4.oneway
    def procesar_con_callback(self, trabajo_id, limite, receptor):
        """Procesa el trabajo y notifica el resultado mediante un callback.

        ``@Pyro4.oneway`` hace que el cliente no espere respuesta. Con la
        configuracion por defecto (ONEWAY_THREADED=True) Pyro4 ejecuta este
        metodo en un hilo propio, asi que no bloquea al resto del servidor.

        ``receptor`` llega como un proxy hacia el objeto del cliente.
        """
        try:
            resultado = self._ejecutar(trabajo_id, limite)
        except Exception as error:  # noqa: BLE001 - se informa al cliente
            # En una llamada oneway la excepcion no llega al cliente, por eso
            # se le informa explicitamente por el canal del callback.
            print("[servidor] ERROR   {}: {}".format(trabajo_id, error))
            self._notificar(receptor, "trabajo_fallido",
                            trabajo_id, str(error))
            return
        self._notificar(receptor, "trabajo_terminado", resultado)

    def estado(self):
        """Devuelve metricas basicas del servidor."""
        with self._lock:
            return {
                "completados": self._trabajos_completados,
                "en_curso": self._trabajos_en_curso,
            }

    # ------------------------------------------------------------------
    @staticmethod
    def _notificar(receptor, metodo, *args):
        """Invoca un metodo del callback del cliente de forma segura.

        Si el cliente ya se desconecto, el error se registra y el servidor
        sigue funcionando (tolerancia a fallos basica).
        """
        try:
            # ``receptor`` es un proxy que llego como argumento en esta
            # misma llamada, asi que solo lo usa este hilo.
            with receptor:
                getattr(receptor, metodo)(*args)
        except Pyro4.errors.CommunicationError as error:
            print("[servidor] No se pudo notificar al cliente: {}".format(
                error))


def main():
    """Crea el daemon, registra el servicio en el Name Server y lo atiende."""
    parser = argparse.ArgumentParser(description="Servidor Nivel 4 (Pyro4)")
    parser.add_argument("--host", default="localhost",
                        help="IP o host donde escucha el daemon")
    parser.add_argument("--ns-host", default=None,
                        help="host del Name Server (por defecto se busca)")
    args = parser.parse_args()

    daemon = Pyro4.Daemon(host=args.host)
    uri = daemon.register(ProcesadorDatos)

    # Localiza el Name Server y publica el nombre logico -> URI.
    with Pyro4.locateNS(host=args.ns_host) as ns:
        ns.register(NOMBRE_SERVICIO, uri)

    print("[servidor] Servicio '{}' registrado".format(NOMBRE_SERVICIO))
    print("[servidor] URI: {}".format(uri))
    print("[servidor] Esperando solicitudes... (Ctrl+C para salir)")

    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        print("\n[servidor] Deteniendo...")
    finally:
        # Se retira el nombre del Name Server para no dejar URIs huerfanas.
        try:
            with Pyro4.locateNS(host=args.ns_host) as ns:
                ns.remove(NOMBRE_SERVICIO)
        except Pyro4.errors.NamingError:
            pass
        daemon.close()


if __name__ == "__main__":
    main()
