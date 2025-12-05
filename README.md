# Staff Directory Crawler

## Descripcion del Proyecto

Herramienta de crawling inteligente para extraer informacion de contacto desde paginas de directorios de staff de diversas organizaciones, utilizando IA para interpretar estructuras HTML variadas.

## Problema que Resuelve

Las paginas de directorios de staff presentan multiples desafios:

- **Estructuras HTML variadas**: Cada sitio web tiene su propia estructura
- **Emails ocultos**: Muchos sitios ocultan emails en atributos `mailto:`, JavaScript, o los ofuscan para evitar spam
- **Paginacion**: Los directorios grandes dividen el contenido en multiples paginas
- **Contenido dinamico**: Algunas paginas cargan datos mediante JavaScript/AJAX
- **Formatos inconsistentes**: Nombres, roles y emails pueden estar en diferentes formatos

## Objetivo

Dado una URL de un directorio de staff, extraer de forma automatizada:

| Campo | Descripcion |
|-------|-------------|
| **Nombre** | Nombre completo del miembro del staff |
| **Rol** | Cargo o posicion en la organizacion |
| **Email** | Direccion de correo electronico |

## Stack Tecnologico

| Tecnologia | Proposito |
|------------|-----------|
| **Python 3.8+** | Lenguaje base del proyecto |
| **crawl4ai** | Libreria de crawling con soporte para LLM |
| **OpenAI API** | Extraccion inteligente de datos mediante IA (GPT-5-nano) |
| **Pydantic** | Validacion de datos y generacion de schemas |
| **asyncio** | Operaciones asincronas para crawling eficiente |

## Arquitectura

```
python-crawl/
├── main.py              # Entry point - configura URL y ejecuta crawler
├── staff_crawler.py     # StaffDirectoryCrawler - logica principal de extraccion
├── models.py            # Modelos Pydantic: StaffMember, StaffDirectory
├── requirements.txt     # Dependencias del proyecto
├── .env                 # Variables de entorno (OPENAI_API_KEY)
└── results/             # Directorio de salida CSV (auto-generado)
```

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                   StaffDirectoryCrawler                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  BrowserConfig  │  │ CrawlerRunConfig│                  │
│  │  - headless     │  │  - cache_mode   │                  │
│  │  - verbose      │  │  - extraction   │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LLMExtractionStrategy (OpenAI GPT-5-nano)           │  │
│  │  - Schema basado en Pydantic (StaffDirectory)        │  │
│  │  - Chunking automatico para paginas grandes          │  │
│  │  - Temperatura 0.0 para resultados consistentes      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Metodos:                                                   │
│  - extract(url) -> List[StaffMember]                       │
│  - extract_many(urls) -> List[StaffMember]                 │
│  - extract_with_pagination(url, config) -> List[StaffMember]│
│  - to_csv(staff) -> str (path al archivo)                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Extraccion

```
URL de Staff Directory
         │
         ▼
┌─────────────────────┐
│   AsyncWebCrawler   │
│   (Playwright)      │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Renderizado JS     │
│  HTML completo      │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  LLMExtraction      │
│  Strategy           │
│  (OpenAI GPT-5-nano) │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Datos Extraidos    │
│  - nombre           │
│  - rol              │
│  - email            │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  CSV Output         │
│  results/*.csv      │
└─────────────────────┘
```

## Instalacion

```bash
# Clonar repositorio
git clone <repository-url>
cd python-crawl

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar navegador para crawl4ai (Playwright/Chromium)
python -m crawl4ai.install
```

## Configuracion

Crear archivo `.env` en la raiz del proyecto:

```env
OPENAI_API_KEY=sk-...
```

## Uso

### Modo Basico

Editar la URL en `main.py` y ejecutar:

```bash
source venv/bin/activate && python main.py
```

### Uso Programatico

```python
import asyncio
from staff_crawler import StaffDirectoryCrawler

async def main():
    crawler = StaffDirectoryCrawler(verbose=True)

    # Extraccion de una URL
    staff = await crawler.extract("https://example.com/staff")

    # Extraccion de multiples URLs en paralelo
    urls = [
        "https://example.com/staff?page=1",
        "https://example.com/staff?page=2"
    ]
    all_staff = await crawler.extract_many(urls)

    # Exportar a CSV
    csv_path = crawler.to_csv(staff)
    print(f"Exportado a: {csv_path}")

asyncio.run(main())
```

### Extraccion con Paginacion Automatica

Para directorios con multiples paginas que usan boton "Next/Siguiente":

```python
import asyncio
from staff_crawler import StaffDirectoryCrawler, PaginationConfig

async def main():
    crawler = StaffDirectoryCrawler(verbose=True)

    # Configuracion por defecto (detecta automaticamente botones comunes)
    staff = await crawler.extract_with_pagination("https://example.com/staff")

    # O con configuracion personalizada
    pagination = PaginationConfig(
        next_button_selector="a.next-page, .pagination .next",  # Selector CSS
        max_pages=10,  # Limite de paginas
        wait_timeout=5000  # Timeout en ms
    )
    staff = await crawler.extract_with_pagination("https://example.com/staff", pagination)

    # Exportar resultados
    csv_path = crawler.to_csv(staff)
    print(f"Exportado: {csv_path}")

asyncio.run(main())
```

#### Selectores por Defecto

El crawler detecta automaticamente estos patrones de botones:
- `a:has-text('Next')`, `a:has-text('Siguiente')`
- `a.next`, `.next a`
- `[rel='next']`
- `a[aria-label*='next']`
- `.pagination a:last-child`

### Resultado Esperado

```
Extrayendo informacion de staff desde: https://example.com/staff
--------------------------------------------------
Se encontraron 45 miembros del staff.

Datos exportados a: results/staff_20241205_143022.csv

Preview (primeros 5):
--------------------------------------------------
  John Doe | CEO | john@example.com
  Jane Smith | CTO | jane@example.com
  ...
```

## Requisitos del Sistema

- Python 3.8+
- API Key de OpenAI
- Conexion a Internet
- ~500MB espacio (para Playwright/Chromium)

## Estado del Proyecto

- [x] Definicion del problema
- [x] Investigacion de crawl4ai
- [x] Estructura del proyecto
- [x] Implementacion del crawler base
- [x] Extraccion con LLM (GPT-5-nano)
- [x] Exportacion a CSV
- [x] Manejo de multiples URLs (extract_many)
- [x] Paginacion automatica (extract_with_pagination)
- [ ] Tests unitarios
- [ ] Manejo avanzado de errores
- [ ] Documentacion de API

## Dependencias

```
crawl4ai>=0.4.2
openai>=1.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

---

*Proyecto en desarrollo activo*
