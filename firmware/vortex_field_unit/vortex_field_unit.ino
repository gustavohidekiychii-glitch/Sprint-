/*
  VORTEX FIELD UNIT — versão Wokwi (simulação)
  -----------------------------------------------
  Versão simplificada do firmware físico, pensada pra rodar no
  simulador Wokwi (wokwi.com) em vez de num ESP32 de verdade.

  O que mudou em relação à versão física:
  - Removidos o HC-SR04 (nível/combustível) e o piezo (vibração) —
    nenhum dos dois entra mais no cálculo de risco da IA (o site já
    não usa mais essas variáveis). Simplifica bastante o circuito.
  - "Distância percorrida" (uma das 4 variáveis que a IA usa) não tem
    um sensor físico simples que meça isso direto (normalmente viria
    de GPS/odômetro). Pra simular, uso um SEGUNDO potenciômetro — você
    gira o botão e o valor muda, representando essa variável.

  Variáveis enviadas pra IA (mesmas 4 do site): horas_uso, temperatura,
  distancia_percorrida, carga_equipamento.

  IMPORTANTE sobre o WiFi no Wokwi: o simulador tem uma rede própria,
  chamada "Wokwi-GUEST" (sem senha), com acesso real à internet. Só
  que ela NÃO enxerga o seu computador — então, rodando local (python
  app.py na sua máquina), o ESP32 simulado não vai conseguir conversar
  com a API. Isso é normal e não é um bug: o simulador roda na nuvem
  da Wokwi, não na sua rede local. Se quiser testar a integração de
  verdade, seria preciso expor sua API com uma ferramenta tipo ngrok
  (te explico se quiser). Sem isso, o firmware ainda funciona sozinho
  — sensores, cálculo de risco local, LEDs, servo e relé continuam
  funcionando normalmente, só a sincronização com o servidor que falha
  (e o código já foi feito pra lidar bem com isso).

  Bibliotecas necessárias (Arduino IDE > Sketch > Include Library > Manage Libraries):
  - DHT sensor library (Adafruit)
  - Adafruit Unified Sensor
  - ESP32Servo
  - ArduinoJson (versão 7.x)

  No Wokwi, use a aba "Library Manager" do editor pra adicionar as
  mesmas bibliotecas antes de rodar a simulação.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <ESP32Servo.h>

// ===================================                                    ==================
// CONFIGURAÇÃO
// =====================================================

// Rede própria do simulador Wokwi — não precisa trocar.
const char* WIFI_SSID  = "Wokwi-GUEST";
const char* WIFI_SENHA = "";

// Só funciona se você expuser sua API publicamente (ex: ngrok).
// Rodando 100% local, deixe como está — o firmware roda sozinho.
const char* API_HOST = "http://192.168.0.100:5000";

// =====================================================
// PINOS
// =====================================================

#define PINO_DHT            4
#define PINO_POT_CARGA      34
#define PINO_POT_DISTANCIA  35
#define PINO_BOTAO          32
#define PINO_RELE           33
#define PINO_SERVO          25
#define PINO_LED_VERDE      26
#define PINO_LED_AMARELO    27
#define PINO_LED_VERMELHO   13
#define PINO_BUZZER         19

#define DHTTIPO DHT22

DHT dht(PINO_DHT, DHTTIPO);
Servo servoRisco;

// =====================================================
// ESTADO DO SISTEMA
// =====================================================

bool operacaoAtiva = false;
unsigned long inicioOperacao = 0;
float horasUsoAcumuladas = 0;   // 1 minuto real = 1 "hora" simulada

float limiteAlertaServidor = 70;
String modoOperacaoServidor = "alerta";

unsigned long ultimaSincronizacao = 0;
const unsigned long INTERVALO_SINCRONIZACAO = 15000; // 15s

unsigned long ultimoEnvio = 0;
const unsigned long INTERVALO_ENVIO = 10000; // 10s

unsigned long ultimoDebounce = 0;
int estadoBotaoAnterior = HIGH;

// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);

  pinMode(PINO_BOTAO, INPUT_PULLUP);
  pinMode(PINO_RELE, OUTPUT);
  pinMode(PINO_LED_VERDE, OUTPUT);
  pinMode(PINO_LED_AMARELO, OUTPUT);
  pinMode(PINO_LED_VERMELHO, OUTPUT);
  pinMode(PINO_BUZZER, OUTPUT);

  // A maioria dos módulos de relé baratos é "ativo em LOW".
  digitalWrite(PINO_RELE, HIGH);

  dht.begin();

  servoRisco.attach(PINO_SERVO);
  servoRisco.write(0);

  conectarWiFi();

  Serial.println("Vortex Field Unit (Wokwi) iniciado.");
}

// =====================================================
// LOOP PRINCIPAL
// =====================================================

void loop() {

  atualizarBotao();

  if (operacaoAtiva) {
    unsigned long agora = millis();
    horasUsoAcumuladas = (agora - inicioOperacao) / 60000.0;
  }

  float temperatura = dht.readTemperature();
  float umidade = dht.readHumidity();

  if (isnan(temperatura)) temperatura = 25; // fallback se o sensor falhar
  if (isnan(umidade)) umidade = 50;

  float distanciaPercorrida = map(analogRead(PINO_POT_DISTANCIA), 0, 4095, 0, 100);
  float cargaEquipamento = map(analogRead(PINO_POT_CARGA), 0, 4095, 0, 100);

  float risco = calcularRiscoLocal(
    horasUsoAcumuladas,
    temperatura,
    distanciaPercorrida,
    cargaEquipamento
  );

  if (millis() - ultimaSincronizacao > INTERVALO_SINCRONIZACAO) {
    sincronizarConfiguracao();
    ultimaSincronizacao = millis();
  }

  bool bloqueado = (
    risco >= limiteAlertaServidor &&
    modoOperacaoServidor == "bloqueio"
  );

  atualizarAtuadores(risco, bloqueado);

  if (millis() - ultimoEnvio > INTERVALO_ENVIO) {

    enviarLeituraParaServidor(
      horasUsoAcumuladas,
      temperatura,
      distanciaPercorrida,
      cargaEquipamento
    );

    ultimoEnvio = millis();
  }

  imprimirStatus(
    risco,
    temperatura,
    umidade,
    distanciaPercorrida,
    cargaEquipamento,
    bloqueado
  );

  delay(300);
}

// =====================================================
// WiFi
// =====================================================

void conectarWiFi() {

  Serial.print("Conectando ao WiFi");
  WiFi.begin(WIFI_SSID, WIFI_SENHA);

  int tentativas = 0;

  while (WiFi.status() != WL_CONNECTED && tentativas < 20) {
    delay(500);
    Serial.print(".");
    tentativas++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado! IP do ESP32: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nNao foi possivel conectar ao WiFi. Rodando em modo local (sem servidor).");
  }
}

// =====================================================
// Botão de start/stop da operação (com debounce simples)
// =====================================================

void atualizarBotao() {

  int leitura = digitalRead(PINO_BOTAO);

  if (leitura != estadoBotaoAnterior) {
    ultimoDebounce = millis();
  }

  if ((millis() - ultimoDebounce) > 50) {

    if (leitura == LOW && estadoBotaoAnterior == HIGH) {

      operacaoAtiva = !operacaoAtiva;

      if (operacaoAtiva) {
        inicioOperacao = millis() - (unsigned long)(horasUsoAcumuladas * 60000);
        Serial.println(">> Operacao iniciada");
      } else {
        Serial.println(">> Operacao parada");
      }
    }
  }

  estadoBotaoAnterior = leitura;
}

// =====================================================
// Risco local — a MESMA fórmula usada pra rotular o dataset
// de treino da IA no site (ver modelo/dataset.py, _risco_ponderado)
// =====================================================

float calcularRiscoLocal(float horas, float temperatura, float distancia, float carga) {

  float riscoHoras = min(horas * 10.0, 100.0);

  // Temperatura é perigosa nos dois sentidos: frio extremo OU calor
  // extremo. Faixa "normal" considerada: 15°C a 35°C.
  const float FAIXA_MIN = 15.0;
  const float FAIXA_MAX = 35.0;

  float foraDaFaixa = 0;
  if (FAIXA_MIN - temperatura > foraDaFaixa) foraDaFaixa = FAIXA_MIN - temperatura;
  if (temperatura - FAIXA_MAX > foraDaFaixa) foraDaFaixa = temperatura - FAIXA_MAX;

  float riscoTemp = min(foraDaFaixa * (100.0 / 40.0), 100.0);

  float riscoDistancia = constrain(distancia, 0, 100);
  float riscoCarga = constrain(carga, 0, 100);

  float riscoTotal =
    (riscoHoras     * 0.40) +
    (riscoTemp      * 0.30) +
    (riscoDistancia * 0.15) +
    (riscoCarga     * 0.15);

  return constrain(riscoTotal, 0, 100);
}

// =====================================================
// Atuadores: LEDs, buzzer, servo e relé
// =====================================================

void atualizarAtuadores(float risco, bool bloqueado) {

  digitalWrite(PINO_LED_VERDE,    risco < 50);
  digitalWrite(PINO_LED_AMARELO,  risco >= 50 && risco < 70);
  digitalWrite(PINO_LED_VERMELHO, risco >= 70);

  int angulo = map((int)risco, 0, 100, 0, 180);
  servoRisco.write(angulo);

  if (risco >= 70) {
    tone(PINO_BUZZER, 1000, 200);
  }

  digitalWrite(PINO_RELE, bloqueado ? LOW : HIGH);
}

// =====================================================
// Comunicação com a API Vortex (Flask) — só funciona se a
// API estiver acessível pela internet (ver nota no topo do arquivo)
// =====================================================

void sincronizarConfiguracao() {

  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(String(API_HOST) + "/api/configuracao");

  int codigo = http.GET();

  if (codigo == 200) {

    String resposta = http.getString();

    JsonDocument doc;
    deserializeJson(doc, resposta);

    limiteAlertaServidor = doc["limite_alerta"] | 70;
    modoOperacaoServidor = doc["modo_operacao"].as<String>();

    Serial.println(
      "Config sincronizada: limite=" + String(limiteAlertaServidor) +
      " modo=" + modoOperacaoServidor
    );

  } else {
    Serial.println("Falha ao sincronizar configuracao (codigo " + String(codigo) + ")");
  }

  http.end();
}

void enviarLeituraParaServidor(
  float horas,
  float temperatura,
  float distancia,
  float carga
) {

  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(String(API_HOST) + "/api/monitorar");
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["horas_uso"] = horas;
  doc["temperatura"] = temperatura;
  doc["distancia_percorrida"] = distancia;
  doc["carga_equipamento"] = carga;

  String corpo;
  serializeJson(doc, corpo);

  int codigo = http.POST(corpo);

  if (codigo == 200) {
    Serial.println("Leitura enviada ao servidor com sucesso.");
  } else {
    Serial.println("Falha ao enviar leitura (codigo " + String(codigo) + ")");
  }

  http.end();
}

// =====================================================
// Debug no Serial Monitor
// =====================================================

void imprimirStatus(
  float risco,
  float temperatura,
  float umidade,
  float distancia,
  float carga,
  bool bloqueado
) {

  Serial.println("----------------------------------------");
  Serial.println("Operacao ativa: " + String(operacaoAtiva ? "sim" : "nao"));
  Serial.println("Horas de uso:   " + String(horasUsoAcumuladas, 2));
  Serial.println("Temperatura:    " + String(temperatura) + " C");
  Serial.println("Umidade:        " + String(umidade) + " %");
  Serial.println("Distancia:      " + String(distancia) + " km");
  Serial.println("Carga:          " + String(carga) + " %");
  Serial.println("Risco:          " + String(risco, 1) + "%");
  Serial.println("Modo servidor:  " + modoOperacaoServidor + " (limite " + String(limiteAlertaServidor) + ")");
  Serial.println("Bloqueado:      " + String(bloqueado ? "SIM" : "nao"));
}
