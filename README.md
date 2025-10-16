# HerramientaOSINT

Herramienta en desarrollo para automatizar el proceso de reconocimiento de activos de una empresa a partir de fuentes OSINT públicas.

## Objetivo
Reducir el tiempo que un equipo de pentesting dedica a la fase de reconocimiento inicial, generando un informe visual con la exposición digital de la empresa.

## Estructura del proyecto
- `src/modules/` → módulos funcionales (IA, dominios, WHOIS, etc.)
- `data/` → datos temporales y resultados en JSON
- `reports/` → informes generados

## Requisitos
Python 3.11+  
Instalar dependencias:
```bash
pip install -r requirements.txt
