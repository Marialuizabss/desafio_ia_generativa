"""Lê a entrada confirmada, extrai o texto e grava o objeto em processados.

A minuta não entra nessa gravação como texto definitivo: depois da extração,
a interface deixa os campos editáveis e só monta a minuta quando o usuário pede.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

try:
    from audit import decisoes_ligadas, registrar_execucao, registrar_revisao
    from audio import MODELO as MODELO_TRANSCRICAO
    from audio import transcrever_audio
    from extracao import CAMPOS, CAMPOS_SOLICITACAO, CATEGORIAS, FONTE_AUSENTE, VALOR_AUSENTE
    from llm_client import extrair_campos, montar_minuta
    from privacidade import contar_remocoes, minimizar_texto
    from vision import ler_texto_visual
except ImportError:
    from src.audit import decisoes_ligadas, registrar_execucao, registrar_revisao
    from src.audio import MODELO as MODELO_TRANSCRICAO
    from src.audio import transcrever_audio
    from src.extracao import CAMPOS, CAMPOS_SOLICITACAO, CATEGORIAS, FONTE_AUSENTE, VALOR_AUSENTE
    from src.llm_client import extrair_campos, montar_minuta
    from src.privacidade import contar_remocoes, minimizar_texto
    from src.vision import ler_texto_visual

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_PROCESSADOS = BASE_DIR / "dados" / "processados"
PASTA_APROVADAS = Path("resultados") / "minutas" / "aprovadas"


MODELOS_ANALISE = {"gpt-5.6-luna", "gpt-5.6-terra", "o4-mini", "gpt-4o-mini"}

# Modelo que lê a entrada antes da extração (o texto digitado não passa por modelo;
# PDF com camada de texto é lido localmente, sem modelo)
MODELOS_LEITURA = {"audio": MODELO_TRANSCRICAO, "imagem": "gpt-4o"}


def processar_entrada(
    entrada: dict,
    forcar: bool = False,
    configuracao: dict | None = None,
    id_execucao_anterior: str | None = None,
) -> dict:
    """Extrai o texto da entrada, monta o objeto e salva o JSON.

    ``entrada`` é o material confirmado na interface, com ``modalidade``,
    ``caminho_copia`` e, no texto, o próprio ``texto``.
    """

    arquivo = (entrada.get("caminho_copia") or "").strip()
    modalidade = entrada.get("modalidade")
    if not arquivo:
        raise ValueError("A cópia da entrada não foi encontrada.")
    if modalidade not in {"texto", "audio", "imagem"}:
        raise ValueError("Forma de envio desconhecida.")

    caminho = BASE_DIR / arquivo
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    PASTA_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    saida = PASTA_PROCESSADOS / f"extracao_{caminho.stem}.json"
    modelo_id, temperatura, idioma = _configuracao(configuracao)
    if saida.is_file() and not forcar:
        registro = json.loads(saida.read_text(encoding="utf-8"))
        if _pode_reaproveitar(registro, arquivo, modelo_id, temperatura, idioma):
            registro["arquivo_extracao"] = saida.relative_to(BASE_DIR).as_posix()
            # Cada envio é uma execução nova, com revisão própria, mesmo sem nova
            # chamada à API. A origem aponta a execução que gerou a extração
            # (None nas extrações anteriores ao registro do RF11).
            origem = registro.get("id_execucao")
            registro["id_execucao_origem"] = origem
            registro["id_execucao"] = registrar_execucao({
                "tipo": "extracao_reaproveitada",
                "modalidade": modalidade,
                "arquivo_origem": arquivo,
                "arquivo_extracao": registro["arquivo_extracao"],
                "id_execucao_origem": origem,
                "modelo": modelo_id,
                "versao_prompt": (registro.get("chamada") or {}).get("versao_prompt"),
                "resultado": "reaproveitada",
                "categoria": registro.get("categoria"),
                "campos_ausentes": registro.get("campos_ausentes"),
                "alertas_seguranca": registro.get("alertas_seguranca"),
                "dados_removidos": registro.get("dados_removidos"),
                "requer_revisao": True,
            })
            return registro

    anterior_id = (id_execucao_anterior or "").strip() or None
    arquivo_anterior = None
    if saida.is_file():
        antigo = json.loads(saida.read_text(encoding="utf-8"))
        arquivo_anterior = _arquivar_extracao(saida, antigo.get("id_execucao"))
        if not anterior_id:
            anterior_id = (antigo.get("id_execucao") or "").strip() or None

    base_registro = {
        "tipo": "extracao_e_minuta",
        "modalidade": modalidade,
        "arquivo_origem": arquivo,
        "modelo": modelo_id,
        "modelo_leitura": MODELOS_LEITURA.get(modalidade),
    }
    if anterior_id:
        base_registro["id_execucao_anterior"] = anterior_id
    if arquivo_anterior:
        base_registro["arquivo_extracao_anterior"] = arquivo_anterior
    inicio = perf_counter()
    try:
        texto = minimizar_texto(_extrair_texto(modalidade, caminho, entrada, idioma))
        resultado, chamada = extrair_campos(
            texto,
            arquivo,
            modelo=modelo_id,
            temperatura=temperatura,
            idioma=idioma,
        )
    except Exception as erro:
        registrar_execucao({
            **base_registro,
            "resultado": "erro",
            "erro": f"{type(erro).__name__}: {erro}",
            "duracao_total_segundos": round(perf_counter() - inicio, 2),
        })
        raise

    registro = resultado.para_dict()
    registro["modalidade"] = modalidade
    registro["arquivo_origem"] = arquivo
    registro["modelo"] = modelo_id
    if anterior_id:
        registro["id_execucao_anterior"] = anterior_id
    if arquivo_anterior:
        registro["arquivo_extracao_anterior"] = arquivo_anterior
    registro["texto_extraido"] = texto
    registro["dados_removidos"] = contar_remocoes(texto)
    registro["chamada"] = chamada
    registro["id_execucao"] = registrar_execucao({
        **base_registro,
        "resultado": "sucesso",
        "arquivo_extracao": saida.relative_to(BASE_DIR).as_posix(),
        "provedor": chamada.get("provedor"),
        "versao_prompt": chamada.get("versao_prompt"),
        "parametros": {"temperatura": temperatura, "idioma": idioma, **(chamada.get("parametros") or {})},
        "duracao_total_segundos": round(perf_counter() - inicio, 2),
        "tempo_resposta_segundos": chamada.get("tempo_resposta_segundos"),
        "tokens_entrada": chamada.get("tokens_entrada"),
        "tokens_saida": chamada.get("tokens_saida"),
        "custo_estimado_usd": chamada.get("custo_estimado_usd"),
        "categoria": registro["categoria"],
        "campos_ausentes": registro["campos_ausentes"],
        "alertas_seguranca": registro["alertas_seguranca"],
        "dados_removidos": registro["dados_removidos"],
        "requer_revisao": True,
    })

    saida.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    registro["arquivo_extracao"] = saida.relative_to(BASE_DIR).as_posix()
    return registro


def motivos_da_revisao(registro: dict) -> list[str]:
    """Por que a aprovação entra como aprovado com revisão (lista vazia: aprovado).

    Documentos, prazo e local nunca vêm na solicitação, então não contam.
    """
    registro = registro or {}
    campos = registro.get("campos") or {}
    motivos = []
    for nome in CAMPOS_SOLICITACAO:
        item = campos.get(nome) or {}
        valor = (item.get("valor") if isinstance(item, dict) else "") or ""
        if not valor.strip() or valor.strip() == VALOR_AUSENTE:
            motivos.append("faltam dados da solicitação")
            break
    if registro.get("campos_alterados"):
        motivos.append("campos alterados na revisão")
    return motivos


def decisao_de_aprovacao(registro: dict) -> str:
    """Aprovado com revisão quando falta dado da solicitação ou o revisor alterou campos."""
    return "aprovado_com_revisao" if motivos_da_revisao(registro) else "aprovado"


def salvar_minuta_aprovada(registro: dict) -> str:
    """Grava a minuta aprovada em resultados/minutas/aprovadas/, sem sobrescrever."""
    minuta = (registro.get("minuta") or "").strip()
    if not minuta:
        raise ValueError("A minuta está vazia.")
    id_execucao = (registro.get("id_execucao") or "").strip()
    if not id_execucao:
        raise ValueError("A execução avaliada não foi identificada.")
    origem = Path(registro.get("arquivo_origem") or "minuta").stem
    pasta = BASE_DIR / PASTA_APROVADAS
    nome = f"minuta_{origem}_{id_execucao[:8]}"
    destino = pasta / f"{nome}.md"
    numero = 2
    while destino.exists():
        destino = pasta / f"{nome}_{numero}.md"
        numero += 1
    pasta.mkdir(parents=True, exist_ok=True)
    destino.write_text(minuta + "\n", encoding="utf-8")
    return destino.relative_to(BASE_DIR).as_posix()


ASSINATURA = (
    ("[NOME DO SERVIDOR RESPONSÁVEL]", "servidor"),
    ("[CARGO / SETOR]", "cargo"),
)

# Dados que a leitura de áudio e imagem pode errar e que o servidor confere com o original
DADOS_CRITICOS = (
    ("solicitante", "Nome do solicitante"),
    ("protocolo", "Protocolo"),
    ("data_solicitacao", "Data da solicitação"),
    ("data_inicio", "Data de início"),
)


def assinar_minuta(minuta: str, servidor: str = "", cargo: str = "") -> str:
    """Troca os colchetes da assinatura pelo que o servidor informou.

    A IA nunca preenche a assinatura: só a pessoa, na aprovação. Campo vazio
    mantém o colchete do modelo.
    """
    valores = {"servidor": (servidor or "").strip(), "cargo": (cargo or "").strip()}
    texto = minuta or ""
    for marcador, campo in ASSINATURA:
        if valores[campo]:
            texto = texto.replace(marcador, valores[campo])
    return texto


def protocolo_da_minuta(registro: dict) -> str:
    valor = (((registro.get("campos") or {}).get("protocolo") or {}).get("valor") or "").strip()
    return "" if valor == VALOR_AUSENTE else valor


def rodape_da_minuta(registro: dict, servidor: str, cargo: str, quando: datetime | None = None) -> list[str]:
    """Linhas do pé do PDF: só o nome do arquivo de origem (sem diretório), protocolo e id."""
    origem = [f"Origem: {Path(registro.get('arquivo_origem') or '').name or 'não informada'}"]
    protocolo = protocolo_da_minuta(registro)
    if protocolo:
        origem.append(f"Protocolo {protocolo}")
    id_execucao = (registro.get("id_execucao") or "").strip()
    if id_execucao:
        origem.append(f"Execução {id_execucao[:8]}")
    quando = quando or datetime.now()
    assinatura = (servidor or "").strip()
    if (cargo or "").strip():
        assinatura += f" ({cargo.strip()})"
    return [
        " · ".join(origem),
        f"Aprovada por {assinatura} em {quando.strftime('%d/%m/%Y às %H:%M')}",
    ]


def nome_do_pdf(registro: dict) -> str:
    """minuta_<protocolo>.pdf; sem protocolo, usa o nome do arquivo de origem."""
    base = protocolo_da_minuta(registro) or Path(registro.get("arquivo_origem") or "minuta").stem
    return f"minuta_{re.sub(r'[^0-9A-Za-z._-]+', '_', base).strip('_') or 'minuta'}.pdf"


def salvar_pdf_aprovado(arquivo_minuta: str, dados: bytes) -> str:
    """Grava o PDF ao lado da minuta aprovada, com o mesmo nome."""
    destino = (BASE_DIR / arquivo_minuta).with_suffix(".pdf")
    if destino.exists():
        raise FileExistsError(f"O PDF já existe: {destino.name}")
    destino.write_bytes(dados)
    return destino.relative_to(BASE_DIR).as_posix()


def caminho_no_projeto(relativo: str) -> Path:
    """Caminho absoluto de um arquivo gravado pelo fluxo (minuta e PDF aprovados)."""
    return BASE_DIR / relativo


def descartar_minuta_aprovada(caminho: str) -> None:
    """Apaga a minuta gravada quando a decisão não chegou ao registro."""
    if caminho:
        (BASE_DIR / caminho).unlink(missing_ok=True)


def preservar_extracao(registro: dict) -> str:
    """Copia o JSON atual para um arquivo que a geração seguinte não sobrescreve."""
    caminho = (registro.get("arquivo_extracao") or "").strip()
    if not caminho:
        raise ValueError("A extração rejeitada não tem arquivo.")
    origem = BASE_DIR / caminho
    if not origem.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {origem}")
    return _arquivar_extracao(origem, registro.get("id_execucao"))


def _arquivar_extracao(origem: Path, id_execucao: str | None) -> str:
    marca = (id_execucao or "").strip() or uuid4().hex
    destino = origem.with_name(f"{origem.stem}__{marca}{origem.suffix}")
    if not destino.exists():
        destino.write_bytes(origem.read_bytes())
    return destino.relative_to(BASE_DIR).as_posix()


def _pode_reaproveitar(registro: dict, arquivo: str, modelo_id: str, temperatura, idioma) -> bool:
    chamada = registro.get("chamada") or {}
    return (
        registro.get("arquivo_origem") == arquivo
        and registro.get("modelo") == modelo_id
        and chamada.get("temperatura") == temperatura
        and chamada.get("idioma") == idioma
        and "dados_removidos" in registro
        and chamada.get("versao_prompt") == _versao_prompt(idioma)
        and not _decisao_impede_reuso(registro.get("id_execucao"))
    )


def _decisao_impede_reuso(id_execucao: str | None) -> bool:
    if not id_execucao:
        return False
    # A rejeição pode ter sido feita num reaproveitamento: vale a decisão mais recente
    decisoes = decisoes_ligadas(id_execucao)
    if not decisoes:
        return False
    return decisoes[-1].get("decisao") in {"rejeitado", "nova_geracao"}


def _versao_prompt(idioma: str | None) -> str:
    try:
        from src import llm_client as cliente
    except ImportError:
        import llm_client as cliente
    return cliente.versao_do_prompt(idioma)


def aplicar_edicao(registro: dict, edicao: dict, dados_conferidos: list[str] | None = None) -> dict:
    """Monta a minuta a partir dos campos revisados e grava a revisão à parte.

    O JSON da extração continua com a resposta do modelo; cada revisão vira
    um arquivo numerado ao lado dele e uma linha no registro (RF11). O objeto
    recebido não é alterado.
    """

    extraido = registro.get("extraido") or {
        "categoria": registro.get("categoria"),
        "assunto": registro.get("assunto"),
        "pedido": registro.get("pedido"),
        "campos": registro.get("campos") or {},
    }
    atualizado = dict(registro)
    atualizado["extraido"] = extraido
    categoria = str(edicao.get("categoria") or "").strip()
    if categoria not in CATEGORIAS:
        categoria = str(registro.get("categoria") or "").strip()
    atualizado["categoria"] = categoria if categoria in CATEGORIAS else "outros"
    atualizado["assunto"] = _texto_editado(edicao.get("assunto"))
    atualizado["pedido"] = _texto_editado(edicao.get("pedido"))

    originais = extraido.get("campos") or {}
    campos = {}
    ausentes = []
    valores = {}
    for nome in CAMPOS:
        valor = _texto_editado(edicao.get(nome))
        original = originais.get(nome) or {}
        if valor == VALOR_AUSENTE:
            fonte = FONTE_AUSENTE
            ausentes.append(nome)
        elif valor == (original.get("valor") or ""):
            fonte = original.get("fonte") or FONTE_AUSENTE
        else:
            fonte = "edicao"
        campos[nome] = {"valor": valor, "fonte": fonte}
        valores[nome] = valor

    atualizado["campos"] = campos
    atualizado["campos_ausentes"] = ausentes
    atualizado["campos_alterados"] = _campos_alterados(extraido, atualizado)
    atualizado["minuta"] = montar_minuta(valores)
    atualizado["minuta_gerada_de_campos"] = True
    atualizado["requer_revisao"] = True
    if dados_conferidos is None:
        atualizado.pop("dados_conferidos", None)
    else:
        atualizado["dados_conferidos"] = list(dados_conferidos)
    atualizado["arquivo_revisao"] = _gravar_revisao(atualizado)
    return atualizado


def _campos_alterados(extraido: dict, atualizado: dict) -> list[str]:
    alterados = [
        nome for nome in ("categoria", "assunto", "pedido")
        if _texto_editado(extraido.get(nome)) != atualizado[nome]
    ]
    originais = extraido.get("campos") or {}
    for nome in CAMPOS:
        original = _texto_editado((originais.get(nome) or {}).get("valor"))
        if original != atualizado["campos"][nome]["valor"]:
            alterados.append(nome)
    return alterados


def _gravar_revisao(atualizado: dict) -> str | None:
    """Grava a revisão numerada; repetir a mesma revisão não cria arquivo novo."""
    caminho = (atualizado.get("arquivo_extracao") or "").strip()
    if not caminho:
        return None
    principal = BASE_DIR / caminho
    id_execucao = (atualizado.get("id_execucao") or "").strip()
    prefixo = f"{principal.stem}__{id_execucao or 'sem_id'}__revisao_"
    existentes = sorted(
        principal.parent.glob(f"{prefixo}*.json"),
        key=lambda arquivo: int(arquivo.stem.rsplit("_", 1)[-1]),
    )
    conteudo = {
        chave: atualizado.get(chave)
        for chave in ("categoria", "assunto", "pedido", "campos", "minuta", "dados_conferidos")
    }
    if existentes:
        ultima = json.loads(existentes[-1].read_text(encoding="utf-8"))
        if {chave: ultima.get(chave) for chave in conteudo} == conteudo:
            return existentes[-1].relative_to(BASE_DIR).as_posix()

    destino = principal.parent / f"{prefixo}{len(existentes) + 1}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    gravado = {chave: valor for chave, valor in atualizado.items() if chave != "arquivo_revisao"}
    destino.write_text(json.dumps(gravado, ensure_ascii=False, indent=2), encoding="utf-8")
    relativo = destino.relative_to(BASE_DIR).as_posix()
    if id_execucao:
        registrar_revisao(
            id_execucao, atualizado["campos_alterados"], relativo, atualizado.get("dados_conferidos"),
        )
    return relativo


def _texto_editado(valor) -> str:
    texto = "" if valor is None else str(valor).strip()
    return texto or VALOR_AUSENTE


def _configuracao(configuracao: dict | None) -> tuple[str, float | None, str | None]:
    try:
        from llm_client import MODELO
    except ImportError:
        from src.llm_client import MODELO

    dados = configuracao or {}
    modelo = str(dados.get("modelo") or MODELO).strip()
    if modelo not in MODELOS_ANALISE:
        modelo = MODELO
    parametros = dados.get("parametros") or {}
    temperatura = parametros.get("temperatura")
    if temperatura is not None:
        temperatura = round(float(temperatura), 1)
    idioma = parametros.get("idioma") or None
    return modelo, temperatura, idioma


def _extrair_texto(modalidade: str, caminho: Path, entrada: dict, idioma: str | None) -> str:
    if modalidade == "texto":
        texto = (entrada.get("texto") or "").strip()
        if not texto:
            texto = caminho.read_text(encoding="utf-8").strip()
    elif modalidade == "audio":
        destino = PASTA_PROCESSADOS / f"transcricao_{caminho.stem}.txt"
        texto = transcrever_audio(caminho, destino_texto=destino, idioma=idioma)
    else:
        texto = ler_texto_visual(caminho)

    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Não foi possível extrair texto desta entrada.")
    return texto
