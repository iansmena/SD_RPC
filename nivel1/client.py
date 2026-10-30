import Pyro4

uri = input("Ingrese el uri: ").strip()
Calculadora = Pyro4.Proxy(uri)    # use name server object lookup uri shortcut

print("<< Menu >>")
print("1. Suma")
print("2. Resta")
print("3. Multiplicacion")
print("4. Division")
print("5. Salir")
op = int(input("Ingrese una opcion: "))

print("Ingreso de datos")
num1 = float(input("Ingrese num1: "))
num2 = float(input("Ingrese num2: "))

match op:
    case 1:
        print(Calculadora.suma(num1, num2))
    case 2:
        print(Calculadora.resta(num1, num2))
    case 3:
        print(Calculadora.multiplicacion(num1, num2))
    case 4:
        if num2 != 0 :
            print(Calculadora.division(num1, num2))
        else :
            print("NO se puede dividir entre 0.")
    case 5:
        print("Fin del programa")