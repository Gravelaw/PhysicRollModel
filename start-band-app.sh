#!/bin/sh
# Start the band screening app (Linux). Run it from a terminal (./start-band-app.sh) or open it
# from the file manager with "Run in terminal". It runs, from this folder:
#   python -m physicroll.band_app --runs-dir band-app-runs
# and keeps the window open if something goes wrong.

case "$0" in
    */*) cd "${0%/*}" || exit 1 ;;
esac

pause_and_exit() {
    printf '\nPress Enter to close this window. '
    read -r _ || true
    exit "$1"
}

PY=""
FOUND=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        version=$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
                >/dev/null 2>&1; then
            PY="$candidate"
            break
        fi
        FOUND="$FOUND $candidate ($version)"
    fi
done

if [ -z "$PY" ]; then
    echo "Python 3.10 or newer was not found."
    if [ -n "$FOUND" ]; then
        echo "Found only:$FOUND"
    fi
    echo "Install Python 3.10 or newer (for example from python.org or your package manager),"
    echo "then start this file again."
    pause_and_exit 1
fi

echo "Starting the band screening app with $PY. Press Ctrl-C to stop it."
"$PY" -m physicroll.band_app --runs-dir band-app-runs
status=$?
if [ "$status" -ne 0 ] && [ "$status" -ne 130 ]; then
    echo
    echo "The band app stopped with an error (code $status). The message above says why."
    pause_and_exit "$status"
fi
exit 0
