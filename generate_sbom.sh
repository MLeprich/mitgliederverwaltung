#!/bin/bash

# SBOM Generation Script für Django Mitgliederverwaltung
# Erstellt verschiedene SBOM-Formate für das Projekt

echo "🔍 Generiere SBOM für Django Mitgliederverwaltung..."

# Erstelle SBOM-Verzeichnis
mkdir -p sbom

# 1. CycloneDX mit Python-spezifischem Tool
echo "📋 Generiere CycloneDX SBOM..."
if command -v cyclonedx-py &> /dev/null; then
    cyclonedx-py -o sbom/sbom-cyclonedx.json
    echo "✅ CycloneDX SBOM erstellt: sbom/sbom-cyclonedx.json"
else
    echo "⚠️  cyclonedx-py nicht installiert. Installiere mit: pip install cyclonedx-bom"
fi

# 2. Syft für umfassende Analyse
echo "🔍 Generiere Syft SBOM..."
if command -v syft &> /dev/null; then
    # SPDX Format
    syft packages dir:. -o spdx-json=sbom/sbom-spdx.json
    # CycloneDX Format
    syft packages dir:. -o cyclonedx-json=sbom/sbom-syft-cyclonedx.json
    # Human-readable Format
    syft packages dir:. -o table=sbom/sbom-human-readable.txt
    echo "✅ Syft SBOMs erstellt"
else
    echo "⚠️  Syft nicht installiert. Installiere von: https://github.com/anchore/syft"
fi

# 3. pip-audit für Vulnerability-Analyse
echo "🛡️  Führe Vulnerability-Scan durch..."
if command -v pip-audit &> /dev/null; then
    pip-audit --format=cyclonedx --output=sbom/vulnerability-report.json
    pip-audit --format=json --output=sbom/vulnerability-report-detailed.json
    echo "✅ Vulnerability-Reports erstellt"
else
    echo "⚠️  pip-audit nicht installiert. Installiere mit: pip install pip-audit"
fi

# 4. requirements.txt basierte SBOM (Fallback)
echo "📄 Erstelle einfache Abhängigkeitsliste..."
if [ -f "requirements.txt" ]; then
    pip freeze > sbom/installed-packages.txt
    echo "✅ Package-Liste erstellt: sbom/installed-packages.txt"
fi

# 5. Projekt-Metadaten sammeln
echo "📊 Sammle Projekt-Metadaten..."
cat > sbom/project-metadata.json << EOF
{
  "project": {
    "name": "Django Mitgliederverwaltung",
    "version": "1.0.0",
    "description": "Mitgliederverwaltungssystem für Vereine",
    "repository": "$(git config --get remote.origin.url 2>/dev/null || echo 'N/A')",
    "branch": "$(git branch --show-current 2>/dev/null || echo 'N/A')",
    "commit": "$(git rev-parse HEAD 2>/dev/null || echo 'N/A')",
    "generated": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)",
    "generator": "manual-sbom-script",
    "python_version": "$(python --version 2>&1)",
    "django_version": "$(python -c 'import django; print(django.get_version())' 2>/dev/null || echo 'N/A')"
  }
}
EOF

echo "✅ Projekt-Metadaten erstellt: sbom/project-metadata.json"

echo ""
echo "🎉 SBOM-Generierung abgeschlossen!"
echo "📁 Alle Dateien befinden sich im 'sbom/' Verzeichnis:"
ls -la sbom/ 2>/dev/null || echo "Keine SBOM-Dateien erstellt"

echo ""
echo "💡 Nächste Schritte:"
echo "   1. Prüfe die generierten SBOM-Dateien"
echo "   2. Lade sie in dein Repository hoch"
echo "   3. Konfiguriere die GitHub Action für automatische Updates"
echo "   4. Teile die SBOM mit Stakeholdern"

