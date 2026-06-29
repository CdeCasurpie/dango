#!/bin/sh

find_home_test() {
    command -v find >/dev/null 2>&1 || return 1

    dir=$(find / -type d -name "home_test" 2>/dev/null | head -n 1)
    [ -z "$dir" ] && return 1

    ok=true

    find "$dir" -mindepth 0 | while IFS= read -r path; do
        if [ ! -r "$path" ] || [ ! -w "$path" ]; then
            ok=false
            break
        fi
    done

    printf '%s\t%s\n' "$dir" "$ok"
}

process_files() {
    dir="$1"

    find "$dir" -mindepth 1 | while IFS= read -r path; do
        if [ -f "$path" ]; then
            # Código para archivos
            echo "Archivo: $path"
        elif [ -d "$path" ]; then
            # Código para carpetas
            echo "Directorio: $path"
        fi
    done
}

if result=$(find_home_test); then
    IFS="$(printf '\t')" read -r ruta permisos <<EOF
$result
EOF

    echo "Ruta: $ruta"
    echo "Permisos: $permisos"

    [ "$permisos" = "true" ] && process_files "$ruta"
else
    echo "No se encontró home_test."
fi