OPERADORES_VALIDOS = ["<", "<=", ">", ">=", "=="]


class RegraLimite:

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
