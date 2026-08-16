def classificar_uso(horas):

    if horas < 4:
        return "Baixo"

    elif horas < 8:
        return "Médio"

    else:
        return "Alto"


def calcular_risco(horas):

    return min(horas * 10, 100)


def gerar_recomendacao(risco):

    if risco >= 90:
        return "Realizar manutenção imediata."

    elif risco >= 70:
        return "Agendar manutenção preventiva."

    elif risco >= 50:
        return "Monitorar equipamento com maior frequência."

    else:
        return "Operação dentro dos padrões."
