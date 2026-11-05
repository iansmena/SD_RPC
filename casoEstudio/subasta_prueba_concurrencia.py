"""Caso de estudio - Prueba de ofertas simultaneas y datos erroneos.

Lanza varios hilos que ofertan exactamente al mismo tiempo, cada uno con
su propio proxy, y verifica que el servidor no tuvo condiciones de
carrera: el precio final debe ser la oferta mas alta y el historial debe
ser estrictamente creciente. Despues envia ofertas con datos erroneos y
comprueba que el servidor responde con excepciones claras y sigue
funcionando.

Ejecucion (con el Name Server y el servidor ya iniciados):
    python3 subasta_prueba_concurrencia.py --hilos 20
"""

import argparse
import random
import threading

import Pyro4

from subasta_excepciones import (OfertaInvalida, SubastaCerrada,
                                 registrar_excepciones)

NOMBRE_SERVICIO = "PYRONAME:subastas.central"


def ofertar_en_paralelo(numero, monto, barrera, resultados):
    """Espera a los demas hilos y envia una oferta en el mismo instante."""
    usuario = f"bot{numero:02d}"
    with Pyro4.Proxy(NOMBRE_SERVICIO) as subasta:
        subasta._pyroBind()
        barrera.wait()
        try:
            subasta.ofertar(usuario, monto)
            resultados.append((usuario, monto, "aceptada"))
        except OfertaInvalida:
            resultados.append((usuario, monto, "rechazada"))


def probar_concurrencia(hilos):
    """Ejecuta las ofertas simultaneas y valida la consistencia final."""
    with Pyro4.Proxy(NOMBRE_SERVICIO) as subasta:
        base = subasta.obtener_estado()["precio_actual"]

    montos = [round(base + random.uniform(1, 500), 2) for _ in range(hilos)]
    barrera = threading.Barrier(hilos)
    resultados = []
    trabajadores = [
        threading.Thread(target=ofertar_en_paralelo,
                         args=(i, montos[i], barrera, resultados))
        for i in range(hilos)
    ]
    for trabajador in trabajadores:
        trabajador.start()
    for trabajador in trabajadores:
        trabajador.join()

    with Pyro4.Proxy(NOMBRE_SERVICIO) as subasta:
        estado = subasta.obtener_estado()
        historial = subasta.obtener_historial()

    aceptadas = sum(1 for r in resultados if r[2] == "aceptada")
    montos_historial = [monto for _, _, monto in historial]
    creciente = all(a < b for a, b in zip(montos_historial,
                                          montos_historial[1:]))

    print(f"Ofertas enviadas a la vez: {hilos}")
    print(f"Aceptadas: {aceptadas} | Rechazadas: {hilos - aceptadas}")
    print(f"Oferta mas alta enviada: ${max(montos):.2f}")
    print(f"Precio final en el servidor: ${estado['precio_actual']:.2f} "
          f"({estado['ganador']})")
    print(f"Historial estrictamente creciente: {creciente}")
    correcto = estado["precio_actual"] == max(montos) and creciente
    print("RESULTADO:", "sin condiciones de carrera" if correcto
          else "INCONSISTENCIA DETECTADA")


def probar_datos_erroneos():
    """Envia ofertas invalidas y verifica que el servicio siga respondiendo."""
    casos = [
        ("", 1000),
        ("ana", "mil"),
        ("ana", -50),
        ("ana", True),
        ("ana", 1),
    ]
    print("\nOfertas con datos erroneos:")
    with Pyro4.Proxy(NOMBRE_SERVICIO) as subasta:
        for usuario, monto in casos:
            try:
                subasta.ofertar(usuario, monto)
                print(f"  ({usuario!r}, {monto!r}) -> aceptada (inesperado)")
            except (OfertaInvalida, SubastaCerrada) as error:
                print(f"  ({usuario!r}, {monto!r}) -> "
                      f"{type(error).__name__}: {error}")
        estado = subasta.obtener_estado()
    print(f"El servidor sigue activo. Precio actual: "
          f"${estado['precio_actual']:.2f}")


def main():
    """Ejecuta las dos pruebas contra el servidor de subastas."""
    parser = argparse.ArgumentParser(description="Prueba de concurrencia")
    parser.add_argument("--hilos", type=int, default=20)
    args = parser.parse_args()

    registrar_excepciones()
    probar_concurrencia(args.hilos)
    probar_datos_erroneos()


if __name__ == "__main__":
    main()
