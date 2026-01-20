# 📡 RJ Sites Address Viewer

A **Streamlit application** for searching, filtering, and visualizing telecom sites/towers in the state of Rio de Janeiro (RJ) using data from an Excel spreadsheet.  
Includes **robust city extraction**, **Google Maps integration**, **interactive Folium map**, and filtering by **site code (sigla)**, **city**, and **tower name**.

***

## ✨ Features

*   🔍 **Search by site code (sigla)** with an **OK button** (controlled form submission).
*   🧠 **Automatic city extraction** from the `nome` field:
    *   Supports **accents**, **hyphens**, and **apostrophes**.
    *   Detects and removes UF suffixes (`RJ`, `/RJ`, `- RJ`).
    *   Matches any of the **92 municipalities** of Rio de Janeiro (accent‑insensitive).
    *   Avoids misclassifying **street names** (e.g., `R.`, `AV.`, `COM`, etc.).
    *   Detects the **last municipality** in the string when the city appears at the end (e.g., `... VALENÇA`).
*   🏙️ **City selectbox**:
    *   Alphabetically sorted
    *   No `None` values
*   🧹 **Optional filter**: *Only show entries with recognized city*.
*   🗺️ **Interactive Folium map** with:
    *   Popups showing Sigla + Tower Name
    *   City
    *   Address
    *   Clickable **Google Maps link**
*   📋 **Filtered results table** including:
    `sigla`, `cidade`, `nome`, `endereco`, `lat`, `lon`.

***

## 🗂️ Spreadsheet Format (`enderecos.xlsx`)

Place the file **enderecos.xlsx** in the project root.

Accepted column names are automatically normalized as follows:

| Spreadsheet Column | Column Used in App |
| ------------------ | ------------------ |
| `sigla_da_torre`   | `sigla`            |
| `nome_da_torre`    | `nome`             |
| `endereço`         | `endereco`         |
| `latitude`         | `lat`              |
| `longitude`        | `lon`              |

### Example

```text
sigla_da_torre | nome                              | endereço                         | latitude | longitude
RJSAM2         | RIO DE JANEIRO - SAMBÓDROMO 2     | R. Marquês de Sapucaí, s/n       | -22,9129 | -43,1960
RJBMA_G1A01    | BARRA MANSA - RJBMA_G1A01         | Av. Joaquim Leite, 123           | -22,5445 | -44,1714
RJBZ1          | ARMAÇÃO DOS BÚZIOS - HOTEL ATLÂNTICO DE BUZIOS | Av. dos Gravatás, 67 | -22,7520 | -41,8870
```

The app automatically handles commas in coordinates (`-22,9129` → `-22.9129`).

***

## 🧰 Requirements

*   **Python 3.9+**

### Recommended `requirements.txt`

```txt
streamlit==1.36.0
pandas==2.2.2
openpyxl==3.1.5
folium==0.16.0
streamlit-folium==0.20.0
```

***

## ▶️ How to Run

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd your-repo
    ```

2.  Create and activate a virtual environment (optional):
    ```bash
    python -m venv .venv
    source .venv/bin/activate      # macOS/Linux
    .venv\Scripts\activate         # Windows
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Add your `enderecos.xlsx` file to the project root.

5.  Run the app:
    ```bash
    streamlit run app.py
    ```

6.  Open your browser at:
        http://localhost:8501

***

## ⚙️ Optional Configuration

Customize the Streamlit UI by adding:

### `.streamlit/config.toml`

```toml
[theme]
primaryColor = "#0E7AFE"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F7FB"
textColor = "#1F2937"
font = "sans serif"
```

***

## 🧠 How City Extraction Works

The app uses a multi‑step strategy to accurately determine the **municipality**:

1.  **Primary rule:** extract the segment before the first hyphen  
    Example:  
    `RIO DE JANEIRO - SAMBÓDROMO 2` → *Rio de Janeiro*

2.  **Cleanup:**
    *   Strip UF suffixes (`RJ`, `/RJ`, `- RJ`)
    *   Normalize accents
    *   Convert to intelligent Title Case
    *   Preserve prepositions (`de`, `da`, `dos`, …)

3.  **Fallback:** avoid names that look like street addresses  
    Example:  
    `RUA RODOLFO DANTAS` → *ignored*

4.  **Final fallback:** detect the **last** RJ municipality found anywhere in the string  
    Example:  
    `DGV-DESVIO GOMES VALENÇA` → *Valença*

***

## 🔎 Filters Overview

*   **Search by Sigla** → requires clicking **OK** to apply
*   **Show only recognized cities**
*   **Filter by City** (clean list)
*   **Filter by Tower Name**

***

## 🗺️ Map & Google Maps Integration

Each Folium marker popup includes:

*   Sigla
*   Tower name
*   City
*   Address
*   **Clickable Google Maps link**

URL example:

    https://www.google.com/maps/search/?api=1&query={lat},{lon}

***

## 🚀 Deployment

### Streamlit Cloud

1.  Push your repository to GitHub
2.  Go to <https://share.streamlit.io>
3.  Select your repo
4.  Deploy 🎉

### Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

```bash
docker build -t rj-sites .
docker run -p 8501:8501 rj-sites
```

***

## 🧪 Quick Test Checklist

*   Cities extracted correctly:
    *   `RIO DE JANEIRO - SAMBÓDROMO 2` → Rio de Janeiro
    *   `BARRA MANSA - RJBMA_G1A01` → Barra Mansa
    *   `ARMAÇÃO DOS BÚZIOS - HOTEL ATLÂNTICO DE BUZIOS` → Armação dos Búzios
    *   `SEROPEDICA - 4GRJSER5976` → Seropédica
    *   `MENA BARRETO COM R.SOROCABA` → (ignored as street)

*   Map markers appear

*   Google Maps links open correctly

*   Sigla search works only after clicking **OK**

***

## 🧩 Customization

You can easily modify:

*   Municipality list (`MUNICIPIOS_RJ`)
*   Preposition rules (`PREPOSICOES_PT`)
*   Street detection heuristics (`PALAVRAS_TIPO_LOGRADOURO`)
*   City aliases (`ALIASES`)

***

## 🐛 Troubleshooting

*   **No results?**
    *   Check if sigla filter is active
    *   Disable *Show only recognized cities*

*   **Map not showing?**
    *   Missing or invalid coordinates

*   **Google Maps link not working?**
    *   Ensure `&` is used (not `&amp;`)

***

## 📜 License

This project is licensed under the **MIT License**.

***

## 🤝 Contributing

Contributions, issues, and pull requests are welcome!

***

## 👤 Author

**Raphael Soares Robles De Franca**  
Developer focused on Python solutions for telecom, electrical engineering, and IT.

versão PT/BR 

Claro, Raphael! Segue um **README.md** completinho (em PT-BR) para você colar no GitHub do seu app Streamlit. Se quiser, eu gero também uma versão em inglês.

***

# 📡 Endereços dos Sites RJ

Aplicação **Streamlit** para visualizar e buscar **sites/torres** no RJ a partir de uma planilha Excel.  
Inclui **filtros por sigla**, **cidade** e **nome da torre**, **extração automática e robusta de cidade** (com acentos), **mapa interativo (Folium)** com marcadores e **links clicáveis para o Google Maps**.

!demo <!-- (opcional: adicione um print depois) -->

***

## ✨ Funcionalidades

*   **Busca por sigla** com **botão “OK”** (formulário) para aplicar o filtro sob demanda.
*   **Extração automática de cidade** a partir do campo `nome`:
    *   Suporte a **acentos**, **hífens** e **apóstrofos** (ex.: *Armação dos Búzios*, *Sant’Ana*).
    *   Remove sufixos de UF (ex.: `RJ`, `/RJ`, `- RJ`).
    *   Reconhece municípios do **RJ** (92 cidades) mesmo sem acentos no texto.
    *   Heurística para **evitar confundir logradouros** (ex.: *RUA*, *AV.*, *COM*).
    *   Opcional: tenta encontrar o **último município** presente quando a cidade vem no fim (ex.: `... VALENÇA`).
*   **Filtro “Somente entradas com cidade reconhecida”** (ativado por padrão).
*   **Select de cidade** ordenado, **sem `None`**.
*   **Mapa interativo** (Folium) com **popups** contendo:
    *   Sigla + Nome
    *   Cidade
    *   Endereço
    *   **Link para Google Maps** (abre em nova aba)
*   **Tabela de resultados** com colunas principais (`sigla`, `cidade`, `nome`, `endereco`, `lat`, `lon`).

***

## 🗂️ Estrutura da Planilha (`enderecos.xlsx`)

O app lê um arquivo **enderecos.xlsx** na raiz do projeto.  
As colunas podem ter variações, mas serão padronizadas conforme abaixo:

| Coluna na planilha | Coluna usada no app |
| ------------------ | ------------------- |
| `sigla_da_torre`   | `sigla`             |
| `nome_da_torre`    | `nome`              |
| `endereço`         | `endereco`          |
| `latitude`         | `lat`               |
| `longitude`        | `lon`               |

> As colunas **lat** e **lon** podem vir com vírgula (`-22,9876`), o app converte para ponto.

### 📄 Exemplo mínimo (Excel)

```text
sigla_da_torre | nome                              | endereço                         | latitude | longitude
RJSAM2         | RIO DE JANEIRO - SAMBÓDROMO 2     | R. Marquês de Sapucaí, s/n       | -22,9129 | -43,1960
RJBMA_G1A01    | BARRA MANSA - RJBMA_G1A01         | Av. Joaquim Leite, 123           | -22,5445 | -44,1714
RJBZ1          | ARMAÇÃO DOS BÚZIOS - HOTEL ATLÂNTICO DE BUZIOS | Av. dos Gravatás, 67 | -22,7520 | -41,8870
```

> Dica: mantenha `nome` no formato `CIDADE - ...` quando possível para aumentar a assertividade da extração.

***

## 🧰 Requisitos

*   **Python 3.9+**
*   Pacotes:
    *   `streamlit`
    *   `pandas`
    *   `openpyxl`
    *   `folium`
    *   `streamlit-folium`

### `requirements.txt` (sugestão)

```txt
streamlit==1.36.0
pandas==2.2.2
openpyxl==3.1.5
folium==0.16.0
streamlit-folium==0.20.0
```

> Versões podem variar. Em produção, fixe versões para reprodutibilidade.

***

## ▶️ Como executar

1.  **Clone** o repositório e entre na pasta:
    ```bash
    git clone https://github.com/seu-usuario/seu-repo.git
    cd seu-repo
    ```

2.  **Crie e ative** um ambiente virtual (opcional, mas recomendado):
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Instale** as dependências:
    ```bash
    pip install -r requirements.txt
    ```

4.  Coloque o arquivo **enderecos.xlsx** na raiz do projeto.

5.  **Rode** o app:
    ```bash
    streamlit run app.py
    ```

6.  Abra no navegador: `http://localhost:8501`

***

## ⚙️ Configurações opcionais

Crie um arquivo **`.streamlit/config.toml`** para personalizar o tema:

```toml
[theme]
primaryColor = "#0E7AFE"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F7FB"
textColor = "#1F2937"
font = "sans serif"
```

***

## 🧠 Como funciona a extração de cidade (resumo)

*   Prioriza o trecho **antes do primeiro hífen** (`CIDADE - ...`).
*   Remove sufixos de UF (`RJ`, `/RJ`, `- RJ`).
*   Mantém **acentos, hífens e apóstrofos** e aplica **Title Case inteligente** (preposições minúsculas).
*   **Evita** classificar entradas que parecem **logradouro** (ex.: começam com `R.` / `AV.` ou possuem `COM` de cruzamento).
*   Se não identificar pela regra principal, tenta localizar o **último município do RJ** mencionado em qualquer parte do texto.
*   Normaliza grafias comuns (ex.: `Seropedica` → `Seropédica`).

***

## 🔎 Uso dos filtros

*   **Buscar por sigla**: digite a sigla e clique em **OK** para aplicar.
*   **Somente entradas com cidade reconhecida**: marcado por padrão (reduz ruído).
*   **Localidade (cidade)**: opções **ordenadas** e **sem valores nulos**.
*   **Nome da torre**: filtro adicional por nome exato.

***

## 🗺️ Mapa e Google Maps

*   Cada marcador exibe **sigla, nome, cidade, endereço** e um **link clicável**:
    *   `https://www.google.com/maps/search/?api=1&query={lat},{lon}`
*   O link abre em **nova aba**.

***

## 🚀 Deploy

### Streamlit Community Cloud

1.  Crie um repositório com:
    *   `app.py`
    *   `enderecos.xlsx` (ou configure para buscar de um storage)
    *   `requirements.txt`
2.  Conecte o repo em **<https://share.streamlit.io>**.
3.  Configure os **secrets** se for integrar com serviços externos (opcional).

### Docker (opcional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

```bash
docker build -t sites-rj .
docker run -p 8501:8501 sites-rj
```

***

## 🧪 Testes rápidos

*   Verifique se a planilha está na raiz e se as colunas são reconhecidas.
*   Confirme que coordenadas (`lat`, `lon`) não estão vazias após a conversão (vírgula → ponto).
*   Teste exemplos:
    *   `RIO DE JANEIRO - SAMBÓDROMO 2` → **Rio de Janeiro**
    *   `BARRA MANSA - RJBMA_G1A01` → **Barra Mansa**
    *   `ARMAÇÃO DOS BÚZIOS - HOTEL ATLÂNTICO DE BUZIOS` → **Armação dos Búzios**
    *   `SEROPEDICA - 4GRJSER5976` → **Seropédica**
    *   `MENA BARRETO COM R.SOROCABA` → **(não classifica cidade)**

***

## 🧩 Personalização

*   **Lista de municípios**: `MUNICIPIOS_RJ` (pode adaptar para outros estados).
*   **Aliases** (normalização de grafias): ajuste o dicionário `ALIASES`.
*   **Heurísticas de logradouro**: edite `PALAVRAS_TIPO_LOGRADOURO` e `parece_logradouro`.

***

## 🐛 Solução de problemas

*   **Nenhum site aparece**:
    *   Verifique se o filtro de **sigla** está ativo (botão **OK**).
    *   Desmarque **“Somente entradas com cidade reconhecida”**.
*   **Mapa não aparece**:
    *   Confira se há **lat/lon** válidos (não `NaN`).
    *   Linhas sem coordenadas são **ignoradas** no mapa.
*   **Link do Google Maps não abre**:
    *   Certifique-se de que a URL está com `&` e **não** `&amp;`.

***

## 📜 Licença

Este projeto está sob a licença **MIT**. Veja o arquivo `LICENSE` para mais detalhes.

***

## 🤝 Contribuições

Contribuições são bem-vindas!  
Abra uma **issue** para sugestões/bugs ou envie um **pull request**.

***

## 👤 Autor

**Raphael Soares Robles De Franca**  
Foco em soluções Python para telecom, elétrica e TI.






