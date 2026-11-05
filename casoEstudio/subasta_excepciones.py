"""Excepciones personalizadas del sistema de subastas.

Pyro4 solo deserializa excepciones conocidas. Este modulo, compartido
por el cliente y el servidor, define las excepciones propias y las
registra en el serializador para que viajen por la red sin perder su
tipo.
"""

from Pyro4.util import SerializerBase


class OfertaInvalida(Exception):
    """Se lanza si la oferta tiene datos erroneos o no supera la actual."""


class SubastaCerrada(Exception):
    """Se lanza cuando se intenta ofertar en una subasta ya finalizada."""


EXCEPCIONES = (OfertaInvalida, SubastaCerrada)


def _excepcion_a_dict(excepcion):
    """Convierte una excepcion propia en un diccionario serializable."""
    return {
        "__class__": f"{__name__}.{type(excepcion).__name__}",
        "mensaje": str(excepcion),
    }


def registrar_excepciones():
    """Registra las excepciones propias en el serializador de Pyro4.

    Debe llamarse en el cliente y en el servidor antes de usar el servicio.
    """
    for clase in EXCEPCIONES:
        nombre = f"{__name__}.{clase.__name__}"
        SerializerBase.register_class_to_dict(clase, _excepcion_a_dict)
        SerializerBase.register_dict_to_class(
            nombre, lambda _, datos, c=clase: c(datos["mensaje"]))
