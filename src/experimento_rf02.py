import hashlib
import json
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Configuração do experimento (provisória até o llm_client.py ficar pronto)
PROVEDOR = "OpenAI"
MODELO = "gpt-6.1-sol"
# Modelos de raciocínio usam max_completion_tokens, que inclui os tokens
# gastos "pensando"; por isso o limite é maior que o tamanho da minuta.
# Sem temperature: o gpt-6-luna só aceita o padrão (1); mantido igual
# nas execuções para que os modelos sejam comparados com os mesmos parâmetros.
PARAMETROS = {"max_completion_tokens": 4000, "seed": 42}
REPETICOES = 2

# Preço em US$ por 1 milhão de tokens — conferir na página de preços da OpenAI.
# Use None se o preço do modelo for desconhecido (o custo fica sem estimativa).
# gpt-6-luna: 0.10 / 0.50
PRECO_ENTRADA = None
PRECO_SAIDA = None

CASO_ID = "CASO-04"
ENTRADA = BASE_DIR / "dados" / "originais" / "entrada_texto.txt"
MODELO_MINUTA = BASE_DIR / "prompts" / "modelo_minuta.md"
PASTA_PROMPTS = BASE_DIR / "prompts" / "desafio1" / "rf02"
PASTA_SAIDA = BASE_DIR / "resultados" / "minutas" / "rf02"

# O Prompt C é gerado pelo próprio modelo, então cada modelo tem o seu arquivo
ARQUIVOS_PROMPT = {
    "A": PASTA_PROMPTS / "prompt_A.txt",
    "B": PASTA_PROMPTS / "prompt_B.txt",
    "C": PASTA_PROMPTS / f"prompt_C_{MODELO}.txt",
}


def ler(caminho):
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    texto = caminho.read_text(encoding="utf-8").strip()

    if not texto:
        raise ValueError(f"Arquivo vazio: {caminho}")

    return texto


def relativo(caminho):
    return caminho.relative_to(BASE_DIR).as_posix()


def versao(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


def montar(modelo_prompt, solicitacao, modelo_minuta):
    return (
        modelo_prompt
        .replace("{MODELO_MINUTA}", modelo_minuta)
        .replace("{SOLICITACAO}", solicitacao)
    )


def criar_cliente():
    try:
        return OpenAI(timeout=60.0, max_retries=2)
    except OpenAIError:
        raise SystemExit(
            "OPENAI_API_KEY não encontrada. Crie o arquivo .env "
            "a partir do .env.example."
        )


def chamar_modelo(client, prompt):
    inicio = perf_counter()

    try:
        resposta = client.chat.completions.create(
            model=MODELO,
            messages=[{"role": "user", "content": prompt}],
            **PARAMETROS,
        )
    except BadRequestError as erro:
        if erro.code in ("unsupported_parameter", "unsupported_value"):
            raise SystemExit(
                f"O modelo {MODELO} não aceita o parâmetro '{erro.param}'. "
                f"Ajuste PARAMETROS no script e registre a mudança na matriz. "
                f"Mensagem da API: {erro.message}"
            )
        raise SystemExit(f"A API recusou a requisição: {erro.message}")
    except AuthenticationError:
        raise SystemExit("Chave da API inválida. Confira o arquivo .env.")
    except RateLimitError:
        raise SystemExit(
            "Limite de requisições ou de crédito atingido. "
            "Aguarde e tente novamente."
        )
    except APIConnectionError:
        raise SystemExit(
            "Serviço da OpenAI indisponível ou sem conexão. "
            "Tente novamente mais tarde."
        )

    duracao = round(perf_counter() - inicio, 2)
    texto = (resposta.choices[0].message.content or "").strip()
    finish_reason = resposta.choices[0].finish_reason

    if not texto and finish_reason == "length":
        raise ValueError(
            "O limite de tokens acabou antes de o modelo gerar o texto. "
            "Aumente max_completion_tokens em PARAMETROS."
        )

    if not texto:
        raise ValueError("A API retornou uma resposta vazia.")

    uso = resposta.usage
    detalhes = getattr(uso, "completion_tokens_details", None)
    tokens_raciocinio = getattr(detalhes, "reasoning_tokens", None)
    custo = None

    if PRECO_ENTRADA is not None and PRECO_SAIDA is not None:
        custo = round((
            uso.prompt_tokens * PRECO_ENTRADA
            + uso.completion_tokens * PRECO_SAIDA
        ) / 1_000_000, 6)

    return {
        "texto": texto,
        "tempo_resposta_segundos": duracao,
        "tokens_entrada": uso.prompt_tokens,
        "tokens_saida": uso.completion_tokens,
        "tokens_raciocinio": tokens_raciocinio,
        "custo_estimado_usd": custo,
        "modelo_retornado": resposta.model,
        "system_fingerprint": resposta.system_fingerprint,
        "finish_reason": finish_reason,
    }


def registrar(registros, caminho, **dados):
    registros.append({
        "id_execucao": str(uuid4()),
        "data_hora": datetime.now().astimezone().isoformat(),
        "requisito": "RF02",
        "provedor": PROVEDOR,
        "modelo": MODELO,
        "parametros": PARAMETROS,
        **dados,
        "revisao_humana": "pendente",
    })

    caminho.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def criar_pasta_execucao():
    nome = datetime.now().strftime("execucao_%Y%m%d_%H%M%S")
    pasta = PASTA_SAIDA / nome
    contador = 2

    while pasta.exists():
        pasta = PASTA_SAIDA / f"{nome}_{contador}"
        contador += 1

    pasta.mkdir(parents=True)
    return pasta


def obter_prompt_c(client, modelo_minuta, registros, arquivo_registro):
    caminho = ARQUIVOS_PROMPT["C"]

    if caminho.is_file():
        print(f"Usando Prompt C já gerado: {relativo(caminho)}")
        return ler(caminho)

    metaprompt = ler(PASTA_PROMPTS / "metaprompt_C.txt")
    entrada = metaprompt.replace("{MODELO_MINUTA}", modelo_minuta)

    print("Gerando Prompt C a partir do metaprompt...")
    resultado = chamar_modelo(client, entrada)
    prompt_c = resultado.pop("texto")

    caminho.write_text(prompt_c, encoding="utf-8")

    registrar(
        registros,
        arquivo_registro,
        etapa="geracao_prompt_C",
        arquivo_prompt=relativo(PASTA_PROMPTS / "metaprompt_C.txt"),
        versao_prompt=versao(metaprompt),
        arquivo_saida=relativo(caminho),
        **resultado,
    )

    if "{SOLICITACAO}" not in prompt_c:
        raise SystemExit(
            f"O Prompt C gerado não contém {{SOLICITACAO}}. Edite "
            f"{relativo(caminho)}, registre a alteração e rode de novo."
        )

    print(f"Prompt C salvo em: {relativo(caminho)}")
    return prompt_c


def executar_experimento():
    solicitacao = ler(ENTRADA)
    modelo_minuta = ler(MODELO_MINUTA)
    client = criar_cliente()

    pasta = criar_pasta_execucao()
    arquivo_registro = pasta / "registro_rf02.json"
    registros = []

    prompts = {
        "A": ler(ARQUIVOS_PROMPT["A"]),
        "B": ler(ARQUIVOS_PROMPT["B"]),
        "C": obter_prompt_c(client, modelo_minuta, registros, arquivo_registro),
    }

    for nome, modelo_prompt in prompts.items():
        prompt_final = montar(modelo_prompt, solicitacao, modelo_minuta)
        arquivo_entrada = pasta / f"entrada_prompt_{nome}.txt"
        arquivo_entrada.write_text(prompt_final, encoding="utf-8")

        for repeticao in range(1, REPETICOES + 1):
            print(f"Executando Prompt {nome} (repetição {repeticao})...")
            resultado = chamar_modelo(client, prompt_final)

            arquivo_saida = pasta / f"saida_{nome}_rep{repeticao}.md"
            arquivo_saida.write_text(resultado.pop("texto"), encoding="utf-8")

            registrar(
                registros,
                arquivo_registro,
                etapa="execucao",
                caso_id=CASO_ID,
                modalidade="texto",
                arquivo_origem=relativo(ENTRADA),
                prompt=nome,
                arquivo_prompt=relativo(ARQUIVOS_PROMPT[nome]),
                versao_prompt=versao(modelo_prompt),
                arquivo_entrada=relativo(arquivo_entrada),
                repeticao=repeticao,
                arquivo_saida=relativo(arquivo_saida),
                **resultado,
            )

    print(f"Experimento concluído. Resultados em: {relativo(pasta)}")


if __name__ == "__main__":
    executar_experimento()
