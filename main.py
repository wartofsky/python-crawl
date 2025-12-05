import asyncio
from staff_crawler import StaffDirectoryCrawler, PaginationConfig


async def main():
    # URL del directorio de staff a extraer
    url = "https://generalstanford.nn.k12.va.us/faculty.html"

    print(f"Extrayendo informacion de staff desde: {url}")
    print("-" * 50)

    crawler = StaffDirectoryCrawler(verbose=True)

    try:
        # Extraccion simple (una sola pagina)
        staff = await crawler.extract(url)

        if not staff:
            print("No se encontraron miembros del staff.")
            return

        print(f"\nSe encontraron {len(staff)} miembros del staff.\n")

        # Guardar en CSV (carpeta results, nombre automatico con timestamp)
        csv_path = crawler.to_csv(staff)
        print(f"Datos exportados a: {csv_path}")

        # Mostrar preview
        print("\nPreview (primeros 5):")
        print("-" * 50)
        for member in staff[:5]:
            print(f"  {member.name} | {member.role or 'N/A'} | {member.email or 'N/A'}")
        if len(staff) > 5:
            print(f"  ... y {len(staff) - 5} mas")

    except Exception as e:
        print(f"Error: {e}")


async def main_with_pagination():
    """Ejemplo de extraccion con paginacion automatica."""
    # URL de un directorio con multiples paginas
    url = "https://example.com/staff-directory"

    print(f"Extrayendo staff con paginacion desde: {url}")
    print("-" * 50)

    crawler = StaffDirectoryCrawler(verbose=True)

    # Configuracion de paginacion personalizada (opcional)
    pagination = PaginationConfig(
        # Selectores CSS para el boton "siguiente"
        next_button_selector="a:has-text('Next'), .pagination .next, [rel='next']",
        max_pages=5,  # Maximo de paginas a recorrer
        wait_timeout=5000  # Tiempo de espera en ms
    )

    try:
        # Extraccion con paginacion automatica
        staff = await crawler.extract_with_pagination(url, pagination)

        if not staff:
            print("No se encontraron miembros del staff.")
            return

        print(f"\nTotal: {len(staff)} miembros del staff.\n")

        # Guardar en CSV
        csv_path = crawler.to_csv(staff)
        print(f"Datos exportados a: {csv_path}")

        # Mostrar preview
        print("\nPreview (primeros 10):")
        print("-" * 50)
        for member in staff[:10]:
            print(f"  {member.name} | {member.role or 'N/A'} | {member.email or 'N/A'}")
        if len(staff) > 10:
            print(f"  ... y {len(staff) - 10} mas")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Ejecutar extraccion simple
    asyncio.run(main())

    # Para usar paginacion, descomentar:
    # asyncio.run(main_with_pagination())
