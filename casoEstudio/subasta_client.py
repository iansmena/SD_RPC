import Pyro4

def main():
    try:
        ns = Pyro4.locateNS()
        uri = ns.lookup("subastas.central")
        
        with Pyro4.Proxy(uri) as servicio:
            usuario = input("Ingresa tu nombre: ").strip()

            if not usuario:
                usuario = "Anonimo"

            while True:
                print("\n===== SISTEMA DE SUBASTAS =====")
                print("1. Empezar")
                print("2. Salir")

                opcion = input("Selecciona una opcion: ")

                if opcion == "1":

                    mensaje = input("Escribe tu mensaje: ")
                    respuesta = servicio.enviar_mensaje(
                        usuario, mensaje
                    )
                    print(respuesta)
                
                elif opcion == "3":
                    print("Desconectando...")
                    break

                else:
                    print("Opcion no valida.")

    except Pyro4.errors.PyroError as error:
        print(f"Error de comunicacion con Pyro4: {error}")

    except OSError as error:
        print(f"Error de conexion: {error}")


if __name__ == "__main__":
    
    main()
