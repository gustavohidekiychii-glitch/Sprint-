"""
Motor de regras configuraveis.

Permite que o cliente (ex: SOMPO) defina seus proprios limites
para variaveis do equipamento (ex: "combustivel < 30%") e gera
alertas automaticamente quando uma leitura viola algum limite.

Isso e independente da rede neural (RiskNet) - sao regras de
negocio simples, nao aprendizado de maquina.
"""

OPERADORES_VALIDOS = ["<", "<=", ">", ">=", "=="]


class RegraLimite:
    """Representa um único limite configurado pelo usuário."""

    def __init__(self, id_regra, variavel, operador, limite, mensagem=None):

        if operador not in OPERADORES_VALIDOS:
            raise ValueError(
                f"Operador inválido: '{operador}'. "
                f"Use um de {OPERADORES_VALIDOS}."
            )

        self.id = id_regra
        self.variavel = variavel
        self.operador = operador
        self.limite = limite
        self.mensagem = mensagem or (
            f"'{variavel}' {operador} {limite}"
        )

    def violada(self, valor):

        if self.operador == "<":
            return valor < self.limite

        elif self.operador == "<=":
            return valor <= self.limite

        elif self.operador == ">":
            return valor > self.limite

        elif self.operador == ">=":
            return valor >= self.limite

        elif self.operador == "==":
            return valor == self.limite

    def to_dict(self):

        return {
            "id": self.id,
            "variavel": self.variavel,
            "operador": self.operador,
            "limite": self.limite,
            "mensagem": self.mensagem,
        }


class MotorRegras:
    """
    Guarda as regras configuradas e avalia leituras de
    equipamentos contra elas, gerando alertas.

    OBS: armazenamento em memória (some ao reiniciar o servidor).
    Para produção, trocar por um banco de dados.
    """

    def __init__(self):
        self.regras = []
        self._proximo_id = 1

    def adicionar_regra(self, variavel, operador, limite, mensagem=None):

        regra = RegraLimite(
            self._proximo_id,
            variavel,
            operador,
            limite,
            mensagem
        )

        self.regras.append(regra)
        self._proximo_id += 1

        return regra

    def remover_regra(self, id_regra):

        antes = len(self.regras)

        self.regras = [
            r for r in self.regras if r.id != id_regra
        ]

        return len(self.regras) < antes

    def listar_regras(self):

        return [r.to_dict() for r in self.regras]

    def avaliar_leitura(self, leitura: dict):
        """
        leitura: dict tipo {"combustivel": 25, "temperatura": 90, ...}

        Retorna a lista de alertas disparados (regras violadas).
        Regras cuja variável não aparece na leitura são ignoradas.
        """

        alertas = []

        for regra in self.regras:

            if regra.variavel not in leitura:
                continue

            valor = leitura[regra.variavel]

            if regra.violada(valor):

                alertas.append({
                    "regra_id": regra.id,
                    "variavel": regra.variavel,
                    "valor_recebido": valor,
                    "operador": regra.operador,
                    "limite": regra.limite,
                    "mensagem": regra.mensagem,
                })

        return alertas
