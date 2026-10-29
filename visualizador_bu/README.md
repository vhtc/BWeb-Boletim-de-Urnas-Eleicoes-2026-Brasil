# Visualizador de Boletins de Urna (BU)

Aplicação local desenvolvida em Python para explorar e consultar arquivos CSV de **Boletins de Urna (BU)** disponibilizados pelo Tribunal Superior Eleitoral (TSE).

A ferramenta permite analisar os dados dos boletins de urna por estado, facilitando o estudo da estrutura dos arquivos, dos registros eleitorais e do processo de contabilização dos votos.

> **Finalidade educacional:** este projeto tem caráter exclusivamente educacional e analítico. Não é uma aplicação oficial do TSE, não realiza apuração eleitoral própria e não substitui os canais oficiais de divulgação dos resultados.

## Funcionalidades

- **Leitura de arquivos CSV:** consulta os dados dos boletins de urna diretamente dos arquivos disponíveis na pasta configurada.
- **Suporte a arquivos ZIP:** identifica e lê arquivos CSV compactados, sem modificar os arquivos originais.
- **Seleção por estado:** prepara em cache temporário do Windows apenas os dados do estado selecionado.
- **Consultas eficientes:** utiliza o DuckDB para consultar os arquivos sem precisar importar toda a base para o Excel.
- **Visualização tabular:** exibe até 500 registros por vez, facilitando a navegação pelos dados.
- **Validação dos arquivos:** ignora arquivos ZIP que não contenham CSV e apresenta avisos sobre esses casos.
- **Configuração da pasta de dados:** permite utilizar a pasta padrão ou informar outro diretório com os arquivos eleitorais.

## Tecnologias utilizadas

- **Python** — linguagem de programação da aplicação.
- **Streamlit** — interface web local para visualização e interação com os dados.
- **DuckDB** — mecanismo de consulta analítica dos arquivos CSV.
- **CSV e ZIP** — formatos utilizados para armazenamento e distribuição dos dados.

## Requisitos

Antes de executar a aplicação, verifique se o ambiente possui:

- Windows;
- Python instalado e disponível no terminal;
- Arquivo `requirements.txt` na pasta do projeto;
- Arquivos CSV ou ZIP contendo os boletins de urna.

## Instalação e execução no Windows

### 1. Acesse a pasta do projeto

Abra o PowerShell ou outro terminal e navegue até o diretório da aplicação.

```powershell
cd "C:\caminho\para\VisualizadorBU"
```

Substitua o caminho pelo diretório em que o projeto está salvo.

### 2. Crie o ambiente virtual

```powershell
python -m venv .venv
```

### 3. Ative o ambiente virtual

```powershell
.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a execução do script de ativação, ajuste a política de execução somente se necessário e conforme as regras de segurança do seu ambiente.

### 4. Instale as dependências

```powershell
python -m pip install -r requirements.txt
```

### 5. Inicie a aplicação

```powershell
streamlit run app.py
```

Após a inicialização, o Streamlit exibirá o endereço local da aplicação no terminal. Abra esse endereço no navegador para começar a utilizar o visualizador.

## Configuração dos arquivos de dados

Por padrão, a aplicação procura os arquivos na pasta:

```text
../Boletim_Urna_CSV
```

Essa pasta é relativa ao diretório de execução da aplicação.

Para disponibilizar os dados, coloque os arquivos `.csv` ou `.zip` nesse diretório. Se os arquivos estiverem em outro local, informe o caminho desejado no campo **Pasta com arquivos CSV**, disponível na interface.

### Formatos e processamento

O leitor foi configurado para trabalhar com arquivos CSV que apresentam as seguintes características:

| Propriedade | Configuração |
|---|---|
| Formato de entrada | CSV ou ZIP contendo CSV |
| Separador de campos | Ponto e vírgula (`;`) |
| Codificação | Latin-1 |
| Consulta dos dados | DuckDB |
| Limite de exibição | 500 registros por vez |
| Preparação temporária | Cache local do Windows para o estado selecionado |

**Importante:** o arquivo ZIP original não é alterado. O cache temporário é utilizado para preparar os dados do estado selecionado, evitando o processamento desnecessário dos demais estados.

Arquivos ZIP que não contenham arquivos CSV são ignorados e relacionados nos avisos apresentados pela aplicação.

## Fonte dos dados

Os arquivos utilizados são obtidos no portal oficial do Tribunal Superior Eleitoral.

- [Tribunal Superior Eleitoral (TSE)](https://www.tse.jus.br/)
- [Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/)

A disponibilidade, a estrutura e a codificação dos arquivos podem variar conforme o conjunto de dados e a eleição consultada. A aplicação considera o formato CSV descrito neste documento.

## Observações e limitações

- A aplicação realiza consultas sobre os arquivos fornecidos pelo usuário; não busca nem atualiza automaticamente os dados no TSE.
- A tabela apresenta até 500 registros por vez. Esse limite de exibição não significa necessariamente que a consulta esteja restrita a apenas 500 registros.
- O desempenho depende do volume de dados, das características dos arquivos e dos recursos disponíveis no computador.
- Os dados apresentados devem ser interpretados considerando a estrutura e a documentação oficial dos boletins de urna.
- Resultados obtidos pela aplicação não devem ser tratados isoladamente como evidência de irregularidade eleitoral.

## Estrutura esperada do projeto

```text
VisualizadorBU/
├── app.py
├── requirements.txt
├── README.md
└── .venv/                 # Ambiente virtual local
```

A pasta de dados pode ficar fora do diretório do projeto, conforme a configuração padrão ou o caminho informado na interface.

## Licença e responsabilidade

Este projeto é destinado a estudos, exploração de dados e aprendizado sobre os boletins de urna. Antes de redistribuir o código ou os conjuntos de dados, verifique as condições de licença e uso aplicáveis a cada recurso.

O projeto é independente do Tribunal Superior Eleitoral (TSE), não possui vínculo institucional com o órgão e não constitui ferramenta oficial de apuração ou auditoria eleitoral.
