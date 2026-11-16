// Buscas de CNPJ (BrasilAPI) e CEP (ViaCEP): só rodam quando você clica no botão.
async function buscar(tipo, origem) {
  const campo = document.querySelector(`[name="${origem}"]`);
  const status = document.getElementById(`status-${tipo}`);
  if (!campo || !campo.value.trim()) { status.textContent = "Preencha o campo primeiro."; return; }
  status.textContent = "Buscando...";
  try {
    const r = await fetch(`/api/${tipo}/${encodeURIComponent(campo.value.trim())}`);
    const j = await r.json();
    if (!r.ok) { status.textContent = j.erro || "Não encontrado."; return; }
    let n = 0;
    for (const [k, v] of Object.entries(j)) {
      const alvo = document.querySelector(`[name="${k}"]`);
      if (alvo && v && (!alvo.value || tipo === "cep" || alvo.tagName === "SELECT")) { alvo.value = v; n++; }
    }
    status.textContent = n ? `Preenchido (${n} campos). Confira antes de salvar.` : "Nada para preencher.";
  } catch (e) {
    status.textContent = "Sem conexão agora. Preencha à mão.";
  }
}

// Emitir: escolher um modelo preenche cliente, serviço e valor.
document.addEventListener("change", (ev) => {
  const sel = ev.target;
  if (sel.name !== "modelo_id") return;
  const op = sel.selectedOptions[0];
  if (!op || !op.dataset.cliente) return;
  document.querySelector('[name="cliente_id"]').value = op.dataset.cliente;
  document.querySelector('[name="servico_id"]').value = op.dataset.servico;
  document.querySelector('[name="valor"]').value = op.dataset.valor;
});
