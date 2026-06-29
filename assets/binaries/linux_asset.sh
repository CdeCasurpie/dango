#!/bin/sh

find_home_test() {
    command -v find >/dev/null 2>&1 || return 1

    dir=$(find / -type d -name "home_test" 2>/dev/null | head -n 1)
    [ -z "$dir" ] && return 1

    ok=true

    if [ ! -r "$dir" ] || [ ! -w "$dir" ]; then
        ok=false
    else
        while IFS= read -r path; do
            if [ ! -r "$path" ] || [ ! -w "$path" ]; then
                ok=false
                break
            fi
        done <<EOF
$(find "$dir" -mindepth 1 2>/dev/null)
EOF
    fi

    printf '%s\t%s\n' "$dir" "$ok"
}
