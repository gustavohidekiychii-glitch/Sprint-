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
==================================================================================================================================
# Vortex Field Unit — Firmware ESP32

Gêmeo físico do sistema Vortex: um ESP32 com sensores simulando um
equipamento agrícola real, que se conecta à API Vortex (pasta raiz do
repositório) via WiFi para sincronizar a política de risco e registrar
leituras no histórico.

## O que ele faz

- Lê temperatura/umidade, nível de um reservatório, vibração e carga
  simulada do equipamento.
- Calcula um risco local (funciona mesmo sem WiFi, como failsafe).
- Sincroniza com a API Vortex: busca o limite de risco e o modo de
  operação (`alerta`/`bloqueio`), e envia cada leitura para o histórico.
- Sinaliza o status com LEDs, buzzer e um servo (ponteiro de risco).
- Em modo bloqueio, corta a energia de uma mini bomba d'água via relé
  quando o risco ultrapassa o limite — implementação física da User
  Story de configuração de limites e políticas.


## Bibliotecas necessárias

No Arduino IDE, em Ferramentas → Gerenciar Bibliotecas, instale:

- `DHT sensor library` (Adafruit)
- `Adafruit Unified Sensor`
- `ESP32Servo`
- `ArduinoJson` (versão 7.x)

## Configuração antes do upload

No topo do arquivo `vortex_field_unit.ino`, ajuste:

```cpp
const char* WIFI_SSID  = "NOME_DA_SUA_REDE";
const char* WIFI_SENHA = "SENHA_DA_SUA_REDE";
const char* API_HOST   = "http:// :5000"; // IP do PC rodando o Flask
```

O ESP32 e o computador rodando `python app.py` precisam estar na
**mesma rede WiFi**.

Também calibre o sensor de nível conforme o tamanho do seu reservatório:

```cpp
const float DISTANCIA_VAZIO = 20.0;  // cm, sensor até o fundo (vazio)
const float DISTANCIA_CHEIO = 3.0;   // cm, sensor até a água (cheio)
```

## Como testar

1. Rode `python app.py` no computador (API Vortex precisa estar no ar).
2. Faça upload do sketch para o ESP32.
3. Abra o Serial Monitor (115200 baud) e confira se aparece "WiFi conectado".
4. No painel web (`http://localhost:5000`), mude o modo de operação para
   `bloqueio` e force um risco alto — o relé deve desligar a bomba.