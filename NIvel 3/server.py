import Pyro4

class SaldoInsuficiente(Exception):
    pass

@Pyro4.expose
@Pyro4.behavior(instance_mode="session")  # Mantiene el saldo en memoria durante la sesion del cliente
class CuentaBancaria(object):
    def __init__(self):
        self.saldo = 0.0

    def get_depositar(self, monto):
        self.saldo = self.saldo + monto
        return f"Deposito exitoso. Tu nuevo saldo es: ${self.saldo}"

    def get_retirar(self, monto):
        if monto > self.saldo:
            raise SaldoInsuficiente("Saldo insuficiente para realizar este retiro.")
        self.saldo = self.saldo - monto
        return f"Retiro exitoso. Tu nuevo saldo es: ${self.saldo}"

    def get_consultar(self):
        return f"Tu saldo actual es: ${self.saldo}"


daemon = Pyro4.Daemon()                    # make a Pyro daemon
ns = Pyro4.locateNS()                      # find the name server
uri = daemon.register(CuentaBancaria)      # register CuentaBancaria as a Pyro object
ns.register("banco", uri)                  # register the object with a name in the name server

print("Servidor del Banco iniciado.")
daemon.requestLoop()                       # start the event loop of the server to wait for calls