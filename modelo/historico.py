#OBS: Por enquanto, só utiliza
#armazenamento em memória (histórico é perdido ao reiniciar o servidor). Para uso real, trocar por um banco de dados.


from datetime import datetime, timezone


class HistoricoRisco:

    def __init__(self):
        self.registros = []

    def registrar(self, horas_uso, risco, alto_risco):

        self.registros.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "horas_uso": horas_uso,
            "risco": risco,
            "alto_risco": alto_risco
        })

    def gerar_relatorio(self):

        if not self.registros:
            return {
                "total_registros": 0,
                "media_risco": None,
                "maximo_risco": None,
                "minimo_risco": None,
                "tendencia": "sem dados",
                "evolucao": []
            }

        riscos = [r["risco"] for r in self.registros]

        media = sum(riscos) / len(riscos)

        tendencia = self._calcular_tendencia(riscos)

        return {
            "total_registros": len(self.registros),
            "media_risco": round(media, 2),
            "maximo_risco": max(riscos),
            "minimo_risco": min(riscos),
            "tendencia": tendencia,
            "evolucao": self.registros
        }

    def _calcular_tendencia(self, riscos):
        """
        Compara a média da primeira metade do histórico com a
        segunda metade para indicar se o risco está subindo,
        caindo ou estável.
        """

        if len(riscos) < 2:
            return "dados insuficientes"

        metade = len(riscos) // 2

        media_inicial = sum(riscos[:metade]) / metade
        media_final = sum(riscos[metade:]) / (len(riscos) - metade)

        diferenca = media_final - media_inicial

        if diferenca > 5:
            return "aumento"

        elif diferenca < -5:
            return "reducao"

        else:
            return "estavel"

    def limpar(self):
        self.registros = []
