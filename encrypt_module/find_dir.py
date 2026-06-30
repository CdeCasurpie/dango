import os

def find_dir_path(dirname: str) -> list:
    """
    Busca directorios llamados <dirname> en las unidades raíz del sistema.
    Devuelve una lista de rutas absolutas a los directorios encontrados.
    """
    roots = ["C:\\", "D:\\"] if os.name == "nt" else ["/"]
    matches = []

    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            if os.path.basename(dirpath) == dirname:
                matches.append(os.path.abspath(dirpath))
    return matches


if __name__ == "__main__":
    print("Buscando directorios 'home_test' en las unidades raíz...")
    matches = find_dir_path("home_test")
    if matches:
        print("Directorios encontrados:")
        for match in matches:
            print(match)
    else:
        print("No se encontraron directorios 'home_test'.")