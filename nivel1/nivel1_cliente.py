"""Nivel 1 - Cliente de la calculadora remota.

Se conecta al servidor con la URI directa (sin Name Server) y ofrece
un menu para ejecutar las operaciones remotas.
"""

import Pyro4
import Pyro4.errors

OPERACIONES = {
    "1": ("Suma", "sumar"),
    "2": ("Resta", "restar"),
    "3": ("Multiplicacion", "multiplicar"),
    "4": ("Division", "dividir"),
}


def leer_numero(mensaje):
    """Pide un numero por consola hasta que el usuario ingrese uno valido."""
    while True:
        try:
            return float(input(mensaje))
        except ValueError:
            print("Ingrese un numero valido.")


def mostrar_menu():
    """Imprime el menu de opciones."""
    print("\n<< Menu >>")
    for clave, (nombre, _) in OPERACIONES.items():
        print(f"{clave}. {nombre}")
    print("5. Salir")


def main():
    """Pide la URI, se conecta al servidor y ejecuta el menu."""
    uri = input("Ingrese la URI del servidor: ").strip()

    try:
        with Pyro4.Proxy(uri) as calculadora:
            while True:
                mostrar_menu()
                opcion = input("Ingrese una opcion: ").strip()

                if opcion == "5":
                    print("Fin del programa.")
                    break

                if opcion not in OPERACIONES:
                    print("Opcion no valida.")
                    continue

                nombre, metodo = OPERACIONES[opcion]
                num1 = leer_numero("Ingrese num1: ")
                num2 = leer_numero("Ingrese num2: ")

                try:
                    resultado = getattr(calculadora, metodo)(num1, num2)
                    print(f"{nombre} de {num1} y {num2} = {resultado}")
                except ZeroDivisionError as error:
                    print(f"Error: {error}")

    except Pyro4.errors.PyroError as error:
        print(f"Error de comunicacion con Pyro4: {error}")


if __name__ == "__main__":
    main()
