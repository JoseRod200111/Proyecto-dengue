import math


# ============================================================
# MODELO SEIR - DENGUE GUATEMALA 2024
# ============================================================

# Población proyectada de Guatemala para 2024.
POBLACION_GUATEMALA_2024 = 17_843_132


# ============================================================
# PARÁMETROS EPIDEMIOLÓGICOS BASE
# ============================================================

# Período de incubación aproximado:
# 7 días = 1 semana.
#
# sigma representa la velocidad con la que una persona
# pasa de Expuesta (E) a Infectada (I).
SIGMA_BASE = 1.0


# Período infeccioso aproximado:
# 4.5 días.
#
# Como nuestro modelo utiliza semanas:
#
# gamma = 1 / (4.5 / 7)
#       = 7 / 4.5
#
# gamma representa la velocidad con la que una persona
# pasa de Infectada (I) a Recuperada (R).
GAMMA_BASE = 7 / 4.5


# ============================================================
# CONDICIONES INICIALES BASE
# ============================================================

# PAHO reporta 1,618 casos durante la semana
# epidemiológica 1 de 2024.
CASOS_SEMANA_1 = 1_618


# Aproximación inicial de personas expuestas.
#
# Como sigma = 1 por semana, utilizamos los casos
# de la primera semana como referencia inicial para E0.
E0_BASE = CASOS_SEMANA_1


# Aproximación de infectados activos al inicio.
#
# Se utiliza la duración infecciosa promedio de 4.5 días:
#
# I0 ≈ casos_semana_1 * (4.5 / 7)
I0_BASE = round(
    CASOS_SEMANA_1
    * 4.5
    / 7
)


# El modelo comienza su ventana temporal en la
# semana epidemiológica 1 de 2024.
#
# R0 = 0 no significa que nadie haya tenido dengue antes,
# sino que no se reconstruye la historia epidemiológica
# previa al inicio de la simulación.
R0_BASE = 0


# ============================================================
# VALIDACIÓN DE PARÁMETROS
# ============================================================

def validar_finito(
    valor,
    nombre
):
    """Rechaza NaN, infinitos y valores no numéricos."""

    if not math.isfinite(valor):
        raise ValueError(
            f"{nombre} debe ser un número finito."
        )


def validar_parametros(
    beta,
    sigma,
    gamma,
    poblacion
):
    """
    Verifica que los parámetros principales del modelo
    tengan valores válidos.

    beta:
        Tasa efectiva de transmisión.

    sigma:
        Tasa de transición de expuesto a infectado.

    gamma:
        Tasa de recuperación.

    poblacion:
        Población total utilizada en el modelo.
    """

    validar_finito(
        poblacion,
        "La población"
    )

    validar_finito(
        beta,
        "beta"
    )

    validar_finito(
        sigma,
        "sigma"
    )

    validar_finito(
        gamma,
        "gamma"
    )

    if poblacion <= 0:
        raise ValueError(
            "La población debe ser mayor que cero."
        )

    if beta <= 0:
        raise ValueError(
            "beta debe ser mayor que cero."
        )

    if sigma <= 0:
        raise ValueError(
            "sigma debe ser mayor que cero."
        )

    if gamma <= 0:
        raise ValueError(
            "gamma debe ser mayor que cero."
        )

    return True


# ============================================================
# CREACIÓN DEL ESTADO INICIAL
# ============================================================

def crear_estado_inicial(
    poblacion,
    expuestos_iniciales,
    infectados_iniciales,
    recuperados_iniciales=0
):
    """
    Construye el estado inicial del modelo SEIR.

    Variables:

    S = susceptibles
    E = expuestos
    I = infectados
    R = recuperados
    C = casos acumulados generados por el modelo

    C no representa un compartimento de población.
    Se utiliza únicamente para medir incidencia acumulada.
    """

    validar_finito(
        poblacion,
        "La población"
    )

    validar_finito(
        expuestos_iniciales,
        "Los expuestos iniciales"
    )

    validar_finito(
        infectados_iniciales,
        "Los infectados iniciales"
    )

    validar_finito(
        recuperados_iniciales,
        "Los recuperados iniciales"
    )

    if poblacion <= 0:
        raise ValueError(
            "La población debe ser mayor que cero."
        )

    if expuestos_iniciales < 0:
        raise ValueError(
            "Los expuestos iniciales no pueden ser negativos."
        )

    if infectados_iniciales < 0:
        raise ValueError(
            "Los infectados iniciales no pueden ser negativos."
        )

    if recuperados_iniciales < 0:
        raise ValueError(
            "Los recuperados iniciales no pueden ser negativos."
        )

    ocupados = (
        expuestos_iniciales
        + infectados_iniciales
        + recuperados_iniciales
    )

    susceptibles_iniciales = (
        poblacion
        - ocupados
    )

    if susceptibles_iniciales < 0:
        raise ValueError(
            "Las condiciones iniciales superan la población total."
        )

    estado = (
        float(susceptibles_iniciales),
        float(expuestos_iniciales),
        float(infectados_iniciales),
        float(recuperados_iniciales),
        0.0,
    )

    return estado


# ============================================================
# ESTADO INICIAL BASE DEL PROYECTO
# ============================================================

def crear_estado_inicial_base():
    """
    Devuelve las condiciones iniciales utilizadas como
    escenario base del proyecto.
    """

    return crear_estado_inicial(
        poblacion=POBLACION_GUATEMALA_2024,
        expuestos_iniciales=E0_BASE,
        infectados_iniciales=I0_BASE,
        recuperados_iniciales=R0_BASE
    )


# ============================================================
# VALIDACIÓN DEL ESTADO
# ============================================================

def validar_estado(
    estado,
    poblacion,
    tolerancia=1e-6
):
    """
    Comprueba la consistencia interna del estado.

    Se verifica que:

    - S, E, I y R no sean negativos.
    - C no sea negativo.
    - S + E + I + R sea igual a la población total.
    """

    if len(estado) != 5:
        raise ValueError(
            "El estado debe contener S, E, I, R y C."
        )

    S, E, I, R, C = estado

    validar_finito(
        S,
        "S"
    )

    validar_finito(
        E,
        "E"
    )

    validar_finito(
        I,
        "I"
    )

    validar_finito(
        R,
        "R"
    )

    validar_finito(
        C,
        "C"
    )

    validar_finito(
        poblacion,
        "La población"
    )

    if S < 0:
        raise ValueError(
            "S no puede ser negativo."
        )

    if E < 0:
        raise ValueError(
            "E no puede ser negativo."
        )

    if I < 0:
        raise ValueError(
            "I no puede ser negativo."
        )

    if R < 0:
        raise ValueError(
            "R no puede ser negativo."
        )

    if C < 0:
        raise ValueError(
            "C no puede ser negativo."
        )

    total = (
        S
        + E
        + I
        + R
    )

    diferencia = abs(
        total
        - poblacion
    )

    if diferencia > tolerancia:
        raise ValueError(
            "S + E + I + R no coincide con la población total."
        )

    return True


# ============================================================
# TRANSMISIÓN ESTACIONAL
# ============================================================

def beta_estacional(
    semana,
    beta_base,
    amplitud,
    fase
):
    """
    Calcula la tasa efectiva de transmisión para una semana.

    Se utiliza una función sinusoidal:

        beta(t) =
        beta_base *
        [1 + amplitud * sin(2*pi*(t - fase)/52)]

    semana:
        Tiempo expresado en semanas.

    beta_base:
        Nivel promedio de transmisión.

    amplitud:
        Intensidad de la variación estacional.

        Debe cumplir:

            0 <= amplitud < 1

    fase:
        Desplaza temporalmente el patrón estacional.
    """

    validar_finito(
        semana,
        "La semana"
    )

    validar_finito(
        beta_base,
        "beta_base"
    )

    validar_finito(
        amplitud,
        "La amplitud"
    )

    validar_finito(
        fase,
        "La fase"
    )

    if beta_base <= 0:
        raise ValueError(
            "beta_base debe ser mayor que cero."
        )

    if amplitud < 0:
        raise ValueError(
            "La amplitud no puede ser negativa."
        )

    if amplitud >= 1:
        raise ValueError(
            "La amplitud debe ser menor que 1."
        )

    beta = beta_base * (
        1
        + amplitud
        * math.sin(
            2
            * math.pi
            * (semana - fase)
            / 52
        )
    )

    return beta


# ============================================================
# ECUACIONES DEL MODELO SEIR
# ============================================================

def derivadas_seir(
    estado,
    semana,
    beta_base,
    amplitud,
    fase,
    sigma,
    gamma,
    poblacion
):
    """
    Calcula las derivadas del modelo SEIR.

    La unidad de tiempo es la semana.

    Ecuaciones:

        dS/dt = -beta(t) * S * I / N

        dE/dt = beta(t) * S * I / N
                - sigma * E

        dI/dt = sigma * E
                - gamma * I

        dR/dt = gamma * I

        dC/dt = sigma * E

    C acumula las transiciones E -> I.

    Esto permitirá calcular posteriormente los casos
    incidentes simulados por semana y compararlos
    con los datos de PAHO.
    """

    validar_estado(
        estado,
        poblacion
    )

    beta = beta_estacional(
        semana,
        beta_base,
        amplitud,
        fase
    )

    validar_parametros(
        beta,
        sigma,
        gamma,
        poblacion
    )

    S, E, I, R, C = estado

    # Personas que pasan de susceptibles a expuestas.
    nuevos_expuestos = (
        beta
        * S
        * I
        / poblacion
    )

    # Personas que pasan de expuestas a infectadas.
    nuevos_infectados = (
        sigma
        * E
    )

    # Personas que pasan de infectadas a recuperadas.
    nuevas_recuperaciones = (
        gamma
        * I
    )

    dS = (
        -nuevos_expuestos
    )

    dE = (
        nuevos_expuestos
        - nuevos_infectados
    )

    dI = (
        nuevos_infectados
        - nuevas_recuperaciones
    )

    dR = (
        nuevas_recuperaciones
    )

    # Casos incidentes acumulados.
    dC = (
        nuevos_infectados
    )

    return (
        dS,
        dE,
        dI,
        dR,
        dC,
    )


# ============================================================
# INFORMACIÓN DEL MODELO
# ============================================================

def mostrar_resumen_modelo():
    """
    Muestra los parámetros y condiciones iniciales
    utilizadas por el escenario base.
    """

    estado_base = crear_estado_inicial_base()

    S0, E0, I0, R0, C0 = estado_base

    print(
        "=================================================="
    )
    print(
        "MODELO SEIR - DENGUE GUATEMALA 2024"
    )
    print(
        "=================================================="
    )

    print()
    print(
        "Población:",
        POBLACION_GUATEMALA_2024
    )

    print()
    print(
        "PARÁMETROS BIOLÓGICOS BASE"
    )

    print(
        "Sigma:",
        round(
            SIGMA_BASE,
            4
        ),
        "por semana"
    )

    print(
        "Gamma:",
        round(
            GAMMA_BASE,
            4
        ),
        "por semana"
    )

    print()
    print(
        "CONDICIONES INICIALES BASE"
    )

    print(
        "S0:",
        int(S0)
    )

    print(
        "E0:",
        int(E0)
    )

    print(
        "I0:",
        int(I0)
    )

    print(
        "R0:",
        int(R0)
    )

    print(
        "C0:",
        int(C0)
    )

    print()
    print(
        "Referencia semana 1 PAHO:",
        CASOS_SEMANA_1,
        "casos"
    )

    print()
    print(
        "PARÁMETROS PREVISTOS PARA CALIBRACIÓN PSO"
    )

    print(
        "- beta_base"
    )

    print(
        "- amplitud"
    )

    print(
        "- fase"
    )

    print(
        "- E0 e I0 podrían calibrarse posteriormente"
    )


# ============================================================
# PRUEBA DEL MÓDULO
# ============================================================

def main():
    mostrar_resumen_modelo()

    print()
    print(
        "Prueba del estado inicial base:"
    )

    estado_base = crear_estado_inicial_base()

    print(
        estado_base
    )

    validar_estado(
        estado_base,
        POBLACION_GUATEMALA_2024
    )

    print(
        "Estado inicial válido."
    )

    print()
    print(
        "Prueba de beta estacional:"
    )

    # Estos valores de beta_base, amplitud y fase
    # todavía son únicamente una prueba técnica.
    beta_prueba = beta_estacional(
        semana=1,
        beta_base=2.0,
        amplitud=0.3,
        fase=30
    )

    print(
        "Beta semana 1:",
        round(
            beta_prueba,
            6
        )
    )

    print()
    print(
        "Prueba de derivadas:"
    )

    derivadas = derivadas_seir(
        estado=estado_base,
        semana=1,
        beta_base=2.0,
        amplitud=0.3,
        fase=30,
        sigma=SIGMA_BASE,
        gamma=GAMMA_BASE,
        poblacion=POBLACION_GUATEMALA_2024
    )

    print(
        "dS, dE, dI, dR, dC:"
    )

    print(
        derivadas
    )


if __name__ == "__main__":
    main()