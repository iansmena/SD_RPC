import Pyro4

server = Pyro4.Proxy("PYRONAME:banco")

while True:
    name = input("Cual es tu nombre? ").strip()
    if name != "":
        break
    else:
        print("Nombre Invalido")

print(f"Bienvenido al Banco, {name}")

while True:
    try: 
        print("\n 1: Depositar \n 2: Retirar \n 3: Consultar saldo \n 4: Salir")
        op = int(input("Seleccione una opcion: "))
        if op == 1:
            try: 
                monto = float(input("Ingrese el monto a depositar: "))
                if monto > 0:
                    print(server.get_depositar(monto))
                else:
                    print("Ingrese un monto mayor a 0")
            except ValueError:
                print("Ingrese un valor valido")

        elif op == 2:
            try:
                monto = float(input("Ingrese el monto a retirar: "))
                if monto > 0:
                    try:
                        print(server.get_retirar(monto))
                    except Exception as e:
                        print("Saldo insuficiente")
                else:
                    print("Ingrese un monto mayor a 0")
            except ValueError:
                print("Ingrese un valor valido")

        elif op == 3:
            print(server.get_consultar())

        elif op == 4:
            print("Saliendo del programa")
            break
        else:
            print("Ingrese un numero correcto")
    except ValueError:
        print("Seleccione un valor valido")