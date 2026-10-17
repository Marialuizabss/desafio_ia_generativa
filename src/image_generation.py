
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

MODELO = "gpt-image-1"

PROMPT_GERACAO = """
Crie uma arte gráfica institucional vertical, elegante e formal,
para um comunicado informativo sobre matrículas em cursos técnicos
no Estado de Mato Grosso, Brasil.

Identidade visual:
- Fundo branco.
- Verde institucional como cor principal.
- Detalhes discretos em amarelo.
- Tipografia legível e composição administrativa.
- Espaço livre centralizado no topo para inserir posteriormente
  o brasão oficial do Estado de Mato Grosso.
- Não desenhe nem invente um brasão.

Conteúdo:
Título: ORIENTAÇÕES PARA MATRÍCULA

Seções:
DOCUMENTAÇÃO
Consulte a secretaria escolar para confirmar os documentos exigidos.

ACOMPANHAMENTO
Acompanhe a análise da solicitação e as próximas orientações.

AVISO IMPORTANTE
O recebimento da solicitação não confirma automaticamente a matrícula.

Rodapé:
Peça demonstrativa — Projeto FIC_DEV 2026.
Não constitui comunicado oficial.

Não invente datas, prazos, endereços ou documentos obrigatórios.
Não inclua dados pessoais de estudantes.
"""

def gerar_imagem():
    saida = BASE_DIR / "resultados" / "imagens" / "imagem_rf10_original.png"
    metadados = BASE_DIR / "resultados" / "logs" / "metadados_rf10.json"

    saida.parent.mkdir(parents=True, exist_ok=True)
    metadados.parent.mkdir(parents=True, exist_ok=True)

    if saida.exists():
        raise FileExistsError(
            f"A imagem original já existe: {saida}"
        )

    client = OpenAI(timeout=180.0, max_retries=1)

    print("Gerando comunicado institucional...")

    resposta = client.images.generate(
        model=MODELO,
        prompt=PROMPT_GERACAO,
        size="1024x1536",
        quality="medium",
    )

    conteudo = resposta.data[0].b64_json

    if not conteudo:
        raise ValueError("A API retornou uma imagem vazia.")

    saida.write_bytes(base64.b64decode(conteudo))

    registro = {
        "requisito": "RF10",
        "etapa": "geracao",
        "modelo": MODELO,
        "prompt": PROMPT_GERACAO.strip(),
        "data_execucao_utc": datetime.now(timezone.utc).isoformat(),
        "arquivo_gerado": str(saida.relative_to(BASE_DIR)),
        "revisao_humana": "pendente",
        "observacao": "Arte demonstrativa, sem dados pessoais.",
    }

    metadados.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Imagem gerada: {saida}")
    print(f"Metadados salvos: {metadados}")


if __name__ == "__main__":
    gerar_imagem()


def editar_imagem():
    entrada = BASE_DIR / "resultados" / "imagens" / "imagem_rf10_layout_formal.png"
    saida = BASE_DIR / "resultados" / "imagens" / "imagem_rf10_editada.png"
    metadados = BASE_DIR / "resultados" / "logs" / "metadados_edicao_rf10.json"

    if not entrada.is_file():
        raise FileNotFoundError(f"Imagem não encontrada: {entrada}")

    if saida.exists():
        raise FileExistsError(f"A imagem editada já existe: {saida}")

    metadados.parent.mkdir(parents=True, exist_ok=True)

    prompt_edicao = """
    Edite a imagem fornecida preservando seu estilo de
    comunicado institucional formal.

    Alteração solicitada:
    Adicione uma linha horizontal fina e discreta na cor
    amarelo-dourado imediatamente abaixo da faixa verde
    do título principal.

    Preserve:
    - O brasão de Mato Grosso.
    - Todos os textos exatamente como estão.
    - A organização das seções.
    - As cores institucionais.
    - O aviso e o rodapé demonstrativo.

    Não adicione informações novas.
    Não modifique nomes, datas ou outros textos.
    """

    client = OpenAI(timeout=180.0, max_retries=1)

    print("Iniciando edição da imagem...")

    with entrada.open("rb") as arquivo:
        resposta = client.images.edit(
            model=MODELO,
            image=arquivo,
            prompt=prompt_edicao,
            size="1024x1536",
            quality="medium",
        )

    conteudo = resposta.data[0].b64_json

    if not conteudo:
        raise ValueError("A API retornou uma imagem vazia.")

    saida.write_bytes(base64.b64decode(conteudo))

    registro = {
        "requisito": "RF10",
        "etapa": "edicao",
        "modelo": MODELO,
        "imagem_entrada": str(entrada.relative_to(BASE_DIR)),
        "imagem_saida": str(saida.relative_to(BASE_DIR)),
        "prompt": prompt_edicao.strip(),
        "data_execucao_utc": datetime.now(timezone.utc).isoformat(),
        "revisao_humana": "pendente",
    }

    metadados.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Imagem editada: {saida}")
    print(f"Metadados salvos: {metadados}")
