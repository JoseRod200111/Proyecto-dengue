from dataclasses import dataclass

from src.modelo_seir import (
    E0_BASE,
    GAMMA_BASE,
    I0_BASE,
    POBLACION_GUATEMALA_2024,
    R0_BASE,
    SIGMA_BASE,
    crear_estado_inicial,
    validar_finito,
    validar_parametros,
)


# ============================================================
# PARÁMETROS DEL ESCENARIO BASE
# ============================================================

BETA_BASE = 2.0
AMPLITUD_BASE = 0.3
FASE_BASE = 30.0
SEMANAS_BASE = 52
PASO_BASE = 0.01


# ============================================================
# CONFIGURACIÓN DE ESCENARIOS
# ============================================================

@dataclass(frozen=True)
class ParametrosSEIR:
    beta_base: float
    amplitud: float
    fase: float
    sigma: float = SIGMA_BASE
    gamma: float = GAMMA_BASE
    poblacion: int = POBLACION_GUATEMALA_2024

    def __post_init__(self):
        validar_parametros(
            self.beta_base,
            self.sigma,
            self.gamma,
            self.poblacion
        )

        validar_finito(
            self.amplitud,
            "La amplitud"
        )

        validar_finito(
            self.fase,
            "La fase"
        )

        if not 0 <= self.amplitud < 1:
            raise ValueError(
                "La amplitud debe cumplir 0 <= amplitud < 1."
            )


@dataclass(frozen=True)
class CondicionesIniciales:
    expuestos: float = E0_BASE
    infectados: float = I0_BASE
    recuperados: float = R0_BASE

    def __post_init__(self):
        for nombre, valor in (
            ("Los expuestos", self.expuestos),
            ("Los infectados", self.infectados),
            ("Los recuperados", self.recuperados),
        ):
            validar_finito(
                valor,
                nombre
            )

            if valor < 0:
                raise ValueError(
                    f"{nombre} no pueden ser negativos."
                )


@dataclass(frozen=True)
class Escenario:
    nombre: str
    parametros: ParametrosSEIR
    condiciones: CondicionesIniciales
    semanas: int = SEMANAS_BASE
    paso: float = PASO_BASE
    semilla: int | None = None
    modo_estocastico: bool = False

    def __post_init__(self):
        if not self.nombre.strip():
            raise ValueError(
                "El escenario debe tener un nombre."
            )

        if (
            isinstance(self.semanas, bool)
            or not isinstance(self.semanas, int)
            or self.semanas <= 0
        ):
            raise ValueError(
                "Las semanas deben ser un entero mayor que cero."
            )

        validar_finito(
            self.paso,
            "El paso"
        )

        if self.paso <= 0:
            raise ValueError(
                "El paso debe ser mayor que cero."
            )

        if self.semilla is not None:
            if (
                isinstance(self.semilla, bool)
                or not isinstance(self.semilla, int)
                or self.semilla < 0
            ):
                raise ValueError(
                    "La semilla debe ser un entero no negativo."
                )

        if not isinstance(
            self.modo_estocastico,
            bool
        ):
            raise ValueError(
                "modo_estocastico debe ser booleano."
            )

        crear_estado_inicial(
            poblacion=self.parametros.poblacion,
            expuestos_iniciales=self.condiciones.expuestos,
            infectados_iniciales=self.condiciones.infectados,
            recuperados_iniciales=self.condiciones.recuperados
        )


def crear_escenario_base():
    """Devuelve el escenario base, todavía sin calibrar."""

    return Escenario(
        nombre="base",
        parametros=ParametrosSEIR(
            beta_base=BETA_BASE,
            amplitud=AMPLITUD_BASE,
            fase=FASE_BASE
        ),
        condiciones=CondicionesIniciales()
    )
