"""Nivel 3 - Excepciones personalizadas del banco distribuido.

Pyro4 solo deserializa excepciones conocidas. Este modulo, compartido
por el cliente y el servidor, define las excepciones propias y las
registra en el serializador para que viajen por la red sin perder
su tipo.
"""

from Pyro4.util import SerializerBase


class SaldoInsuficiente(Exception):
    """Se lanza cuando el monto a retirar supera el saldo disponible."""

    pass


class MontoInvalido(Exception):
    """Se lanza cuando el monto no es un numero mayor a 0."""

    pass


def _exception_a_dict(excepcion):
    """Convierte una excepcion propia en un diccionario serializable."""
    return {
        "__class__": f"{__name__}.{type(excepcion).__name__}",
        "mensaje": str(excepcion),
    }


def registrar_excepciones():
    """Registra las excepciones propias en el serializador de Pyro4.

    Debe llamarse en el cliente y en el servidor antes de usar el servicio.
    """
    for clase in (SaldoInsuficiente, MontoInvalido):
        nombre = f"{__name__}.{clase.__name__}"
        SerializerBase.register_class_to_dict(clase, _exception_a_dict)
        SerializerBase.register_dict_to_class(
            nombre, lambda _, datos, c=clase: c(datos["mensaje"]))
