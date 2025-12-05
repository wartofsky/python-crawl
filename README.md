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
| **OpenAI API** | Extraccion inteligente de datos mediante IA (GPT-4o-mini) |
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
│  │  Estrategia Hibrida de Extraccion                    │  │
│  │  - LLM (GPT-4o-mini) para contenido visible          │  │
│  │  - Regex para emails embebidos en HTML               │  │
│  │  - Auto-deteccion del mejor metodo                   │  │
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
│  Analisis de        │
│  Contenido          │──────────────────┐
└─────────────────────┘                  │
         │                               │
         ▼                               ▼
┌─────────────────────┐    ┌─────────────────────┐
│  Emails Embebidos?  │    │  Emails Visibles?   │
│  (mailto:, JSON)    │    │  (en markdown)      │
└─────────────────────┘    └─────────────────────┘
         │                               │
         ▼                               ▼
┌─────────────────────┐    ┌─────────────────────┐
│  Extraccion Regex   │    │  Extraccion LLM     │
│  (rapida, precisa)  │    │  (GPT-4o-mini)      │
└─────────────────────┘    └─────────────────────┘
         │                               │
         └───────────────┬───────────────┘
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

## Estrategia de Extraccion Hibrida

El crawler utiliza una estrategia hibrida que selecciona automaticamente el mejor metodo:

### 1. Extraccion por Patrones (Regex)
Usada cuando los emails estan embebidos en el HTML (no visibles directamente):
- Patrones `mailto:` con nombres en aria-label
- Estructuras JSON embebidas en atributos
- Links de email con texto adyacente

**Ventajas**: Rapida, precisa, sin costo de API

### 2. Extraccion por LLM (GPT-4o-mini)
Usada cuando los emails son visibles en el contenido renderizado:
- Interpreta estructuras HTML variadas
- Extrae roles y posiciones contextuales
- Maneja formatos inconsistentes

**Ventajas**: Flexible, entiende contexto

### Auto-Deteccion
El crawler analiza automaticamente:
1. Cuenta emails en HTML crudo vs markdown renderizado
2. Si hay mas emails en HTML que en markdown → usa Regex
3. Si los emails son visibles en markdown → usa LLM

## Instalacion

```bash
# Clonar repositorio
git clone https://github.com/wartofsky/python-crawl.git
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

El crawler detecta automaticamente dos tipos de paginacion:

#### 1. Paginacion URL-Based (Automatica)
Detecta patrones como `?page=2`, `?page_no=2`, `?const_page=2` y navega todas las paginas automaticamente.

```python
import asyncio
from staff_crawler import StaffDirectoryCrawler, PaginationConfig

async def main():
    crawler = StaffDirectoryCrawler(verbose=True)

    # Detecta automaticamente paginacion URL
    staff = await crawler.extract_with_pagination(
        "https://example.com/staff",
        PaginationConfig(max_pages=10)
    )

    csv_path = crawler.to_csv(staff)
    print(f"Exportado: {csv_path}")

asyncio.run(main())
```

#### 2. Paginacion JS-Based (Click en boton)
Para paginas que usan JavaScript para cargar contenido:

```python
pagination = PaginationConfig(
    next_button_selector="a.next-page, .pagination .next",
    max_pages=10,
    wait_timeout=5000  # ms
)
staff = await crawler.extract_with_pagination(url, pagination)
```

#### Selectores de Paginacion por Defecto

El crawler detecta automaticamente estos patrones:

**URL-Based:**
- `?page=N`, `?page_no=N`, `?p=N`, `?const_page=N`

**JS-Based (botones):**
- `[aria-label='Next Page']`, `li.next a`
- `a:has-text('Next')`, `a:has-text('Siguiente')`
- `a.next`, `.next a`, `[rel='next']`
- `a[aria-label*='next']`, `.pagination a:last-child`

## URLs Probadas

| URL | Tipo | Paginas | Staff | Emails | Estrategia |
|-----|------|---------|-------|--------|------------|
| generalstanford.nn.k12.va.us/faculty.html | Simple | 1 | 62 | 62 | Regex |
| aacps.org/o/marleyes/page/faculty-staff | Accordions | 1 | 78 | 78 | Regex |
| baltimorecityschools.org/o/ruhrah/staff | URL pagination | 8 | 157 | 140 | Hibrida |
| ovs.onslow.k12.nc.us/directory | URL pagination | 3 | 48 | 48 | LLM |

## Resultado Esperado

```
Extrayendo desde: https://example.com/staff
--------------------------------------------------
Pagina 1: Cargando https://example.com/staff
Detectada paginacion URL (3 paginas)
Extrayendo 3 paginas...
Tipo de contenido detectado: visible (16 emails)
Usando extraccion LLM...

Total: 48 miembros extraidos de 3 pagina(s)

Primeros 5:
  John Doe | Principal | john.doe@example.com
  Jane Smith | Teacher | jane.smith@example.com
  ...

Datos exportados a: results/staff_20241205_143022.csv
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
- [x] Extraccion con LLM (GPT-4o-mini)
- [x] Exportacion a CSV
- [x] Manejo de multiples URLs (extract_many)
- [x] Paginacion automatica URL-based
- [x] Paginacion automatica JS-based
- [x] Estrategia hibrida (LLM + Regex)
- [x] Auto-deteccion de tipo de contenido
- [x] Soporte para emails en aria-label
- [ ] Tests unitarios
- [ ] Manejo avanzado de errores
- [ ] Rate limiting configurable

## Dependencias

```
crawl4ai>=0.4.2
openai>=1.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

## API Reference

### StaffDirectoryCrawler

```python
class StaffDirectoryCrawler:
    def __init__(
        self,
        provider: str = "openai/gpt-4o-mini",
        api_token: Optional[str] = None,  # Default: OPENAI_API_KEY env
        headless: bool = True,
        verbose: bool = False
    )
```

#### Metodos

| Metodo | Descripcion |
|--------|-------------|
| `extract(url)` | Extrae staff de una URL |
| `extract_many(urls)` | Extrae staff de multiples URLs en paralelo |
| `extract_with_pagination(url, config)` | Extrae con paginacion automatica |
| `to_csv(staff, filename)` | Exporta a CSV |

### PaginationConfig

```python
@dataclass
class PaginationConfig:
    next_button_selector: str = "..."  # Selectores CSS para boton Next
    max_pages: int = 10                 # Limite de paginas
    wait_timeout: int = 5000            # Timeout en ms
    content_selector: str = "body"      # Selector para detectar cambio
```

### StaffMember

```python
class StaffMember(BaseModel):
    name: str                    # Nombre completo
    role: Optional[str] = None   # Cargo/posicion
    email: Optional[str] = None  # Email
```

---

*Proyecto en desarrollo activo*
