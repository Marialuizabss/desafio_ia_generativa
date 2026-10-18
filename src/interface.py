"""Interface de entrada da Central de Atendimento.

Toda a definição visual fica neste módulo. O `main` só a executa.

Depois da confirmação, a entrada fica em ``st.session_state["entrada"]``:

- ``modalidade``: ``"texto"``, ``"audio"`` ou ``"imagem"``
- ``origem``: ``"cola"`` ou ``"arquivo"``
- ``texto``: solicitação escrita, ou ``None``
- ``nome_arquivo``: nome enviado, ou o nome gerado para o texto colado
- ``caminho_copia``: caminho relativo da cópia em ``dados/originais/``
- ``preservou_existente``: a cópia não reescreveu um arquivo que já estava na pasta
- ``tipo_mime``: tipo do arquivo
- ``tamanho_bytes``: tamanho do texto ou do arquivo
- ``conteudo``: bytes guardados

A escolha do modelo fica em ``st.session_state["configuracao_modelo"]``:

- ``modelo``: id escolhido em ``config/modelos.json``
- ``parametros``: idioma, temperatura, tamanho e qualidade que se aplicam
  a esse modelo, já com o que o usuário alterou
"""

from html import escape
from pathlib import Path

import streamlit as st

try:
    from fluxo import aplicar_edicao, processar_entrada
except ImportError:
    from src.fluxo import aplicar_edicao, processar_entrada

try:
    from src.configuracao import carregar_modelos, obter_modelo, parametros_aplicaveis, rotulo_da_opcao
    from src.extracao import CATEGORIAS, VALOR_AUSENTE
except ImportError:
    from configuracao import carregar_modelos, obter_modelo, parametros_aplicaveis, rotulo_da_opcao
    from extracao import CATEGORIAS, VALOR_AUSENTE

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_ORIGINAIS = BASE_DIR / "dados" / "originais"

# Marcador que o modelo copia do modelo de minuta; a interface troca pela imagem
MARCADOR_BRASAO = "[CABEÇALHO COM BRASÃO — dados/originais/brasao.png]"
BRASAO = PASTA_ORIGINAIS / "brasao.png"

MODALIDADES = (
    ("texto", "Texto", "Cole o pedido ou envie um .txt", ":material/edit_note:"),
    ("audio", "Áudio", "Envie o arquivo de voz", ":material/graphic_eq:"),
    ("imagem", "Imagem ou PDF", "Envie a ficha digitalizada", ":material/document_scanner:"),
)

ROTULOS = {chave: titulo for chave, titulo, *_ in MODALIDADES}

EXTENSOES = {
    "texto": {".txt"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".webm"},
    "imagem": {".png", ".jpg", ".jpeg", ".webp", ".pdf"},
}

TIPOS_UPLOAD = {
    "texto": ["txt"],
    "audio": ["mp3", "wav", "m4a", "ogg", "webm"],
    "imagem": ["png", "jpg", "jpeg", "webp", "pdf"],
}

LIMITE_BYTES = {
    "texto": 5 * 1024 * 1024,
    "audio": 25 * 1024 * 1024,
    "imagem": 20 * 1024 * 1024,
}

MENSAGEM_VAZIA = {
    "texto": "Cole o pedido ou envie um .txt para continuar.",
    "audio": "Envie o arquivo de voz para continuar.",
    "imagem": "Envie a ficha digitalizada para continuar.",
}

MIME_AUDIO = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
}

LIMITE_TEXTO = 20_000

ROTULOS_CAMPOS = (
    ("solicitante", "Solicitante"),
    ("protocolo", "Protocolo"),
    ("data_solicitacao", "Data"),
    ("curso", "Curso"),
    ("eixo", "Eixo"),
    ("carga_horaria", "Carga horária"),
    ("turno", "Turno"),
    ("data_inicio", "Início"),
    ("regras_ciencia", "Ciência das regras"),
    ("documentos_necessarios", "Documentos"),
    ("prazo_apresentacao", "Prazo"),
    ("local_horario", "Local e horário"),
)

ROTULOS_CATEGORIA = {
    "matricula": "Matrícula",
    "documentacao": "Documentação",
    "frequencia_cancelamento": "Frequência e cancelamento",
    "informacao_geral": "Informação geral",
    "reclamacao": "Reclamação",
    "outros": "Outros",
}

CAMPOS_LONGOS = {"regras_ciencia", "documentos_necessarios", "local_horario"}

ROTULOS_PARAMETRO = {
    "idioma": "Idioma",
    "temperatura": "Temperatura",
    "tamanho": "Tamanho",
    "qualidade": "Qualidade",
}

ETAPAS = (
    (1, "Modelo", "Modelo e idioma", "Escolha quem vai ler a solicitação."),
    (2, "Envio", "Forma de envio", "Escolha como o pedido chega e confira o que será enviado."),
    (3, "Revisão", "Avaliação humana", "Confira os campos extraídos e ajuste o que for preciso."),
    (4, "Minuta", "Minuta", "Rascunho montado com os campos revisados."),
)

ESTILOS = """
<style>
  :root {
    --verde: #4169E1;
    --verde-escuro: #2746C4;
    --tinta: #172033;
    --apoio: #5C6B86;
    --linha: #D5DFF2;
    --folha: #FFFFFF;
    --fundo: #E8EEF9;
    --suave: #F4F7FC;
    --serif: "Iowan Old Style", Palatino, "Palatino Linotype", Georgia, serif;
    --sans: "Avenir Next", "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
  }

  html, body, [class*="css"] {
    font-family: var(--sans);
  }

  .stApp {
    background: var(--fundo);
    color: var(--tinta);
  }

  [data-testid="stHeader"],
  [data-testid="stToolbar"] {
    background: transparent;
  }

  [data-testid="stToolbar"] {
    display: none;
  }

  footer {
    display: none;
  }

  [data-testid="stMainBlockContainer"],
  .block-container {
    max-width: 640px;
    margin-left: auto;
    margin-right: auto;
    padding-top: 2.4rem;
    padding-bottom: 2.4rem;
  }

  .st-key-folha {
    background: var(--folha);
    border: 1px solid var(--linha);
    border-radius: 16px;
    padding: 1.15rem 1.25rem 1rem;
    box-shadow: 0 18px 48px rgba(22, 46, 36, 0.06);
  }

  .st-key-palco > div[data-testid="stVerticalBlock"] {
    gap: 1.35rem;
  }

  .st-key-palco_avancar,
  .st-key-palco_voltar {
    animation-duration: 0.42s;
    animation-timing-function: cubic-bezier(.22, .7, .25, 1);
    animation-fill-mode: both;
  }

  .st-key-palco_avancar {
    animation-name: deslizar-avancar;
  }

  .st-key-palco_voltar {
    animation-name: deslizar-voltar;
  }

  @keyframes deslizar-avancar {
    from { opacity: 0; transform: translateX(1.75rem); }
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes deslizar-voltar {
    from { opacity: 0; transform: translateX(-1.75rem); }
    to { opacity: 1; transform: translateX(0); }
  }

  @media (prefers-reduced-motion: reduce) {
    .st-key-palco_avancar,
    .st-key-palco_voltar {
      animation: none;
    }
  }

  .topo .filete {
    width: 2.4rem;
    height: 2px;
    margin: 0 0 1.15rem;
    border-radius: 2px;
    background: var(--verde);
  }

  .marca {
    margin: 0 0 0.85rem;
    color: var(--apoio);
    font-size: 0.64rem;
    font-weight: 650;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .passos {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.55rem;
    margin: 0 0 1.15rem;
    padding: 0;
    list-style: none;
  }

  .passos li {
    margin: 0;
    padding-top: 0.4rem;
    border-top: 2px solid var(--linha);
    color: #8A97B0;
    font-size: 0.64rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    line-height: 1.3;
    text-align: center;
  }

  .passos li.feita {
    border-color: #8EAAE8;
    color: #2A3A66;
  }

  .passos li.atual {
    border-color: var(--verde);
    color: var(--verde);
  }

  .topo .selo,
  .rotulo {
    margin: 0;
    color: var(--verde);
    font-size: 0.64rem;
    font-weight: 650;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .topo h1 {
    margin: 0.15rem 0 0.2rem;
    color: var(--tinta);
    font-family: var(--serif);
    font-size: 1.35rem;
    font-weight: 500;
    letter-spacing: -0.03em;
    line-height: 1.15;
  }

  .topo .apoio,
  .orientacao {
    margin: 0;
    color: var(--apoio);
    font-size: 0.75rem;
    line-height: 1.45;
  }

  .rotulo {
    margin: 0 0 0.35rem;
    color: #3A4A72;
    font-size: 0.6rem;
    letter-spacing: 0.08em;
  }

  [data-testid="stWidgetLabel"] p {
    font-size: 0.75rem;
  }

  [data-testid="stCaptionContainer"] p {
    font-size: 0.72rem;
  }

  .divisoria {
    margin: 0.85rem 0 0.35rem;
    color: var(--apoio);
    font-size: 0.68rem;
    font-weight: 650;
    letter-spacing: 0.12em;
    line-height: 1.3;
    text-align: center;
    text-transform: uppercase;
  }

  .st-key-escolher_texto [data-testid="stBaseButton-secondary"],
  .st-key-escolher_audio [data-testid="stBaseButton-secondary"],
  .st-key-escolher_imagem [data-testid="stBaseButton-secondary"],
  .st-key-escolher_texto [data-testid="stBaseButton-primary"],
  .st-key-escolher_audio [data-testid="stBaseButton-primary"],
  .st-key-escolher_imagem [data-testid="stBaseButton-primary"],
  .st-key-prosseguir [data-testid="stBaseButton-primary"],
  .st-key-voltar [data-testid="stBaseButton-secondary"] {
    border-radius: 10px !important;
    min-height: 2.35rem;
    font-size: 0.84rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    box-shadow: none !important;
  }

  .st-key-escolher_texto [data-testid="stBaseButton-secondary"],
  .st-key-escolher_audio [data-testid="stBaseButton-secondary"],
  .st-key-escolher_imagem [data-testid="stBaseButton-secondary"] {
    border: 1px solid var(--linha) !important;
    background: var(--folha) !important;
    color: var(--tinta) !important;
  }

  .st-key-escolher_texto [data-testid="stBaseButton-secondary"]:hover,
  .st-key-escolher_audio [data-testid="stBaseButton-secondary"]:hover,
  .st-key-escolher_imagem [data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--verde) !important;
    color: var(--verde) !important;
  }

  .st-key-escolher_texto [data-testid="stBaseButton-primary"],
  .st-key-escolher_audio [data-testid="stBaseButton-primary"],
  .st-key-escolher_imagem [data-testid="stBaseButton-primary"] {
    border: 1px solid var(--verde) !important;
    background: var(--verde) !important;
    color: #FFFFFF !important;
  }

  .st-key-escolher_texto [data-testid="stBaseButton-primary"]:hover,
  .st-key-escolher_audio [data-testid="stBaseButton-primary"]:hover,
  .st-key-escolher_imagem [data-testid="stBaseButton-primary"]:hover {
    border-color: var(--verde-escuro) !important;
    background: var(--verde-escuro) !important;
    color: #FFFFFF !important;
  }

  .st-key-coluna_texto [data-testid="stCaptionContainer"],
  .st-key-coluna_audio [data-testid="stCaptionContainer"],
  .st-key-coluna_imagem [data-testid="stCaptionContainer"] {
    text-align: center;
    margin-top: -0.15rem;
  }

  .st-key-coluna_texto [data-testid="stCaptionContainer"] p,
  .st-key-coluna_audio [data-testid="stCaptionContainer"] p,
  .st-key-coluna_imagem [data-testid="stCaptionContainer"] p {
    color: var(--apoio);
    font-size: 0.74rem;
  }

  [data-testid="stTextArea"] textarea {
    border: 1px solid var(--linha);
    border-radius: 10px;
    background: var(--suave);
    color: var(--tinta);
    font-size: 0.9rem;
    line-height: 1.45;
    padding: 0.55rem 0.75rem;
  }

  [data-testid="stTextArea"] textarea:focus {
    border-color: var(--verde);
    box-shadow: 0 0 0 3px rgba(65, 105, 225, 0.16);
  }

  [data-testid="stTextInput"] input {
    border: 1px solid var(--linha);
    border-radius: 10px;
    background: var(--suave);
    color: var(--tinta);
    font-size: 0.9rem;
    padding-top: 0.35rem;
    padding-bottom: 0.35rem;
  }

  [data-testid="stTextInput"] input:focus {
    border-color: var(--verde);
    box-shadow: 0 0 0 3px rgba(65, 105, 225, 0.16);
  }

  [data-testid="stFileUploaderDropzone"] {
    border: 1px dashed #C5D2EA;
    border-radius: 14px;
    background: var(--suave);
    padding: 0.85rem 1rem;
  }

  [data-testid="stFileUploaderDropzone"]:hover,
  [data-testid="stFileUploaderDropzone"]:focus-within {
    border-color: var(--verde);
    background: #F3F6FC;
  }

  [data-testid="stFileUploaderDropzoneInstructions"] span {
    font-size: 0;
    color: var(--apoio);
  }

  [data-testid="stFileUploaderDropzoneInstructions"] span::after {
    content: "ou solte o arquivo aqui";
    font-size: 0.8rem;
    line-height: 1.4;
    color: var(--apoio);
  }

  [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] {
    border: none !important;
    border-radius: 10px !important;
    background: var(--verde) !important;
    color: #FFFFFF !important;
  }

  [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"]:hover {
    background: var(--verde-escuro) !important;
    color: #FFFFFF !important;
  }

  [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] p {
    font-size: 0;
  }

  [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] p::after {
    content: "Escolher";
    font-size: 0.95rem;
    line-height: 1.2;
  }

  .contador {
    margin: -0.2rem 0 0.2rem;
    color: var(--apoio);
    font-size: 0.82rem;
    text-align: right;
  }

  .contador.limite {
    color: #8A4B32;
  }

  .aviso {
    margin: 0.2rem 0 0;
    color: #8A4B32;
    font-size: 0.92rem;
  }

  .st-key-modelo {
    margin-top: 0;
    padding-top: 0;
  }

  .st-key-modelo [data-baseweb="select"] > div {
    border-radius: 14px;
    border-color: var(--linha);
    background: var(--suave);
  }

  .st-key-modelo [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: var(--verde);
  }

  .st-key-restaurar_padroes {
    margin-top: 0.15rem;
  }

  .st-key-restaurar_padroes [data-testid="stBaseButton-secondary"] {
    border: 1px solid var(--linha) !important;
    border-radius: 14px !important;
    background: transparent !important;
    color: var(--verde) !important;
    min-height: 2.7rem;
    font-weight: 600;
    box-shadow: none !important;
  }

  .st-key-restaurar_padroes [data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--verde) !important;
    color: var(--verde-escuro) !important;
  }

  .st-key-prosseguir [data-testid="stBaseButton-primary"] {
    border: none !important;
    background: var(--verde) !important;
    color: #FFFFFF !important;
  }

  .st-key-prosseguir [data-testid="stBaseButton-primary"]:hover {
    background: var(--verde-escuro) !important;
    color: #FFFFFF !important;
  }

  .st-key-prosseguir [data-testid="stBaseButton-primary"]:disabled {
    border: none !important;
    background: #E4EAF6 !important;
    color: #8A97B0 !important;
  }

  .st-key-voltar [data-testid="stBaseButton-secondary"] {
    border: 1px solid var(--linha) !important;
    background: transparent !important;
    color: var(--verde) !important;
  }

  .st-key-voltar [data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--verde) !important;
    color: var(--verde-escuro) !important;
  }

  .st-key-edicao [data-baseweb="select"] > div {
    border-radius: 14px;
    border-color: var(--linha);
    background: var(--suave);
  }

  .titulo-entrada {
    margin: 0.15rem 0 0.85rem;
    color: var(--tinta);
    font-family: var(--serif);
    font-size: clamp(1.7rem, 3vw, 2rem);
    font-weight: 500;
    letter-spacing: -0.03em;
    line-height: 1.1;
  }

  button:focus-visible {
    outline: 2px solid var(--verde);
    outline-offset: 2px;
  }

  .ficha {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.85rem 1.4rem;
    margin: 0.3rem 0 0.4rem;
  }

  .ficha .amplo {
    grid-column: 1 / -1;
  }

  .ficha dt {
    margin: 0;
    color: var(--apoio);
    font-size: 0.66rem;
    font-weight: 650;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .ficha dd {
    margin: 0.18rem 0 0;
    color: var(--tinta);
    font-size: 0.9rem;
    line-height: 1.4;
    overflow-wrap: anywhere;
  }

  .trecho {
    margin: 0.15rem 0 0;
    padding: 0.65rem 0.8rem;
    border-left: 2px solid var(--verde);
    border-radius: 0 10px 10px 0;
    background: var(--suave);
    color: var(--tinta);
    font-size: 0.84rem;
    line-height: 1.45;
  }

  [data-testid="stImage"] img {
    border: 1px solid #E1E7F4;
    border-radius: 12px;
  }

  @media (max-width: 700px) {
    [data-testid="stMainBlockContainer"],
    .block-container {
      padding-top: 1.3rem;
    }

    .st-key-folha {
      padding: 0.95rem 0.85rem 0.8rem;
      border-radius: 14px;
    }

    .passos {
      gap: 0.35rem;
    }

    .st-key-seletor [data-testid="stHorizontalBlock"] {
      flex-direction: column;
      gap: 0.35rem;
    }

    .ficha {
      grid-template-columns: 1fr;
    }
  }
</style>
"""


def obter_entrada() -> dict | None:
    """Devolve a entrada confirmada nesta sessão."""
    if not st.session_state.get("confirmada"):
        return None
    return st.session_state.get("entrada")


def renderizar() -> None:
    """Desenha uma etapa por vez e guarda a escolha na sessão."""
    st.set_page_config(
        page_title="Central de atendimento",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(ESTILOS, unsafe_allow_html=True)
    _iniciar_estado()
    _ajustar_etapa()
    animacao = st.session_state.animacao
    st.session_state.animacao = ""

    with st.container(key="folha"):
        st.markdown('<p class="marca">Central de atendimento</p>', unsafe_allow_html=True)
        _passos()
        with st.container(key=f"palco_{animacao}" if animacao else "palco"):
            _titulo_da_etapa()
            if st.session_state.etapa == 1:
                _etapa_modelo()
            elif st.session_state.etapa == 2:
                _etapa_envio()
            elif st.session_state.etapa == 3:
                _etapa_revisao()
            else:
                _etapa_minuta()


def _iniciar_estado() -> None:
    st.session_state.setdefault("etapa", 1)
    st.session_state.setdefault("animacao", "")
    st.session_state.setdefault("modalidade", "texto")
    st.session_state.setdefault("confirmada", False)
    st.session_state.setdefault("entrada", None)
    st.session_state.setdefault("texto_guardado", "")
    st.session_state.setdefault("erro", None)
    st.session_state.setdefault("extracao_chave", None)
    st.session_state.setdefault("extracao_registro", None)
    st.session_state.setdefault("extracao_erro", None)
    st.session_state.setdefault("extracao_forcar", False)
    st.session_state.setdefault("edicao_id", None)
    st.session_state.setdefault("minuta_erro", None)


def _ajustar_etapa() -> None:
    etapa = int(st.session_state.get("etapa") or 1)
    if etapa > 2 and not st.session_state.get("entrada"):
        etapa = 2
    registro = st.session_state.get("extracao_registro") or {}
    if etapa > 3 and not registro.get("minuta_gerada_de_campos"):
        etapa = 3
    st.session_state.etapa = etapa


def _ir(destino: int) -> None:
    _guardar_rascunho()
    _guardar_edicao()
    destino = max(1, min(4, int(destino)))
    atual = int(st.session_state.get("etapa") or 1)
    if destino == atual:
        return
    st.session_state.animacao = "avancar" if destino > atual else "voltar"
    st.session_state.etapa = destino


def _guardar_rascunho() -> None:
    if "rascunho_texto" in st.session_state:
        st.session_state.texto_guardado = st.session_state.rascunho_texto or ""


def _chaves_edicao() -> tuple[str, ...]:
    return ("edit_categoria", "edit_assunto", "edit_pedido", *(f"edit_{nome}" for nome, _ in ROTULOS_CAMPOS))


def _guardar_edicao() -> None:
    if "edit_assunto" not in st.session_state:
        return
    st.session_state.edicao_guardada = {
        chave: st.session_state.get(chave) for chave in _chaves_edicao()
    }
    st.session_state.edicao_id_guardada = st.session_state.get("edicao_id")


def _passos() -> None:
    atual = st.session_state.etapa
    itens = []
    for numero, nome, *_ in ETAPAS:
        if numero == atual:
            classe = "atual"
        elif numero < atual:
            classe = "feita"
        else:
            classe = ""
        itens.append(f'<li class="{classe}">{numero} {escape(nome)}</li>')
    st.markdown(f'<ol class="passos">{"".join(itens)}</ol>', unsafe_allow_html=True)


def _titulo_da_etapa() -> None:
    _, _, titulo, apoio = ETAPAS[st.session_state.etapa - 1]
    st.markdown(
        f"""
        <header class="topo">
          <p class="selo">Etapa {st.session_state.etapa} de 4</p>
          <h1>{escape(titulo)}</h1>
          <p class="apoio">{escape(apoio)}</p>
        </header>
        """,
        unsafe_allow_html=True,
    )


def _navegacao(prosseguir=None, desabilitado: bool = False) -> None:
    if st.session_state.etapa == 1:
        st.button(
            "Prosseguir",
            key="prosseguir",
            type="primary",
            width="stretch",
            disabled=desabilitado or prosseguir is None,
            on_click=prosseguir,
        )
        return

    if prosseguir is None:
        st.button(
            "Voltar",
            key="voltar",
            width="stretch",
            on_click=_ir,
            args=(st.session_state.etapa - 1,),
        )
        return

    voltar, seguir = st.columns(2, gap="small")
    with voltar:
        st.button(
            "Voltar",
            key="voltar",
            width="stretch",
            on_click=_ir,
            args=(st.session_state.etapa - 1,),
        )
    with seguir:
        st.button(
            "Prosseguir",
            key="prosseguir",
            type="primary",
            width="stretch",
            disabled=desabilitado,
            on_click=prosseguir,
        )


def _etapa_modelo() -> None:
    _secao_modelo()
    _navegacao(_prosseguir_modelo)


def _prosseguir_modelo() -> None:
    _ir(2)


def _prosseguir_envio() -> None:
    _confirmar()
    if st.session_state.erro or not st.session_state.get("entrada"):
        return
    _ir(3)


def _prosseguir_revisao() -> None:
    _gerar_minuta_editada()
    if st.session_state.minuta_erro:
        return
    _ir(4)


def _etapa_envio() -> None:
    modalidade = st.session_state.modalidade
    _seletor()
    if modalidade == "texto":
        arquivo = _campo_texto()
    else:
        arquivo = _campo_arquivo(modalidade)

    pendencia = _pendencia(modalidade, arquivo)
    if st.session_state.erro:
        st.markdown(
            f'<p class="aviso">{escape(st.session_state.erro)}</p>',
            unsafe_allow_html=True,
        )
    elif pendencia:
        st.caption(pendencia)
    else:
        _selecionado(modalidade, arquivo)
    _navegacao(_prosseguir_envio, desabilitado=pendencia is not None)


def _selecionado(modalidade: str, arquivo) -> None:
    material, erro = receber_material(modalidade, arquivo)
    if erro or material is None:
        return
    if material.get("origem") == "cola":
        origem = "Texto colado"
        tamanho = f"{_formatar_inteiro(len(material['texto']))} caracteres"
    elif modalidade == "texto":
        origem = material["nome_arquivo"] or "Arquivo .txt"
        tamanho = f"{_formatar_inteiro(len(material['texto']))} caracteres"
    else:
        origem = material["nome_arquivo"] or "Arquivo"
        tamanho = formatar_tamanho(material["tamanho_bytes"])
    st.markdown(
        f"""
        <dl class="ficha">
          <div><dt>Selecionado</dt><dd>{escape(ROTULOS[modalidade])}</dd></div>
          <div><dt>Origem</dt><dd>{escape(origem)}</dd></div>
          <div class="amplo"><dt>Tamanho</dt><dd>{escape(tamanho)}</dd></div>
        </dl>
        """,
        unsafe_allow_html=True,
    )


def _etapa_revisao() -> None:
    _mostrar_extracao(st.session_state.entrada)
    if st.session_state.minuta_erro:
        st.markdown(
            f'<p class="aviso">{escape(st.session_state.minuta_erro)}</p>',
            unsafe_allow_html=True,
        )
    pronto = bool(st.session_state.extracao_registro) and not st.session_state.extracao_erro
    _navegacao(_prosseguir_revisao if pronto else None, desabilitado=not pronto)


def _etapa_minuta() -> None:
    registro = st.session_state.extracao_registro or {}
    minuta = (registro.get("minuta") or "").strip()
    com_brasao, texto = preparar_minuta(minuta)
    if com_brasao and BRASAO.is_file():
        st.image(str(BRASAO), width=88)
    st.markdown(texto)
    st.caption("Revisão humana obrigatória antes de qualquer envio.")
    _navegacao(None)


def _secao_modelo() -> None:
    try:
        config = carregar_modelos()
    except ValueError as erro:
        st.markdown(
            f'<p class="aviso">{escape(str(erro))}</p>',
            unsafe_allow_html=True,
        )
        return

    ids = [modelo["id"] for modelo in config["modelos"]]
    if st.session_state.get("modelo_escolhido") not in ids:
        st.session_state.modelo_escolhido = config["modelo_padrao"]
    modelo = obter_modelo(config, st.session_state.modelo_escolhido)
    for nome, valor in parametros_aplicaveis(modelo).items():
        st.session_state.setdefault(f"cfg_{nome}", valor)

    with st.container(key="modelo"):
        st.selectbox(
            "Modelo",
            ids,
            key="modelo_escolhido",
            format_func=lambda modelo_id: obter_modelo(config, modelo_id)["nome"],
            on_change=_ao_trocar_modelo,
            label_visibility="collapsed",
            persist_state="session",
        )
        modelo = obter_modelo(config, st.session_state.modelo_escolhido)
        st.caption(modelo["descricao"])
        _parametros_do_modelo(config, modelo)
        if _parametros_alterados(modelo):
            st.button(
                "Restaurar padrões",
                key="restaurar_padroes",
                width="stretch",
                on_click=_restaurar_padroes,
            )
        _guardar_configuracao(modelo)


def _parametros_do_modelo(config: dict, modelo: dict) -> None:
    nomes = list(parametros_aplicaveis(modelo))
    if not nomes:
        return
    colunas = st.columns(len(nomes), gap="small")
    for coluna, nome in zip(colunas, nomes):
        with coluna:
            if nome == "temperatura":
                faixa = config["temperatura"]
                st.slider(
                    ROTULOS_PARAMETRO[nome],
                    min_value=faixa["minimo"],
                    max_value=faixa["maximo"],
                    step=faixa["passo"],
                    key="cfg_temperatura",
                    persist_state="session",
                )
                continue
            opcoes = [item["valor"] for item in config["opcoes"][nome]]
            st.selectbox(
                ROTULOS_PARAMETRO[nome],
                opcoes,
                key=f"cfg_{nome}",
                format_func=lambda valor, parametro=nome: rotulo_da_opcao(config, parametro, valor),
                persist_state="session",
            )


def _guardar_configuracao(modelo: dict) -> None:
    st.session_state.configuracao_modelo = {
        "modelo": modelo["id"],
        "parametros": {
            nome: st.session_state.get(f"cfg_{nome}")
            for nome in parametros_aplicaveis(modelo)
        },
    }


def _parametros_alterados(modelo: dict) -> bool:
    for nome, padrao in parametros_aplicaveis(modelo).items():
        atual = st.session_state.get(f"cfg_{nome}")
        if isinstance(padrao, float):
            if atual is None or abs(float(atual) - padrao) > 0.001:
                return True
        elif atual != padrao:
            return True
    return False


def _ao_trocar_modelo() -> None:
    config = carregar_modelos()
    modelo = obter_modelo(config, st.session_state.modelo_escolhido)
    for nome, valor in parametros_aplicaveis(modelo).items():
        st.session_state[f"cfg_{nome}"] = valor


def _restaurar_padroes() -> None:
    _ao_trocar_modelo()


def _seletor() -> None:
    with st.container(key="seletor"):
        colunas = st.columns(3, gap="small")
        for coluna, (chave, titulo, descricao, icone) in zip(colunas, MODALIDADES):
            with coluna:
                with st.container(key=f"coluna_{chave}"):
                    selecionada = st.session_state.modalidade == chave
                    st.button(
                        titulo,
                        key=f"escolher_{chave}",
                        type="primary" if selecionada else "secondary",
                        icon=icone,
                        width="stretch",
                        on_click=_escolher,
                        args=(chave,),
                    )
                    st.caption(descricao)


def _campo_texto():
    st.markdown('<p class="rotulo">Solicitação</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="orientacao">Cole o pedido ou envie um arquivo .txt.</p>',
        unsafe_allow_html=True,
    )
    if "rascunho_texto" not in st.session_state:
        entrada = st.session_state.get("entrada") or {}
        guardado = st.session_state.texto_guardado
        if not guardado and entrada.get("origem") == "cola":
            guardado = entrada.get("texto") or ""
        st.session_state.rascunho_texto = guardado
    texto = st.text_area(
        "Solicitação",
        key="rascunho_texto",
        height=120,
        label_visibility="collapsed",
        placeholder="Descreva quem solicita, o curso, o turno e o que precisa ser resolvido.",
        persist_state="session",
    )
    st.session_state.texto_guardado = texto
    quantidade = len(texto.strip())
    classe = "contador limite" if quantidade > LIMITE_TEXTO else "contador"
    st.markdown(
        f'<p class="{classe}">{_formatar_inteiro(quantidade)} caracteres</p>',
        unsafe_allow_html=True,
    )
    st.markdown('<p class="divisoria">ou</p>', unsafe_allow_html=True)
    arquivo = st.file_uploader(
        "Arquivo .txt",
        type=TIPOS_UPLOAD["texto"],
        key="arquivo_texto",
        label_visibility="collapsed",
        accept_multiple_files=False,
        max_upload_size=5,
    )
    if arquivo is not None:
        st.caption(f"{arquivo.name} · {formatar_tamanho(arquivo.size)}")
        texto_arquivo = _decodificar_texto(arquivo.getvalue())
        if texto_arquivo:
            st.markdown(
                f'<p class="trecho">{escape(_trecho(texto_arquivo))}</p>',
                unsafe_allow_html=True,
            )
        if texto.strip():
            st.markdown(
                '<p class="orientacao">O arquivo .txt será registrado.</p>',
                unsafe_allow_html=True,
            )
    return arquivo


def _campo_arquivo(modalidade: str):
    if modalidade == "audio":
        titulo = "Arquivo de voz"
        detalhe = "MP3, WAV, M4A, OGG ou WEBM, até 25 MB."
    else:
        titulo = "Ficha digitalizada"
        detalhe = "PNG, JPG, WEBP ou PDF, até 20 MB."

    st.markdown(f'<p class="rotulo">{titulo}</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="orientacao">{detalhe}</p>',
        unsafe_allow_html=True,
    )
    arquivo = st.file_uploader(
        titulo,
        type=TIPOS_UPLOAD[modalidade],
        key=f"arquivo_{modalidade}",
        label_visibility="collapsed",
        accept_multiple_files=False,
        max_upload_size=25 if modalidade == "audio" else 20,
    )
    nome, mime, dados = _bytes_do_arquivo(modalidade, arquivo)
    if dados and nome:
        reutilizado = arquivo is None
        origem = f"Mantendo {nome}" if reutilizado else nome
        st.caption(f"{origem} · {formatar_tamanho(len(dados))}")
        _previsualizar(modalidade, nome, mime, dados)
    return arquivo


def _mostrar_extracao(entrada: dict) -> None:
    chave = entrada.get("caminho_copia")
    if st.session_state.get("extracao_chave") != chave:
        st.session_state.extracao_registro = None
        st.session_state.extracao_erro = None
        st.session_state.extracao_chave = chave
        st.session_state.edicao_id = None
        st.session_state.minuta_erro = None

    if st.session_state.extracao_erro:
        st.markdown(
            f'<p class="aviso">{escape(st.session_state.extracao_erro)}</p>',
            unsafe_allow_html=True,
        )
        if st.button("Tentar de novo", key="repetir_extracao", width="stretch"):
            st.session_state.extracao_erro = None
            st.session_state.extracao_registro = None
            st.session_state.extracao_forcar = True
            st.rerun()
        return

    if not st.session_state.extracao_registro:
        with st.spinner("Extraindo o texto e preenchendo os campos..."):
            try:
                forcar = st.session_state.extracao_forcar
                st.session_state.extracao_forcar = False
                st.session_state.extracao_registro = processar_entrada(
                    entrada,
                    forcar=forcar,
                    configuracao=st.session_state.get("configuracao_modelo"),
                )
            except Exception as erro:
                st.session_state.extracao_erro = _mensagem_extracao(erro)
                st.rerun()

    _resumo_extracao(st.session_state.extracao_registro)


def _resumo_extracao(registro: dict) -> None:
    _preparar_edicao(registro)
    alertas = registro.get("alertas_seguranca") or []
    aviso_alerta = ""
    if alertas:
        itens = "".join(f"<li>{escape(str(item))}</li>" for item in alertas)
        aviso_alerta = f'<ul class="orientacao">{itens}</ul>'

    st.markdown(
        '<p class="orientacao">Ao prosseguir, a minuta é montada com estes campos.</p>',
        unsafe_allow_html=True,
    )
    if aviso_alerta:
        st.markdown(aviso_alerta, unsafe_allow_html=True)

    with st.container(key="edicao"):
        st.selectbox(
            "Categoria",
            list(CATEGORIAS),
            key="edit_categoria",
            format_func=lambda valor: ROTULOS_CATEGORIA.get(valor, valor),
            persist_state="session",
        )
        st.text_input("Assunto", key="edit_assunto", persist_state="session")
        st.text_area("Pedido", key="edit_pedido", height=88, persist_state="session")
        _campos_edicao()

    ausentes = _ausentes_da_edicao()
    if ausentes:
        st.caption("Campos não localizados: " + ", ".join(ausentes))
    _resumo_chamada(registro.get("chamada") or {})
    _guardar_edicao()


def _preparar_edicao(registro: dict) -> None:
    identificador = registro.get("id_execucao") or registro.get("arquivo_extracao")
    if st.session_state.get("edicao_id") == identificador and "edit_assunto" in st.session_state:
        return
    guardada = st.session_state.get("edicao_guardada")
    if (
        st.session_state.get("edicao_id_guardada") == identificador
        and isinstance(guardada, dict)
    ):
        for chave in _chaves_edicao():
            if chave not in st.session_state and chave in guardada:
                st.session_state[chave] = guardada[chave]
        if "edit_assunto" in st.session_state:
            st.session_state.edicao_id = identificador
            return
    st.session_state.edicao_id = identificador
    st.session_state.minuta_erro = None
    categoria = str(registro.get("categoria") or "").strip()
    st.session_state.edit_categoria = categoria if categoria in CATEGORIAS else "outros"
    st.session_state.edit_assunto = registro.get("assunto") or ""
    st.session_state.edit_pedido = registro.get("pedido") or ""
    campos = registro.get("campos") or {}
    for nome, _ in ROTULOS_CAMPOS:
        valor = ((campos.get(nome) or {}).get("valor")) or VALOR_AUSENTE
        st.session_state[f"edit_{nome}"] = valor


def _campos_edicao() -> None:
    linha = []
    for nome, rotulo in ROTULOS_CAMPOS:
        if nome in CAMPOS_LONGOS:
            _linha_de_campos(linha)
            linha = []
            st.text_area(rotulo, key=f"edit_{nome}", height=76, persist_state="session")
            continue
        linha.append((nome, rotulo))
        if len(linha) == 2:
            _linha_de_campos(linha)
            linha = []
    _linha_de_campos(linha)


def _linha_de_campos(linha: list[tuple[str, str]]) -> None:
    if not linha:
        return
    colunas = st.columns(len(linha))
    for coluna, (nome, rotulo) in zip(colunas, linha):
        with coluna:
            st.text_input(rotulo, key=f"edit_{nome}", persist_state="session")


def _ausentes_da_edicao() -> list[str]:
    ausentes = []
    for nome, _ in ROTULOS_CAMPOS:
        valor = (st.session_state.get(f"edit_{nome}") or "").strip()
        if not valor or valor == VALOR_AUSENTE:
            ausentes.append(nome)
    return ausentes


def _gerar_minuta_editada() -> None:
    registro = st.session_state.get("extracao_registro") or {}
    edicao = {
        "categoria": st.session_state.get("edit_categoria"),
        "assunto": st.session_state.get("edit_assunto"),
        "pedido": st.session_state.get("edit_pedido"),
    }
    for nome, _ in ROTULOS_CAMPOS:
        valor = (st.session_state.get(f"edit_{nome}") or "").strip() or VALOR_AUSENTE
        st.session_state[f"edit_{nome}"] = valor
        edicao[nome] = valor
    assunto = (edicao["assunto"] or "").strip() or VALOR_AUSENTE
    pedido = (edicao["pedido"] or "").strip() or VALOR_AUSENTE
    st.session_state.edit_assunto = assunto
    st.session_state.edit_pedido = pedido
    edicao["assunto"] = assunto
    edicao["pedido"] = pedido
    _guardar_edicao()
    try:
        st.session_state.extracao_registro = aplicar_edicao(registro, edicao)
        st.session_state.minuta_erro = None
    except (OSError, FileNotFoundError, ValueError) as erro:
        st.session_state.minuta_erro = str(erro)


def preparar_minuta(minuta: str) -> tuple[bool, str]:
    """Separa o marcador do brasão e mantém as quebras de linha no Markdown.

    O Markdown junta linhas separadas por uma única quebra; terminar a linha
    com dois espaços faz cada quebra da minuta aparecer na tela.
    """
    texto = (minuta or "").strip()
    com_brasao = texto.startswith(MARCADOR_BRASAO)
    if com_brasao:
        texto = texto.removeprefix(MARCADOR_BRASAO).lstrip()
    return com_brasao, texto.replace("\n", "  \n")


def _resumo_chamada(chamada: dict) -> None:
    if not chamada:
        return
    partes = []
    if chamada.get("temperatura") is not None:
        partes.append(f"temperatura {chamada['temperatura']}")
    if chamada.get("tempo_resposta_segundos") is not None:
        partes.append(f"{chamada['tempo_resposta_segundos']} s")
    if chamada.get("tokens_total") is not None:
        partes.append(f"{chamada['tokens_total']} tokens")
    if chamada.get("custo_estimado_usd") is not None:
        custo = f"{chamada['custo_estimado_usd']:.6f}".replace(".", ",")
        partes.append(f"US$ {custo}")
    if partes:
        st.caption("Chamada: " + " · ".join(partes))


def _mensagem_extracao(erro: Exception) -> str:
    if isinstance(erro, (ValueError, FileNotFoundError, OSError)):
        texto = str(erro)
    else:
        texto = "Não foi possível concluir a extração."
    if "sk-" in texto or "api_key" in texto.casefold():
        return "A consulta ao modelo falhou. Confira a chave da API no arquivo .env."
    return texto


def _escolher(modalidade: str) -> None:
    st.session_state.modalidade = modalidade
    st.session_state.erro = None


def _confirmar() -> None:
    modalidade = st.session_state.modalidade
    arquivo = st.session_state.get(f"arquivo_{modalidade}")
    material, erro = receber_material(modalidade, arquivo)
    if erro or material is None:
        st.session_state.erro = erro or MENSAGEM_VAZIA[modalidade]
        return
    try:
        copia = guardar_copia(material["nome_arquivo"], material["conteudo"])
    except OSError:
        st.session_state.erro = "Não foi possível guardar a cópia do arquivo."
        return
    if not copia["caminho"].is_file() or copia["caminho"].stat().st_size == 0:
        st.session_state.erro = "O arquivo não foi encontrado."
        return
    material["caminho_copia"] = copia["relativo"]
    material["preservou_existente"] = copia["preservou_existente"]
    material["nome_arquivo"] = copia["caminho"].name
    st.session_state.entrada = material
    st.session_state.confirmada = True
    st.session_state.erro = None


def _pendencia(modalidade: str, arquivo) -> str | None:
    _, erro = receber_material(modalidade, arquivo)
    return erro


def receber_material(modalidade: str, arquivo) -> tuple[dict | None, str | None]:
    """Confere o que foi entregue e devolve o material pronto para guardar."""
    if modalidade == "texto":
        return _receber_texto(arquivo)
    nome, mime, dados = _bytes_do_arquivo(modalidade, arquivo)
    if nome is None or dados is None:
        return None, MENSAGEM_VAZIA[modalidade]
    erro = conferir_arquivo(modalidade, nome, dados)
    if erro:
        return None, erro
    return _material(modalidade, "arquivo", Path(nome).name, mime, dados, None), None


def _receber_texto(arquivo) -> tuple[dict | None, str | None]:
    if arquivo is not None:
        dados = arquivo.getvalue()
        erro = conferir_arquivo("texto", arquivo.name, dados)
        if erro:
            return None, erro
        texto = _decodificar_texto(dados)
        if not texto:
            return None, "O arquivo está vazio."
        if len(texto) > LIMITE_TEXTO:
            return None, f"O texto passa de {_formatar_inteiro(LIMITE_TEXTO)} caracteres."
        return _material(
            "texto",
            "arquivo",
            Path(arquivo.name).name,
            _mime("texto", arquivo.name, arquivo.type),
            dados,
            texto,
        ), None

    texto = (st.session_state.get("rascunho_texto") or "").strip()
    if texto:
        if len(texto) > LIMITE_TEXTO:
            return None, f"O texto passa de {_formatar_inteiro(LIMITE_TEXTO)} caracteres."
        dados = texto.encode("utf-8")
        return _material("texto", "cola", "solicitacao_texto.txt", "text/plain", dados, texto), None

    anterior = _arquivo_anterior("texto")
    if anterior:
        nome, mime, dados = anterior
        erro = conferir_arquivo("texto", nome, dados)
        if erro:
            return None, erro
        texto = _decodificar_texto(dados)
        if not texto:
            return None, "O arquivo está vazio."
        return _material("texto", "arquivo", nome, mime, dados, texto), None
    return None, MENSAGEM_VAZIA["texto"]


def _material(modalidade, origem, nome, mime, dados, texto) -> dict:
    return {
        "modalidade": modalidade,
        "origem": origem,
        "texto": texto,
        "nome_arquivo": nome,
        "tipo_mime": mime,
        "tamanho_bytes": len(dados),
        "conteudo": dados,
    }


def conferir_arquivo(modalidade: str, nome: str | None, dados: bytes | None) -> str | None:
    """Confere existência, extensão aceita e conteúdo não vazio."""
    if nome is None or dados is None or not str(nome).strip():
        return "O arquivo não foi encontrado."
    if Path(nome).name in {"", ".", ".."}:
        return "O arquivo não foi encontrado."
    extensao = Path(nome).suffix.lower()
    if extensao not in EXTENSOES[modalidade]:
        return "Essa extensão não é aceita."
    if len(dados) == 0:
        return "O arquivo está vazio."
    if len(dados) > LIMITE_BYTES[modalidade]:
        return f"O arquivo passa de {formatar_tamanho(LIMITE_BYTES[modalidade])}."
    return None


def guardar_copia(nome: str, dados: bytes, pasta: Path | None = None) -> dict:
    """Grava uma cópia em dados/originais sem alterar arquivo já existente."""
    if not dados:
        raise OSError("O arquivo está vazio.")
    destino_pasta = pasta or PASTA_ORIGINAIS
    destino_pasta.mkdir(parents=True, exist_ok=True)
    desejado = destino_pasta / _nome_seguro(nome)
    ja_existia = desejado.exists()
    if desejado.is_file() and _mesmo_conteudo(desejado, dados):
        return _resultado_copia(desejado, preservou_existente=True)

    destino = _destino_livre(desejado)
    if destino.exists():
        raise OSError("Já existe um arquivo nesse caminho.")
    temporario = destino_pasta / f".{destino.name}.parcial"
    try:
        temporario.write_bytes(dados)
        temporario.replace(destino)
    finally:
        if temporario.exists():
            temporario.unlink()
    if not destino.is_file() or destino.stat().st_size == 0:
        raise OSError("O arquivo não foi encontrado.")
    return _resultado_copia(destino, preservou_existente=ja_existia)


def _nome_seguro(nome: str) -> str:
    base = Path(str(nome).replace("\\", "/")).name.strip().replace("\x00", "")
    if base in {"", ".", ".."}:
        return "solicitacao.txt"
    return base


def _destino_livre(destino: Path) -> Path:
    if not destino.exists():
        return destino
    indice = 2
    while True:
        candidato = destino.with_name(f"{destino.stem}_{indice}{destino.suffix}")
        if not candidato.exists():
            return candidato
        indice += 1


def _mesmo_conteudo(caminho: Path, dados: bytes) -> bool:
    if caminho.stat().st_size != len(dados):
        return False
    return caminho.read_bytes() == dados


def _resultado_copia(destino: Path, preservou_existente: bool) -> dict:
    try:
        relativo = destino.relative_to(BASE_DIR).as_posix()
    except ValueError:
        relativo = destino.as_posix()
    return {
        "caminho": destino,
        "relativo": relativo,
        "preservou_existente": preservou_existente,
    }


def _decodificar_texto(dados: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return dados.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return dados.decode("latin-1").strip()


def _bytes_do_arquivo(modalidade: str, arquivo) -> tuple[str | None, str | None, bytes | None]:
    if arquivo is not None:
        return arquivo.name, _mime(modalidade, arquivo.name, arquivo.type), arquivo.getvalue()
    return _arquivo_anterior(modalidade) or (None, None, None)


def _arquivo_anterior(modalidade: str) -> tuple[str, str | None, bytes] | None:
    entrada = st.session_state.get("entrada") or {}
    conteudo = entrada.get("conteudo")
    if entrada.get("modalidade") == modalidade and conteudo:
        return entrada.get("nome_arquivo") or "arquivo", entrada.get("tipo_mime"), conteudo
    return None


def _mime(modalidade: str, nome: str, mime: str | None) -> str | None:
    if mime and mime != "application/octet-stream":
        return mime
    extensao = Path(nome).suffix.lower()
    if modalidade == "audio":
        return MIME_AUDIO.get(extensao, mime)
    if extensao == ".txt":
        return "text/plain"
    if extensao == ".pdf":
        return "application/pdf"
    return mime


def _previsualizar(modalidade: str, nome: str | None, mime: str | None, dados: bytes | None) -> None:
    if not dados:
        return
    if modalidade == "audio":
        st.audio(dados, format=mime or "audio/mpeg")
        return
    if _eh_pdf(nome, mime):
        _previsualizar_pdf(dados)
        return
    try:
        st.image(dados, width="stretch")
    except Exception:
        st.caption("Não foi possível pré-visualizar esta imagem. O arquivo segue registrado.")


def _previsualizar_pdf(dados: bytes) -> None:
    try:
        import fitz
    except ImportError:
        st.caption("PDF recebido. A pré-visualização não está disponível neste ambiente.")
        return
    try:
        with fitz.open(stream=dados, filetype="pdf") as documento:
            if documento.page_count == 0:
                st.caption("O PDF não tem páginas.")
                return
            pagina = documento[0]
            pixmap = pagina.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
            st.image(pixmap.tobytes("png"), width="stretch")
            total = documento.page_count
            legenda = "1 página" if total == 1 else f"Página 1 de {total}"
            st.caption(legenda)
    except Exception:
        st.caption("Não foi possível pré-visualizar este PDF. O arquivo segue registrado.")


def _eh_pdf(nome: str | None, mime: str | None) -> bool:
    if mime == "application/pdf":
        return True
    return bool(nome and nome.lower().endswith(".pdf"))


def _trecho(texto: str, limite: int = 280) -> str:
    limpo = " ".join(texto.split())
    if len(limpo) <= limite:
        return limpo
    return limpo[: limite - 1].rstrip() + "…"


def formatar_tamanho(tamanho: int) -> str:
    if tamanho < 1024:
        return f"{tamanho} B"
    if tamanho < 1024 * 1024:
        return f"{round(tamanho / 1024)} KB"
    valor = f"{tamanho / (1024 * 1024):.1f}".replace(".", ",")
    return f"{valor} MB"


def _formatar_inteiro(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")
