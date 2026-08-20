// Agent Ledger — landing page
// Sem dependência externa: sem CDN, sem framework, sem chamada de rede além do link do WhatsApp.

const WHATSAPP_NUMBER = "5521982301476"; // formato internacional, só dígitos

const MESSAGES = {
  pt: "Olá! Vi o Agent Ledger e quero saber mais sobre a auditoria de agente de IA.",
  en: "Hi! I saw Agent Ledger and I'd like to know more about the AI agent audit."
};

const I18N = {
  pt: {
    cta_short: "Falar no WhatsApp",
    cta_full: "Pedir uma auditoria pelo WhatsApp",
    hero_eyebrow: "AI Eval Audit · metodologia DOUVRAS",
    hero_title: "Não dizemos que seu agente de IA funciona.<br>Provamos — ou provamos que não.",
    hero_lede: "Auditoria independente de agentes de IA e modelos de linguagem: tool calling, JSON, recuperação de erro, alucinação, segurança. Cada número vem de execução real, com o método que aplicamos primeiro contra nós mesmos.",
    hero_secondary: "Ver a prova antes de falar com a gente",
    proof_title: "Prova, não promessa",
    proof_lede: "Três coisas que já aconteceram nesta pesquisa — verificáveis no repositório público, não alegação de marketing.",
    proof1_tag: "DEFEITO ENCONTRADO EM MODELO PUBLICADO",
    proof1_title: "Achamos um bug que não era nosso",
    proof1_body: "O template de chat publicado dentro de um modelo GGUF real fecha a tag de instrução no lugar errado — qualquer ferramenta padrão (llama-server, Ollama, LM Studio) recebe saída degenerada desse modelo sem saber por quê.",
    proof2_tag: "DERRUBAMOS NOSSA PRÓPRIA HIPÓTESE",
    proof2_title: "Publicamos quando erramos, no mesmo ciclo",
    proof2_body: "Registramos a hipótese de que modelos pequenos não chamam ferramenta. O segundo modelo que testamos — nós mesmos — a derrubou horas depois. A retratação foi publicada junto, não escondida.",
    proof2_col1: "Modelo",
    proof2_col2: "Chamadas de ferramenta",
    proof3_tag: "CONTRA O PRÓPRIO INTERESSE",
    proof3_title: "Dissemos quando nosso próprio placar não presta",
    proof3_body: "O escore agregado do nosso benchmark não separa um agente correto de um degenerado com confiança suficiente — e publicamos isso mesmo sendo desfavorável ao nosso instrumento. Se o placar de IA que você usa hoje nunca admitiu um limite, vale perguntar por quê.",
    deliver_title: "O que você recebe",
    deliver_lede: "Um relatório de agente, com número reproduzível em cada linha — não impressão, execução.",
    report_head: "Agent Evaluation Report — seu agente",
    metric_tool: "Tool use",
    metric_instr: "Instruction following",
    metric_halluc: "Hallucination",
    metric_recovery: "Error recovery",
    metric_json: "JSON compliance",
    metric_security: "Security",
    report_foot: "17 falhas críticas · 38 falhas altas · dataset de falhas incluído",
    report_note: "Números ilustrativos — o relatório do seu agente é gerado a partir da execução real dele, não preenchido a mão.",
    step1_t: "1. Você nos dá acesso",
    step1_d: "ao agente, modelo ou API — ou só aos logs, se preferir não expor o sistema.",
    step2_t: "2. Rodamos a auditoria",
    step2_d: "centenas de tarefas com gabarito e contraexemplo, grader determinístico, sem depender de outro LLM para julgar.",
    step3_t: "3. Você recebe o relatório",
    step3_d: "com as falhas priorizadas, o dataset reproduzível, e uma chamada para revisar junto.",
    pricing_title: "Como começar",
    pricing_label_br: "Brasil · primeiros casos",
    pricing_label_intl: "Internacional · pacote",
    pricing_note: "Dois preços diferentes de propósito: o valor em reais é de entrada, pra construir os primeiros casos reais no Brasil. O pacote internacional já reflete referência de mercado (Upwork, projetos de ML/eval). Customizações (benchmark específico do seu domínio, dataset de treino) sob consulta nos dois casos.",
    pricing_fx_note: "Câmbio de referência 15/08/2026: US$ 1 ≈ R$ 5,11 · € 1 ≈ R$ 5,98. Conversão ilustrativa, não cotação de fechamento de negócio.",
    about_title: "Como isso é construído",
    about_body: "A infraestrutura por trás desta auditoria é o método <b>DOUVRAS</b> — Delimitação, Observação, Unificação, Validação, Redução, Arquitetura e Sistematização — desenvolvido para exigir que toda alegação venha com evidência, toda lacuna seja registrada, e toda hipótese tenha um jeito declarado de ser derrubada antes de ser testada.",
    about_body2: "O código, o corpus de tarefas, os relatórios e as retratações são públicos.",
    about_link: "Ver o repositório →"
  },
  en: {
    cta_short: "Chat on WhatsApp",
    cta_full: "Request an audit on WhatsApp",
    hero_eyebrow: "AI Eval Audit · DOUVRAS methodology",
    hero_title: "We don't tell you your AI agent works.<br>We prove it — or prove it doesn't.",
    hero_lede: "Independent evaluation of AI agents and language models: tool calling, JSON, error recovery, hallucination, security. Every number comes from a real run, using the same method we apply to ourselves first.",
    hero_secondary: "See the proof before you talk to us",
    proof_title: "Proof, not promises",
    proof_lede: "Three things that already happened in this research — verifiable in the public repository, not marketing copy.",
    proof1_tag: "DEFECT FOUND IN A PUBLISHED MODEL",
    proof1_title: "We found a bug that wasn't ours",
    proof1_body: "The chat template published inside a real GGUF model closes the instruction tag in the wrong place — any standard tool (llama-server, Ollama, LM Studio) gets degenerate output from that model without knowing why.",
    proof2_tag: "WE DISPROVED OUR OWN HYPOTHESIS",
    proof2_title: "We publish when we're wrong, same cycle",
    proof2_body: "We registered the hypothesis that small models don't call tools. The second model we tested — ourselves — disproved it hours later. The retraction was published alongside it, not hidden.",
    proof2_col1: "Model",
    proof2_col2: "Tool calls",
    proof3_tag: "AGAINST OUR OWN INTEREST",
    proof3_title: "We say it when our own scoreboard isn't good enough",
    proof3_body: "Our benchmark's aggregate score doesn't separate a correct agent from a degenerate one with enough confidence — and we published that even though it's unfavorable to our own instrument. If the AI scoreboard you use today has never admitted a limit, that's worth asking about.",
    deliver_title: "What you get",
    deliver_lede: "An agent report where every line is a reproducible number — not an impression, an execution.",
    report_head: "Agent Evaluation Report — your agent",
    metric_tool: "Tool use",
    metric_instr: "Instruction following",
    metric_halluc: "Hallucination",
    metric_recovery: "Error recovery",
    metric_json: "JSON compliance",
    metric_security: "Security",
    report_foot: "17 critical failures · 38 high failures · failure dataset included",
    report_note: "Illustrative numbers — your agent's report is generated from its actual run, not filled in by hand.",
    step1_t: "1. You give us access",
    step1_d: "to the agent, model, or API — or just the logs, if you'd rather not expose the system.",
    step2_t: "2. We run the audit",
    step2_d: "hundreds of tasks with gold answers and counterexamples, deterministic grading, no other LLM used as judge.",
    step3_t: "3. You get the report",
    step3_d: "with failures prioritized, a reproducible dataset, and a call to review it together.",
    pricing_title: "How to start",
    pricing_label_br: "Brazil · first cases",
    pricing_label_intl: "International · package",
    pricing_note: "Two different prices on purpose: the BRL figure is entry pricing to build the first real cases in Brazil. The international package already reflects market reference (Upwork, ML/eval projects). Customization (domain-specific benchmark, training dataset) on request either way.",
    pricing_fx_note: "Reference rate as of 2026-08-15: US$1 ≈ R$5.11 · €1 ≈ R$5.98. Illustrative conversion, not a deal-closing quote.",
    about_title: "How this is built",
    about_body: "The infrastructure behind this audit is the <b>DOUVRAS</b> method — Delimitation, Observation, Unification, Validation, Reduction, Architecture and Systematization — built to require that every claim ship with evidence, every gap get registered, and every hypothesis have a declared way to be proven wrong before it's tested.",
    about_body2: "The code, the task corpus, the reports, and the retractions are all public.",
    about_link: "See the repository →"
  }
};

function waLink(lang) {
  const text = encodeURIComponent(MESSAGES[lang] || MESSAGES.pt);
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${text}`;
}

function applyLang(lang) {
  const dict = I18N[lang] || I18N.pt;
  document.documentElement.lang = lang === "en" ? "en" : "pt";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (dict[key] !== undefined) el.innerHTML = dict[key];
  });
  ["ctaTop", "ctaHero", "ctaPricing", "ctaFooter"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.href = waLink(lang);
  });
  const toggle = document.getElementById("langToggle");
  if (toggle) toggle.textContent = lang === "en" ? "PT" : "EN";
  localStorage.setItem("agentledger_lang", lang);
}

(function init() {
  const saved = localStorage.getItem("agentledger_lang");
  const browserLang = (navigator.language || "pt").toLowerCase().startsWith("pt") ? "pt" : "en";
  let current = saved || browserLang;

  applyLang(current);

  const toggle = document.getElementById("langToggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      current = current === "en" ? "pt" : "en";
      applyLang(current);
    });
  }
})();
