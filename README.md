# 🧠 Central Inteligente de Atendimento e Comunicação Institucional

**Desafio Prático 01 — Inteligência Artificial Generativa | FIC_DEV 2026**

Protótipo multimodal para apoiar o atendimento institucional por meio de inteligência artificial generativa, com foco em automação assistida, acessibilidade, segurança, rastreabilidade e revisão humana.

**Status:** Em desenvolvimento

## 📌 Sobre o projeto

O projeto propõe uma central capaz de processar solicitações fictícias em diferentes formatos e apoiar a elaboração de respostas institucionais.

As funcionalidades previstas incluem:

- Processamento e classificação de solicitações textuais.
- Transcrição de mensagens de áudio.
- Extração de informações de documentos por visão computacional.
- Geração de minutas de respostas institucionais.
- Síntese de voz para acessibilidade.
- Geração e edição de imagens.
- Revisão e aprovação humana.
- Registro de execuções e proteção de dados.

**Importante:** o sistema não deve enviar respostas automaticamente aos cidadãos. As informações geradas precisam ser verificadas antes de sua utilização.

## 🛠️ Tecnologias

| Tecnologia | Finalidade |
|---|---|
| Python | Implementação da aplicação |
| Git e GitHub | Versionamento e colaboração |
| JSON | Configurações, extrações e metadados |
| OpenAI API | Integração com modelos de inteligência artificial |
| python-dotenv | Carregamento de variáveis de ambiente |
| unittest | Testes automatizados |
| Markdown | Documentação técnica |

Os modelos utilizados nas funcionalidades de áudio, visão e geração de imagens estão definidos nos respectivos módulos do projeto.

## 🏗️ Arquitetura

O fluxo geral previsto é:

1. Recebimento de uma entrada textual, sonora ou visual.
2. Validação da entrada e identificação de arquivos ausentes.
3. Extração e processamento das informações.
4. Análise da solicitação e preparação da resposta.
5. Geração da minuta institucional.
6. Revisão humana.
7. Produção de recursos acessíveis, quando aplicável.
8. Registro dos resultados e metadados da execução.

A implementação é organizada em módulos Python independentes.

## 📋 Requisitos funcionais

O projeto contempla 13 requisitos funcionais. O quadro abaixo distingue as funcionalidades já verificadas daquelas que ainda precisam de validação.

| Requisito | Descrição | Situação |
|---|---|---|
| RF01 | Inicialização e configuração | A validar |
| RF02 | Experimento de engenharia de prompts | A validar |
| RF03 | Prompt seguro e conteúdo não confiável | A validar |
| RF04 | Chamada de API e tratamento de falhas | A validar |
| RF05 | Entrada textual e extração estruturada | A validar |
| RF06 | Transcrição de áudio | Testes aprovados |
| RF07 | Síntese de voz e acessibilidade | Testes aprovados |
| RF08 | Visão e OCR | Testes aprovados |
| RF09 | Geração da minuta institucional | A validar |
| RF10 | Geração ou edição de imagem | Testes aprovados |
| RF11 | Registro e rastreabilidade | A validar |
| RF12 | LGPD, privacidade e minimização | A validar |
| RF13 | Avaliação de qualidade e revisão humana | Casos de teste e gabaritos adicionados; validação integral pendente |

A situação de cada requisito deve ser atualizada conforme a implementação, os testes e as evidências forem revisados.

## 📂 Estrutura do projeto

```text
desafio_ia_generativa/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── config.json
├── dados/
│   ├── originais/
│   ├── gabaritos/
│   └── processados/
├── src/
│   ├── main.py
│   ├── llm_client.py
│   ├── prompts.py
│   ├── audio.py
│   ├── vision.py
│   ├── image_generation.py
│   ├── layout_rf10.py
│   └── audit.py
├── tests/
│   ├── test_audio.py
│   ├── test_image_generation.py
│   └── test_vision.py
├── prompts/
├── resultados/
│   ├── minutas/
│   ├── audios/
│   ├── imagens/
│   └── logs/
└── documentacao/
```

## ⚙️ Instalação e configuração

### Pré-requisitos

- Python compatível com as dependências do projeto.
- Git.
- Chave de API válida para os serviços utilizados.
- Conexão com a internet para chamadas aos serviços externos.

### 1. Criar e ativar o ambiente virtual

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar as dependências

```powershell
python -m pip install -r requirements.txt
```

### 3. Configurar as credenciais

Crie o arquivo `.env` a partir do modelo:

```powershell
Copy-Item .env.example .env
```

Preencha a variável de ambiente correspondente à chave de API, conforme indicado no `.env.example`.

**Segurança:** não compartilhe o arquivo `.env` e não envie chaves ou credenciais para o repositório.

## ▶️ Execução

O ponto de entrada previsto para a aplicação é:

```powershell
python -m src.main
```

A execução integrada deve ser validada para confirmar o funcionamento do fluxo completo.

As funcionalidades individuais estão organizadas em seus respectivos módulos dentro de `src/`.

### Arquivos de entrada e saída

- **RF06:** recebe `dados/originais/entrada_audio.mp3` e produz a transcrição em `dados/processados/`, com metadados em `resultados/logs/`.
- **RF07:** utiliza `resultados/minutas/texto_rf07.txt` e gera `resultados/audios/audio_rf07.mp3`.
- **RF08:** utiliza a imagem `dados/processados/entrada_rf08_pagina1.png` e grava a extração estruturada em `dados/processados/extracao_rf08.json`. O PDF original deve ser convertido ou preparado como imagem antes dessa execução.
- **RF10:** gera ou edita imagens e registra os resultados e metadados em `resultados/`.

Os arquivos de entrada necessários devem estar presentes nos caminhos esperados pelos respectivos módulos.

## 🧪 Testes e avaliação

Os testes automatizados são implementados com `unittest`.

Para executar toda a suíte:

```powershell
python -m unittest discover -s tests -v
```

Para testar somente o RF08:

```powershell
python -m unittest tests.test_vision -v
```

Para testar somente os requisitos de áudio:

```powershell
python -m unittest tests.test_audio -v
```

Para verificar a sintaxe de um módulo:

```powershell
python -m py_compile src/vision.py
```

A avaliação do sistema deve considerar:

- Fidelidade às informações de entrada.
- Completude e consistência dos resultados.
- Formato e linguagem institucional.
- Ausência de informações inventadas.
- Resistência a instruções maliciosas presentes nos documentos.
- Tratamento de entradas inválidas e falhas de API.
- Registro da origem das informações.
- Revisão humana e rastreabilidade.

Os resultados dos testes devem ser registrados após cada alteração relevante.

## 🔐 Segurança e LGPD

O desenvolvimento considera os seguintes princípios:

- Utilização de dados fictícios para os experimentos.
- Proteção de chaves e credenciais.
- Minimização de dados pessoais enviados aos provedores.
- Tratamento de documentos e instruções incorporadas como conteúdo não confiável.
- Identificação de campos ausentes ou ilegíveis.
- Registro de metadados relevantes para auditoria.
- Revisão humana antes da aprovação de informações institucionais.
- Ausência de envio automático de respostas aos cidadãos.

A implementação efetiva de cada controle deve ser confirmada por inspeção do código e testes específicos.

## 📊 Resultados e evidências

Os resultados gerados são organizados nas pastas `dados/processados/` e `resultados/`, de acordo com a funcionalidade executada.

A pasta `dados/gabaritos/` contém arquivos de referência utilizados nos casos de teste. A documentação complementar inclui registros de validação e evidências disponíveis.

Os resultados devem ser avaliados considerando as limitações dos modelos e a necessidade de conferência humana.

## 📚 Documentação

A documentação técnica complementar está organizada em `documentacao/`, incluindo registros de validação e casos de teste.

Os arquivos de referência e os exemplos de entrada estão organizados em `dados/originais/` e `dados/gabaritos/`.

## 👩‍💻 Desenvolvimento

**Maria Luiza**
Desafio Prático 01 — FIC_DEV 2026
Programador de Sistemas com Inteligência Artificial

---

*Projeto desenvolvido para fins educacionais, com uso de inteligência artificial generativa e supervisão humana.*
