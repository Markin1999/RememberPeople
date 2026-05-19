#!/bin/bash
# Build script for RememberPeople macOS app
# Run this from the RememberPeople directory with the venv active

echo "=== RememberPeople — Build macOS .app ==="
echo ""

# Check venv is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Attenzione: il virtual environment non sembra attivo."
    echo "   Attivalo con: source ~/mypeople-env/bin/activate"
    echo ""
fi

echo "🔨 Avvio build con PyInstaller..."
echo ""

pyinstaller \
    --name "RememberPeople" \
    --windowed \
    --onedir \
    --clean \
    --noconfirm \
    --hidden-import "psycopg2" \
    --hidden-import "matplotlib.backends.backend_qtagg" \
    --hidden-import "PyQt6.QtPrintSupport" \
    --add-data "ui:ui" \
    --add-data "utils:utils" \
    main.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build completata con successo!"
    echo ""
    echo "📦 Trovi la tua app in:"
    echo "   dist/RememberPeople.app"
    echo ""
    echo "Per aprirla:"
    echo "   open dist/RememberPeople.app"
    echo ""
    echo "⚠️  IMPORTANTE: Prima di aprire l'app, assicurati che Docker sia in esecuzione"
    echo "   e il database sia attivo:"
    echo "   docker start mypeople-db"
else
    echo ""
    echo "❌ Build fallita. Controlla gli errori sopra."
fi
