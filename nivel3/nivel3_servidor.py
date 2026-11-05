"""Nivel 3 - Servidor del banco distribuido (servicio con estado).

Registra CuentaBancaria en el Name Server como practica.banco. Usa
instance_mode="session": cada conexion de cliente tiene su propia
cuenta, y el saldo se conserva entre llamadas consecutivas.
"""

import threading

import Pyro4
import Pyro4.errors

from nivel3_excepciones import (MontoInvalido, SaldoInsuficiente,
                                registrar_excepciones)

NOMBRE_SERVICIO = "practica.banco"


@Pyro4.expose
@Pyro4.behavior(instance_mode="session")
class CuentaBancaria(object):
    """Cuenta bancaria remota que conserva el saldo durante la sesion."""

    def __init__(self):
        """Inicializa el estado interno y el Lock que lo protege."""
        self._saldo = 0.0
        self._lock = threading.Lock()

    @staticmethod
    def _validar_monto(monto):
        """Lanza MontoInvalido si el monto no es un numero mayor a 0."""
        if isinstance(monto, bool) or not isinstance(monto, (int, float)):
            raise MontoInvalido("El monto debe ser un numero.")
        if monto <= 0:
            raise MontoInvalido("El monto debe ser mayor a 0.")

    def depositar(self, monto):
        """Suma el monto al saldo y devuelve el saldo nuevo."""
        self._validar_monto(monto)
        with self._lock:
            self._saldo += monto
            return self._saldo

    def retirar(self, monto):
        """Resta el monto del saldo y devuelve el saldo nuevo.

        Lanza SaldoInsuficiente si el monto supera el saldo.
        """
        self._validar_monto(monto)
        with self._lock:
            if monto > self._saldo:
                raise SaldoInsuficiente(
                    f"Saldo insuficiente. Saldo actual: ${self._saldo:.2f}")
            self._saldo -= monto
            return self._saldo

    def consultar_saldo(self):
        """Devuelve el saldo actual de la cuenta."""
        with self._lock:
            return self._saldo


def main():
    """Crea el daemon, registra el banco en el Name Server y lo atiende."""
    registrar_excepciones()

    daemon = Pyro4.Daemon()
    uri = daemon.register(CuentaBancaria)

    with Pyro4.locateNS() as ns:
        ns.register(NOMBRE_SERVICIO, uri)

    print("Servidor del banco iniciado.")
    print(f"Servicio registrado como: {NOMBRE_SERVICIO}")

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
