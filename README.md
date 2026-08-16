# Vortex — Monitoramento de Risco de Equipamentos - Trabalho FIAP 1° Ano IA

O Vortex é um sistema que ajuda a monitorar o risco de equipamentos em
operação (por exemplo, máquinas agrícolas), pensando no contexto de seguradoras.

Ele funciona a partir de quatro funcionalidades principais:

1. **Limites configuráveis** — o próprio cliente define regras simples,
   como "avisar se o combustível ficar abaixo de 30%" ou "avisar se a
   temperatura passar de 90°". Quando uma leitura do equipamento viola
   algum desses limites, o sistema gera um alerta.

2. **Inteligência Artificial** — uma rede neural analisa as horas de uso
   do equipamento e calcula um score de risco, indicando se ele está em
   um nível de atenção e sugerindo uma recomendação (ex: agendar
   manutenção preventiva).

3. **Política de operação** — o cliente escolhe um limite geral de
   risco e o que acontece quando ele é atingido: apenas **alertar** o
   operador, ou **bloquear** a operação até que o risco diminua.

4. **Relatório de evolução** — cada análise feita fica registrada, e o
   sistema calcula a média, o máximo/mínimo de risco e a tendência
   (subindo, caindo ou estável) ao longo do tempo.

O projeto tem uma API (Flask) e um painel web simples, onde é possível
cadastrar os limites, ajustar a política de operação, simular leituras
do equipamento e acompanhar os alertas, o resultado da IA e o relatório
na tela.


## Como rodar:
```bash
python -m venv venv
source venv/bin/activate 
pip install -r requirements.txt
python app.py
```
Depois acesse **http://localhost:5000** no navegador.
## Testes
```bash
pytest
```
## Tecnologias usadas

- **Flask** — API e servidor web
- **PyTorch** — rede neural que calcula o risco
- **Pandas / scikit-learn** — preparação dos dados de treino
- **HTML/CSS/JS puro** — painel de configuração e monitoramento