
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
BRASAO = BASE / "dados/entrada/brasao.png"
SAIDA = BASE / "dados/saida/imagem_rf10_layout_formal.png"

LARGURA, ALTURA = 1024, 1536
VERDE = "#165C3F"
VERDE_ESCURO = "#1E4636"
TEXTO = "#334A3E"
CINZA = "#62756A"
CLARO = "#EFF5F0"
BRANCO = "#FFFFFF"

FONTES = Path("C:/Windows/Fonts")

titulo = ImageFont.truetype(str(FONTES / "georgiab.ttf"), 42)
subtitulo = ImageFont.truetype(str(FONTES / "segoeuib.ttf"), 27)
corpo = ImageFont.truetype(str(FONTES / "segoeui.ttf"), 25)
pequena = ImageFont.truetype(str(FONTES / "segoeui.ttf"), 20)
cabecalho = ImageFont.truetype(str(FONTES / "segoeuib.ttf"), 22)

imagem = Image.new("RGB", (LARGURA, ALTURA), "#E9EEEA")
d = ImageDraw.Draw(imagem)

# Folha branca
d.rectangle((55, 40, 969, 1496), fill=BRANCO, outline="#CFD9D2", width=2)

def centralizar(texto, y, fonte, cor):
    caixa = d.textbbox((0, 0), texto, font=fonte)
    largura = caixa[2] - caixa[0]
    d.text(((LARGURA - largura) / 2, y), texto, font=fonte, fill=cor)

def texto_linhas(texto, x, y, fonte, cor, max_largura, espaco=12):
    palavras = texto.split()
    linha = ""
    for palavra in palavras:
        tentativa = f"{linha} {palavra}".strip()
        if d.textlength(tentativa, font=fonte) <= max_largura:
            linha = tentativa
        else:
            d.text((x, y), linha, font=fonte, fill=cor)
            y += fonte.size + espaco
            linha = palavra
    if linha:
        d.text((x, y), linha, font=fonte, fill=cor)
        y += fonte.size + espaco
    return y

# Brasão original
with Image.open(BRASAO) as b:
    b = b.convert("RGBA")
    b.thumbnail((130, 125))
    x = (LARGURA - b.width) // 2
    imagem.paste(b, (x, 85), b)

centralizar("GOVERNO DO ESTADO DE MATO GROSSO", 225, cabecalho, VERDE_ESCURO)
centralizar("ESCOLA TÉCNICA ESTADUAL", 260, pequena, CINZA)

# Faixa de título
d.rectangle((90, 315, 934, 475), fill=VERDE)
centralizar("COMUNICADO INFORMATIVO", 337, pequena, "#D9E9DD")
centralizar("ORIENTAÇÕES PARA", 372, titulo, BRANCO)
centralizar("MATRÍCULA", 423, titulo, BRANCO)

# Introdução
d.text((125, 520), "Prezados estudantes,", font=subtitulo, fill=VERDE_ESCURO)

texto_linhas(
    "Para dar continuidade ao processo de matrícula, acompanhe as "
    "orientações fornecidas pela secretaria escolar e verifique os "
    "documentos necessários para a efetivação.",
    125, 570, corpo, TEXTO, 770
)

d.line((125, 740, 899, 740), fill="#D1DDD4", width=2)

# Ícones institucionais discretos
def icone_documento(x, y):
    d.rounded_rectangle(
        (x, y, x + 38, y + 46),
        radius=4,
        outline=VERDE,
        width=3,
    )
    d.line((x + 9, y + 16, x + 29, y + 16), fill=VERDE, width=3)
    d.line((x + 9, y + 25, x + 29, y + 25), fill=VERDE, width=3)
    d.line((x + 9, y + 34, x + 23, y + 34), fill=VERDE, width=3)


def icone_calendario(x, y):
    d.rounded_rectangle(
        (x, y + 7, x + 42, y + 46),
        radius=4,
        outline=VERDE,
        width=3,
    )
    d.line((x, y + 19, x + 42, y + 19), fill=VERDE, width=3)
    d.line((x + 11, y, x + 11, y + 13), fill=VERDE, width=4)
    d.line((x + 31, y, x + 31, y + 13), fill=VERDE, width=4)
    d.line((x + 11, y + 33, x + 19, y + 40), fill=VERDE, width=3)
    d.line((x + 19, y + 40, x + 33, y + 25), fill=VERDE, width=3)


icone_documento(125, 775)
icone_calendario(125, 920)

# Seção de documentação
d.text((185, 780), "DOCUMENTAÇÃO", font=subtitulo, fill=VERDE_ESCURO)
texto_linhas(
    "Consulte a secretaria escolar para confirmar a documentação exigida.",
    125, 825, corpo, TEXTO, 770
)

# Seção de acompanhamento
d.text((185, 925), "ACOMPANHAMENTO", font=subtitulo, fill=VERDE_ESCURO)
texto_linhas(
    "Acompanhe a análise da solicitação e as orientações sobre as próximas etapas.",
    125, 970, corpo, TEXTO, 770
)

# Aviso importante
d.rounded_rectangle((110, 1100, 914, 1265), radius=12, fill=CLARO)
d.text((140, 1125), "INFORMAÇÃO IMPORTANTE", font=subtitulo, fill=VERDE_ESCURO)
texto_linhas(
    "O recebimento da solicitação não representa a confirmação automática da matrícula.",
    140, 1175, corpo, TEXTO, 735
)

# Rodapé
d.line((125, 1330, 899, 1330), fill="#D1DDD4", width=2)
centralizar("Secretaria Escolar", 1350, cabecalho, VERDE_ESCURO)
centralizar("Peça demonstrativa — Projeto FIC_DEV 2026", 1388, corpo, CINZA)
centralizar("Não constitui comunicado oficial", 1430, pequena, CINZA)

SAIDA.parent.mkdir(parents=True, exist_ok=True)
imagem.save(SAIDA)

print(f"Layout formal criado: {SAIDA}")
