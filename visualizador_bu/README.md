# Visualizador de Boletim de Urna

Aplicação local para explorar os arquivos CSV de Boletim de Urna (BU). Os dados utilizados foram obtidos no site oficial do Tribunal Superior Eleitoral (TSE). A aplicação tem finalidade educacional: apoiar estudos sobre a estrutura dos boletins de urna e o funcionamento da contabilização dos votos. Não é uma aplicação oficial do TSE nem substitui os canais oficiais de apuração e divulgação dos resultados.

Você pode colocar arquivos `.csv` ou `.zip` na pasta de dados. Somente o estado selecionado é preparado em cache temporário do Windows; o ZIP original não é modificado. A tabela na tela mostra no máximo 500 registros por vez.

## Executar no Windows

No terminal, a partir desta pasta:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Abra o endereço local mostrado pelo Streamlit no navegador. A pasta padrão de dados é `../Boletim_Urna_CSV`. Para incluir outros estados, coloque os arquivos `.zip` ou `.csv` nessa pasta ou informe outra pasta no campo **Pasta com arquivos CSV**. ZIPs que não tenham CSV são ignorados e listados como aviso.

O leitor espera arquivos separados por ponto e vírgula e usa codificação Latin-1, compatível com o CSV atual. DuckDB consulta os arquivos diretamente, sem importar a base para o Excel.