MODOS_VALIDOS = ["alerta", "bloqueio"]
CONFIG = {
    "limite_alerta": 70,
    "modo_operacao": "alerta"  # "alerta": só notifica | "bloqueio": impede a operação
}


def atualizar_config(limite_alerta=None, modo_operacao=None):

    if modo_operacao is not None:

        if modo_operacao not in MODOS_VALIDOS:
            raise ValueError(
                f"modo_operacao inválido: '{modo_operacao}'. "
                f"Use um de {MODOS_VALIDOS}."
            )

        CONFIG["modo_operacao"] = modo_operacao

    if limite_alerta is not None:

        if not isinstance(limite_alerta, (int, float)):
            raise ValueError("limite_alerta deve ser numérico.")

        CONFIG["limite_alerta"] = limite_alerta

    return CONFIG


def avaliar_operacao(risco):

    risco_alto = risco >= CONFIG["limite_alerta"]

    bloqueado = (
        risco_alto and CONFIG["modo_operacao"] == "bloqueio"
    )

    return {
        "risco_alto": risco_alto,
        "modo_operacao": CONFIG["modo_operacao"],
        "operacao_bloqueada": bloqueado
    }
