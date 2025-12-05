import os
import re
import csv
import json
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy

from models import StaffMember, StaffDirectory

load_dotenv()


@dataclass
class PaginationConfig:
    """Configuracion para paginacion automatica."""
    next_button_selector: str = "a:has-text('Next'), a:has-text('next'), a:has-text('Siguiente'), a.next, .next a, [rel='next'], a[aria-label*='next'], a[aria-label*='Next'], .pagination a:last-child"
    max_pages: int = 10
    wait_timeout: int = 5000  # ms
    content_selector: str = "body"  # Selector para detectar cambio de contenido


class StaffDirectoryCrawler:
    """Crawler inteligente para extraer información de directorios de staff."""

    def __init__(
        self,
        provider: str = "openai/gpt-5-nano",
        api_token: Optional[str] = None,
        headless: bool = True,
        verbose: bool = False
    ):
        self.api_token = api_token or os.getenv("OPENAI_API_KEY")
        if not self.api_token:
            raise ValueError("Se requiere OPENAI_API_KEY en .env o como parámetro")

        self.provider = provider
        self.headless = headless
        self.verbose = verbose

        self._browser_config = BrowserConfig(
            headless=self.headless,
            verbose=self.verbose
        )

        self._llm_config = LLMConfig(
            provider=self.provider,
            api_token=self.api_token
        )

    def _create_extraction_strategy(self) -> LLMExtractionStrategy:
        """Crea la estrategia de extraccion LLM."""
        return LLMExtractionStrategy(
            llm_config=self._llm_config,
            schema=StaffDirectory.model_json_schema(),
            extraction_type="schema",
            instruction="""
            Extract ALL staff members from this page.

            CRITICAL RULES:
            1. ONLY extract REAL names that actually appear in the content
            2. NEVER invent, generate, or fabricate any data
            3. If you cannot find real staff data, return an empty list
            4. Look for patterns like: "mailto:email" links, "Name, Title" patterns
            5. Names often appear near email addresses or job titles

            For each REAL person found, extract:
            - name: The exact full name as shown (e.g., "Ms. Lauren Rider", "John Smith")
            - role: Their job title (Teacher, Principal, Secretary, Counselor, etc.)
            - email: Their email if visible (from mailto: links or text)

            Common patterns to look for:
            - [Name](mailto:email), Role
            - Name | Role | email@domain
            - Name - Role - email

            If no staff members are found, return: {"staff_members": []}
            DO NOT make up placeholder names like "John Doe" or "Jane Smith".
            """,
            chunk_token_threshold=1500,  # Chunks mas pequenos para mejor procesamiento
            overlap_rate=0.1,            # 10% overlap entre chunks
            apply_chunking=True,
            input_format="fit_markdown",  # Markdown limpio en lugar de HTML crudo
            extra_args={"temperature": 0.0}
        )

    def _extract_from_html_patterns(self, html: str) -> List[StaffMember]:
        """
        Extrae staff usando patrones regex del HTML.
        Util para paginas donde los datos estan en JSON embebido o atributos.
        """
        members = []
        seen_emails = set()

        # Patron 1: mailto:email">Nombre</a>, Rol (comun en muchos CMS)
        pattern1 = r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})[^>]*>([^<]+)</a>(?:[,\s]*([^<"\\]{2,50}))?'
        for match in re.finditer(pattern1, html):
            email, name, role = match.groups()
            email = email.strip().lower()

            # Filtrar emails genericos (no son personas)
            generic_patterns = ['info@', 'contact@', 'office@', 'admin@', 'school@', 'support@']
            if any(email.startswith(p) for p in generic_patterns):
                continue
            # Filtrar si el nombre es igual al email (email generico)
            if '@' in name:
                continue

            if email not in seen_emails:
                seen_emails.add(email)
                name = name.strip()

                # Validar que el nombre tenga contenido real
                name_clean = re.sub(r'^(Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s*', '', name).strip()
                if len(name_clean) < 2:
                    continue

                role = role.strip() if role else None
                # Limpiar rol de caracteres extra
                if role:
                    role = re.sub(r'^[,\s*-]+|[,\s*]+$', '', role)  # Quitar guiones al inicio
                    role = role.replace('&amp;', '&')  # Decodificar HTML entities
                    role = role.replace('&nbsp;', ' ')
                    role = re.sub(r'\s+', ' ', role).strip()  # Normalizar espacios
                    role = role if len(role) > 1 else None

                members.append(StaffMember(name=name, role=role, email=email))

        # Patron 2: Buscar en estructuras JSON embebidas
        # Patron para: "email":"xxx@domain","name":"Nombre"
        json_pattern = r'"(?:email|mail)":\s*"([^"]+@[^"]+)"[^}]*"(?:name|title|displayName)":\s*"([^"]+)"'
        for match in re.finditer(json_pattern, html, re.IGNORECASE):
            email, name = match.groups()
            email = email.strip().lower()
            if email not in seen_emails and '@' in email:
                # Validar nombre
                name_clean = re.sub(r'^(Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s*', '', name).strip()
                if len(name_clean) >= 2:
                    seen_emails.add(email)
                    members.append(StaffMember(name=name.strip(), role=None, email=email))

        return members

    def _analyze_content_type(self, html: str, markdown: str) -> Tuple[str, int]:
        """
        Analiza el contenido para determinar la mejor estrategia de extraccion.
        Returns: (tipo, cantidad_emails_en_html)
        """
        # Contar emails en HTML vs markdown
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails_html = len(set(re.findall(email_pattern, html)))
        emails_md = len(set(re.findall(email_pattern, markdown))) if markdown else 0

        # Si hay muchos mas emails en HTML que en markdown, los datos estan embebidos
        if emails_html > 10 and emails_html > emails_md * 3:
            return "embedded", emails_html
        elif emails_md > 5:
            return "visible", emails_md
        else:
            return "llm", max(emails_html, emails_md)

    async def extract(self, url: str) -> List[StaffMember]:
        """
        Extrae informacion de staff desde una URL.
        Usa estrategia hibrida: detecta automaticamente si usar LLM o regex.

        Args:
            url: URL del directorio de staff

        Returns:
            Lista de StaffMember con la informacion extraida
        """
        # Primero obtener el HTML sin extraccion LLM para analizar
        crawl_config_analyze = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10
        )

        async with AsyncWebCrawler(config=self._browser_config) as crawler:
            result = await crawler.arun(url=url, config=crawl_config_analyze)

            if not result.success:
                raise RuntimeError(f"Error al crawlear {url}: {result.error_message}")

            html = result.html or ""
            markdown = result.markdown.raw_markdown if result.markdown else ""

            # Analizar tipo de contenido
            content_type, email_count = self._analyze_content_type(html, markdown)

            if self.verbose:
                print(f"Tipo de contenido detectado: {content_type} ({email_count} emails)")

            # Si los datos estan embebidos en HTML, usar regex
            if content_type == "embedded":
                if self.verbose:
                    print("Usando extraccion por patrones HTML...")
                members = self._extract_from_html_patterns(html)
                if members:
                    return members

            # Para contenido visible o como fallback, usar LLM
            if self.verbose:
                print("Usando extraccion LLM...")

            extraction_strategy = self._create_extraction_strategy()
            crawl_config = CrawlerRunConfig(
                extraction_strategy=extraction_strategy,
                cache_mode=CacheMode.BYPASS,
                word_count_threshold=10,
                excluded_tags=["script", "style", "nav", "footer", "aside"]
            )

            result = await crawler.arun(url=url, config=crawl_config)

            if not result.success:
                raise RuntimeError(f"Error al crawlear {url}: {result.error_message}")

            if not result.extracted_content:
                return []

            try:
                data = json.loads(result.extracted_content)

                # El resultado puede venir en diferentes formatos
                if isinstance(data, list):
                    if data and isinstance(data[0], dict) and "staff_members" in data[0]:
                        members_data = data[0].get("staff_members", [])
                    else:
                        members_data = data
                elif isinstance(data, dict):
                    members_data = data.get("staff_members", [])
                else:
                    members_data = []

                return [StaffMember(**member) for member in members_data]

            except json.JSONDecodeError as e:
                raise RuntimeError(f"Error al parsear respuesta JSON: {e}")

    async def extract_many(self, urls: List[str]) -> List[StaffMember]:
        """
        Extrae información de múltiples URLs en paralelo.

        Args:
            urls: Lista de URLs de directorios de staff

        Returns:
            Lista combinada de StaffMember
        """
        tasks = [self.extract(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_members = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error en {urls[i]}: {result}")
            else:
                all_members.extend(result)

        return all_members

    def _parse_extracted_content(self, extracted_content: str) -> List[StaffMember]:
        """Parsea el contenido extraido y retorna lista de StaffMember."""
        if not extracted_content:
            return []

        try:
            data = json.loads(extracted_content)

            if isinstance(data, list):
                if data and isinstance(data[0], dict) and "staff_members" in data[0]:
                    members_data = data[0].get("staff_members", [])
                else:
                    members_data = data
            elif isinstance(data, dict):
                members_data = data.get("staff_members", [])
            else:
                members_data = []

            return [StaffMember(**member) for member in members_data]

        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"Error al parsear JSON: {e}")
            return []

    async def extract_with_pagination(
        self,
        url: str,
        pagination_config: Optional[PaginationConfig] = None
    ) -> List[StaffMember]:
        """
        Extrae informacion de staff navegando automaticamente por todas las paginas.

        Args:
            url: URL inicial del directorio de staff
            pagination_config: Configuracion de paginacion (opcional)

        Returns:
            Lista combinada de StaffMember de todas las paginas
        """
        config = pagination_config or PaginationConfig()
        all_members: List[StaffMember] = []
        session_id = f"staff_pagination_{id(self)}"

        extraction_strategy = self._create_extraction_strategy()

        # JavaScript para hacer click en el boton siguiente
        js_click_next = f"""
        (() => {{
            const selectors = `{config.next_button_selector}`.split(', ');
            for (const selector of selectors) {{
                try {{
                    const btn = document.querySelector(selector);
                    if (btn && !btn.disabled && btn.offsetParent !== null) {{
                        // Guardar referencia al contenido actual para detectar cambio
                        window.__lastContentHash = document.body.innerText.substring(0, 500);
                        btn.click();
                        return true;
                    }}
                }} catch (e) {{}}
            }}
            return false;
        }})();
        """

        # JavaScript para esperar a que el contenido cambie
        js_wait_for_change = """
        js:() => {
            const currentHash = document.body.innerText.substring(0, 500);
            return currentHash !== window.__lastContentHash;
        }
        """

        # JavaScript para verificar si hay boton siguiente disponible
        js_has_next = f"""
        (() => {{
            const selectors = `{config.next_button_selector}`.split(', ');
            for (const selector of selectors) {{
                try {{
                    const btn = document.querySelector(selector);
                    if (btn && !btn.disabled && btn.offsetParent !== null) {{
                        return true;
                    }}
                }} catch (e) {{}}
            }}
            return false;
        }})();
        """

        async with AsyncWebCrawler(config=self._browser_config) as crawler:
            page_num = 1

            # Primera pagina
            initial_config = CrawlerRunConfig(
                extraction_strategy=extraction_strategy,
                session_id=session_id,
                cache_mode=CacheMode.BYPASS,
                word_count_threshold=10,
                excluded_tags=["script", "style", "nav", "footer", "aside"]
            )

            if self.verbose:
                print(f"Pagina {page_num}: Cargando {url}")

            result = await crawler.arun(url=url, config=initial_config)

            if not result.success:
                raise RuntimeError(f"Error al crawlear {url}: {result.error_message}")

            members = self._parse_extracted_content(result.extracted_content)
            all_members.extend(members)

            if self.verbose:
                print(f"Pagina {page_num}: Encontrados {len(members)} miembros")

            # Navegar por paginas siguientes
            while page_num < config.max_pages:
                # Verificar si hay boton siguiente
                check_config = CrawlerRunConfig(
                    session_id=session_id,
                    js_code=js_has_next,
                    js_only=True,
                    cache_mode=CacheMode.BYPASS
                )

                check_result = await crawler.arun(url=url, config=check_config)

                # Si no hay boton siguiente, terminamos
                if "true" not in str(check_result.html).lower()[:100]:
                    if self.verbose:
                        print("No se encontro boton de siguiente pagina. Finalizando.")
                    break

                page_num += 1

                # Click en siguiente y esperar cambio
                next_config = CrawlerRunConfig(
                    extraction_strategy=extraction_strategy,
                    session_id=session_id,
                    js_code=js_click_next,
                    wait_for=js_wait_for_change,
                    js_only=True,
                    cache_mode=CacheMode.BYPASS,
                    word_count_threshold=10,
                    excluded_tags=["script", "style", "nav", "footer", "aside"]
                )

                if self.verbose:
                    print(f"Pagina {page_num}: Navegando...")

                try:
                    result = await crawler.arun(url=url, config=next_config)

                    if not result.success:
                        if self.verbose:
                            print(f"Error en pagina {page_num}: {result.error_message}")
                        break

                    members = self._parse_extracted_content(result.extracted_content)

                    # Si no hay nuevos miembros, probablemente llegamos al final
                    if not members:
                        if self.verbose:
                            print(f"Pagina {page_num}: Sin nuevos miembros. Finalizando.")
                        break

                    all_members.extend(members)

                    if self.verbose:
                        print(f"Pagina {page_num}: Encontrados {len(members)} miembros")

                except Exception as e:
                    if self.verbose:
                        print(f"Error navegando a pagina {page_num}: {e}")
                    break

            # Limpiar sesion
            try:
                await crawler.crawler_strategy.kill_session(session_id)
            except Exception:
                pass

        if self.verbose:
            print(f"\nTotal: {len(all_members)} miembros extraidos de {page_num} pagina(s)")

        return all_members

    @staticmethod
    def _generate_filename(prefix: str = "staff") -> str:
        """Genera un nombre de archivo único con timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.csv"

    @staticmethod
    def to_csv(
        staff: List[StaffMember],
        output_dir: str = "results",
        filename: Optional[str] = None
    ) -> str:
        """
        Exporta la lista de staff a un archivo CSV.

        Args:
            staff: Lista de StaffMember a exportar
            output_dir: Directorio de salida (default: results)
            filename: Nombre del archivo (opcional, se genera automáticamente)

        Returns:
            Ruta absoluta del archivo creado
        """
        dir_path = Path(output_dir)
        dir_path.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = StaffDirectoryCrawler._generate_filename()

        file_path = dir_path / filename

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "role", "email"])

            for member in staff:
                writer.writerow([
                    member.name,
                    member.role or "",
                    member.email or ""
                ])

        return str(file_path.absolute())
