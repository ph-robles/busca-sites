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

