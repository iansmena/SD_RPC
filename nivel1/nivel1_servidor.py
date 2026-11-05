"""Nivel 1 - Servidor de la calculadora remota.

Publica el objeto Calculadora en un daemon de Pyro4 sin Name Server;
el cliente se conecta usando la URI que se imprime en consola.
"""

import Pyro4


@Pyro4.expose
class Calculadora(object):
    """Servicio remoto con las cuatro operaciones aritmeticas basicas."""

    def sumar(self, num1, num2):
        """Devuelve num1 + num2."""
        return num1 + num2

    def restar(self, num1, num2):
        """Devuelve num1 - num2."""
        return num1 - num2

    def multiplicar(self, num1, num2):
        """Devuelve num1 * num2."""
        return num1 * num2

    def dividir(self, num1, num2):
        """Devuelve num1 / num2.

        Lanza ZeroDivisionError si num2 es 0; Pyro4 la relanza en el cliente.
        """
        if num2 == 0:
            raise ZeroDivisionError("No se puede dividir entre 0.")
        return num1 / num2


def main():
    """Crea el daemon, registra la calculadora y atiende solicitudes."""
    daemon = Pyro4.Daemon()
    uri = daemon.register(Calculadora)

    print("Servidor de la calculadora listo.")
    print(f"URI: {uri}")

    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        daemon.close()


if __name__ == "__main__":
    main()
