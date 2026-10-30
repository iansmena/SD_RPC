import Pyro4

@Pyro4.expose
class Calculadora(object):
    def suma(self, num1, num2):
        s = num1 + num2
        return "La suma entre {0} y {1} es igual a {2}".format(num1, num2, s)

    def resta(self, num1, num2):
        s = num1 - num2
        return "La resta entre {0} y {1} es igual a {2}".format(num1, num2, s)

    def multiplicacion(self, num1, num2):
        s = num1 * num2
        return "La multiplicacion entre {0} y {1} es igual a {2}".format(num1, num2, s)

    def division(self, num1, num2):
        s = num1 / num2
        return "La division entre {0} y {1} es igual a {2}".format(num1, num2, s)

    

daemon = Pyro4.Daemon()                # make a Pyro daemon
# ns = Pyro4.locateNS()                  # find the name server
uri = daemon.register(Calculadora)   # register the greeting maker as a Pyro object
# ns.register("calculo", uri)   # register the object with a name in the name server

print("Ready.")
print(f"uri:{uri}")
daemon.requestLoop()                   # start the event loop of the server to wait for calls
