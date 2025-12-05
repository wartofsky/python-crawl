import asyncio
from staff_crawler import StaffDirectoryCrawler, PaginationConfig


async def main():
    # URL del directorio de staff a extraer
    url = "https://sb.kcs.k12.nc.us/school-info/our-staff"

    print(f"Extrayendo informacion de staff desde: {url}")
    print("-" * 50)

    crawler = StaffDirectoryCrawler(verbose=True)

    try:
        # Extraccion con paginacion automatica
        # - Detecta paginacion URL-based (?page=N, ?const_page=N, etc.)
        # - Si no hay paginacion URL, intenta JS-based (click en Next)
        # - Detecta duplicados para evitar loops infinitos
        pagination = PaginationConfig(max_pages=10)
        staff = await crawler.extract_with_pagination(url, pagination)

        if not staff:
            print("No se encontraron miembros del staff.")
            return

        print(f"\nSe encontraron {len(staff)} miembros del staff.\n")

        # Guardar en CSV (carpeta results, nombre automatico con timestamp)
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
    asyncio.run(main())
