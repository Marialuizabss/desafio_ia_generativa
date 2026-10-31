"""Abertura simultânea do índice e falha inesperada na consulta (RF17 e RF20).

Rodam offline: o índice é aberto numa pasta temporária e nenhum modelo de
embeddings é carregado.
"""

import threading

from src.consulta_acervo import MENSAGEM_FALHA_INESPERADA, classificar_consulta
from src.provider_adapter import ErroProvedor
from src.vector_store import obter_colecao


def test_duas_aberturas_simultaneas_do_indice_nao_falham(tmp_path):
    # Sem a trava, duas consultas ao mesmo tempo na interface quebravam com
    # "'RustBindingsAPI' object has no attribute 'bindings'" (8 em 10 rodadas).
    for rodada in range(5):
        pasta = tmp_path / f"indice_{rodada}"
        largada = threading.Barrier(2)
        erros = []

        def abrir():
            largada.wait()
            try:
                obter_colecao(pasta=pasta).count()
            except Exception as erro:
                erros.append(repr(erro))

        threads = [threading.Thread(target=abrir) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert erros == [], f"rodada {rodada}: {erros}"


def test_erro_inesperado_nao_mostra_detalhe_tecnico():
    erro = AttributeError("'RustBindingsAPI' object has no attribute 'bindings'")
    saida = classificar_consulta(erro=erro)

    assert saida["tipo"] == "falha"
    assert saida["texto"] == MENSAGEM_FALHA_INESPERADA
    assert "RustBindingsAPI" not in saida["texto"] + saida["justificativa"]
    assert saida["resposta"] is None
    assert saida["estado"] == "revisar"


def test_falha_do_provedor_continua_com_a_mensagem_em_portugues():
    erro = ErroProvedor("Não foi possível conectar ao serviço.", auditoria={})
    saida = classificar_consulta(erro=erro)

    assert saida["tipo"] == "falha"
    assert "Não foi possível conectar ao serviço." in saida["texto"]
    assert saida["texto"] != MENSAGEM_FALHA_INESPERADA
