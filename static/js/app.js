const API = '';

async function verificarStatus() {
  const pill = document.getElementById('status-pill');
  try {
    const res = await fetch(`${API}/api/status`);
    const data = await res.json();
    pill.textContent = data.status === 'online' ? 'sistema online' : 'offline';
    pill.classList.remove('offline');
  } catch (e) {
    pill.textContent = 'offline';
    pill.classList.add('offline');
  }
}

async function carregarRegras() {
  const res = await fetch(`${API}/api/regras`);
  const data = await res.json();
  const lista = document.getElementById('lista-regras');
  lista.innerHTML = '';

  if (data.regras.length === 0) {
    lista.classList.add('vazio');
    return;
  }
  lista.classList.remove('vazio');

  data.regras.forEach(regra => {
    const item = document.createElement('div');
    item.className = 'regra-item';
    item.innerHTML = `
      <span class="desc"><span class="var">${regra.variavel}</span> ${regra.operador} ${regra.limite}</span>
      <button class="del" onclick="removerRegra(${regra.id})">&times;</button>
    `;
    lista.appendChild(item);
  });
}

async function criarRegra() {
  const variavel = document.getElementById('variavel').value.trim();
  const operador = document.getElementById('operador').value;
  const limite = parseFloat(document.getElementById('limite').value);
  const mensagem = document.getElementById('mensagem').value.trim();

  if (!variavel || isNaN(limite)) {
    alert('Preencha a variável e o valor limite.');
    return;
  }

  await fetch(`${API}/api/regras`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ variavel, operador, limite, mensagem: mensagem || undefined })
  });

  document.getElementById('variavel').value = '';
  document.getElementById('limite').value = '';
  document.getElementById('mensagem').value = '';

  carregarRegras();
  sincronizarCamposComRegras();
}

async function removerRegra(id) {
  await fetch(`${API}/api/regras/${id}`, { method: 'DELETE' });
  carregarRegras();
}

function adicionarCampoLeitura(nomePreenchido) {
  const container = document.getElementById('campos-leitura');
  const row = document.createElement('div');
  row.className = 'campo-leitura-row';
  row.innerHTML = `
    <input type="text" class="nome-var" placeholder="variável (ex: combustivel)" value="${nomePreenchido || ''}">
    <input type="number" class="valor-var" placeholder="valor">
    <button type="button" onclick="this.parentElement.remove()">&times;</button>
  `;
  container.appendChild(row);
}

async function sincronizarCamposComRegras() {
  // Garante que exista pelo menos um campo por variável já configurada
  const res = await fetch(`${API}/api/regras`);
  const data = await res.json();
  const container = document.getElementById('campos-leitura');

  if (container.children.length === 0) {
    const variaveis = [...new Set(data.regras.map(r => r.variavel))];
    if (variaveis.length === 0) {
      adicionarCampoLeitura();
      adicionarCampoLeitura('horas_uso');
    } else {
      variaveis.forEach(v => adicionarCampoLeitura(v));
    }
  }
}

async function monitorar() {
  const linhas = document.querySelectorAll('.campo-leitura-row');
  const leitura = {};

  linhas.forEach(linha => {
    const nome = linha.querySelector('.nome-var').value.trim();
    const valor = parseFloat(linha.querySelector('.valor-var').value);
    if (nome && !isNaN(valor)) leitura[nome] = valor;
  });

  if (Object.keys(leitura).length === 0) {
    alert('Informe ao menos uma variável com valor.');
    return;
  }

  const res = await fetch(`${API}/api/monitorar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(leitura)
  });

  const data = await res.json();
  renderizarResultado(data);
}

function renderizarResultado(data) {
  const container = document.getElementById('resultado');
  container.innerHTML = '';

  if (data.alertas.length === 0) {
    const ok = document.createElement('div');
    ok.className = 'ok-card';
    ok.textContent = '✓ Nenhum limite violado nesta leitura.';
    container.appendChild(ok);
  } else {
    data.alertas.forEach(alerta => {
      const card = document.createElement('div');
      card.className = 'alerta-card';
      card.innerHTML = `
        <div class="titulo">⚠ ${alerta.mensagem}</div>
        <div>${alerta.variavel} = ${alerta.valor_recebido} (limite: ${alerta.operador} ${alerta.limite})</div>
      `;
      container.appendChild(card);
    });
  }

  if (data.analise_ia) {
    const ia = data.analise_ia;

    if (ia.operacao_bloqueada) {
      const bloqueio = document.createElement('div');
      bloqueio.className = 'alerta-card bloqueio';
      bloqueio.innerHTML = `<div class="titulo">⛔ Operação bloqueada</div><div>Risco acima do limite configurado em modo bloqueio.</div>`;
      container.appendChild(bloqueio);
    }

    const card = document.createElement('div');
    card.className = 'ia-card';
    card.innerHTML = `
      <div class="label">Risco (IA)</div><div class="valor">${ia.risco}%</div>
      <div class="label">Nível de uso</div><div class="valor">${ia.nivel_uso}</div>
      <div class="label">Alto risco</div><div class="valor">${ia.alto_risco ? 'sim' : 'não'}</div>
      <div class="label">Recomendação</div><div class="valor">${ia.recomendacao}</div>
    `;
    container.appendChild(card);

    carregarRelatorio();
  }
}

async function carregarConfiguracao() {
  const res = await fetch(`${API}/api/configuracao`);
  const data = await res.json();
  document.getElementById('cfg-limite').value = data.limite_alerta;
  document.getElementById('cfg-modo').value = data.modo_operacao;
}

async function salvarConfiguracao() {
  const limite_alerta = parseFloat(document.getElementById('cfg-limite').value);
  const modo_operacao = document.getElementById('cfg-modo').value;
  const status = document.getElementById('cfg-status');

  const res = await fetch(`${API}/api/configuracao`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ limite_alerta, modo_operacao })
  });

  status.classList.remove('sucesso', 'erro');

  if (res.ok) {
    status.textContent = '✓ Configuração salva.';
    status.classList.add('sucesso');
  } else {
    const err = await res.json();
    status.textContent = `✗ ${err.erro}`;
    status.classList.add('erro');
  }
}

async function carregarRelatorio() {
  const res = await fetch(`${API}/api/relatorio`);
  const data = await res.json();

  const resumo = document.getElementById('relatorio-resumo');
  resumo.innerHTML = `
    <div class="label">Registros</div><div class="valor">${data.total_registros}</div>
    <div class="label">Risco médio</div><div class="valor">${data.media_risco ?? '—'}</div>
    <div class="label">Risco máx / mín</div><div class="valor">${data.maximo_risco ?? '—'} / ${data.minimo_risco ?? '—'}</div>
    <div class="label">Tendência</div><div class="valor">${data.tendencia}</div>
  `;

  const lista = document.getElementById('relatorio-lista');
  lista.innerHTML = '';

  data.evolucao.slice().reverse().forEach(reg => {
    const linha = document.createElement('div');
    linha.className = 'regra-item';
    const hora = new Date(reg.timestamp).toLocaleTimeString('pt-BR');
    linha.innerHTML = `
      <span class="desc">${hora} — horas_uso=${reg.horas_uso}</span>
      <span class="desc" style="font-weight:${reg.alto_risco ? '700' : '400'}">
        risco ${reg.risco}%
      </span>
    `;
    lista.appendChild(linha);
  });
}

verificarStatus();
carregarRegras().then(sincronizarCamposComRegras);
carregarConfiguracao();
carregarRelatorio();