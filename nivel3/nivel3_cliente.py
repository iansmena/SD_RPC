"""Nivel 3 - Cliente del banco distribuido.

Usa un unico proxy durante toda la sesion para que el servidor
mantenga el mismo saldo entre operaciones, y maneja las excepciones
personalizadas que envia el servidor.
"""

import Pyro4
import Pyro4.errors

from nivel3_excepciones import (MontoInvalido, SaldoInsuficiente,
                                registrar_excepciones)

NOMBRE_SERVICIO = "PYRONAME:practica.banco"


def leer_nombre():
    """Pide el nombre del usuario hasta que no este vacio."""
    while True:
        nombre = input("Cual es tu nombre? ").strip()
        if nombre:
            return nombre
        print("Nombre invalido.")


def leer_monto(mensaje):
    """Pide un monto por consola hasta que sea numerico."""
    while True:
        try:
            return float(input(mensaje))
        except ValueError:
            print("Ingrese un valor numerico valido.")


def mostrar_menu():
    """Imprime el menu de opciones."""
    print("\n1. Depositar")
    print("2. Retirar")
    print("3. Consultar saldo")
    print("4. Salir")


def main():
    """Abre una sesion con el banco y ejecuta el menu de operaciones."""
    registrar_excepciones()
    nombre = leer_nombre()
    print(f"Bienvenido al banco, {nombre}")

    try:
        with Pyro4.Proxy(NOMBRE_SERVICIO) as cuenta:
            while True:
                mostrar_menu()
                opcion = input("Seleccione una opcion: ").strip()

                try:
                    if opcion == "1":
                        monto = leer_monto("Ingrese el monto a depositar: ")
                        saldo = cuenta.depositar(monto)
                        print(f"Deposito exitoso. Nuevo saldo: ${saldo:.2f}")
                    elif opcion == "2":
                        monto = leer_monto("Ingrese el monto a retirar: ")
                        saldo = cuenta.retirar(monto)
                        print(f"Retiro exitoso. Nuevo saldo: ${saldo:.2f}")
                    elif opcion == "3":
                        saldo = cuenta.consultar_saldo()
                        print(f"Saldo actual: ${saldo:.2f}")
                    elif opcion == "4":
                        print("Saliendo del programa.")
                        break
                    else:
                        print("Opcion no valida.")
                except (SaldoInsuficiente, MontoInvalido) as error:
                    print(f"Error: {error}")

    except Pyro4.errors.NamingError:
        print("No se encontro el Name Server o el servicio.")
    except Pyro4.errors.PyroError as error:
        print(f"Error de comunicacion con Pyro4: {error}")


if __name__ == "__main__":
    main()
