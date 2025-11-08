# HerramientaOSINT

**HerramientaOSINT** es una aplicación desarrollada para **automatizar el proceso de reconocimiento de activos digitales** de una empresa a partir de fuentes **OSINT** (*Open Source Intelligence*).  
Su objetivo es reducir el tiempo que los equipos de **pentesting o inteligencia** dedican a la fase de reconocimiento inicial, generando una visión completa de la **exposición digital de la organización**.

## Objetivo
La herramienta permite:
- Identificar **dominios, subdominios, IPs y sistemas autónomos** relacionados con una empresa.
- Enriquecer los resultados con información WHOIS, ASN y redes asociadas.
- **Correlacionar y visualizar** la huella digital completa de una organización.
- Exportar la información en un **informe visual automatizado**.

## Funcionalidades principales

- Descubrimiento automático de **dominios y subdominios** (WhoisXMLAPI, crt.sh, etc.)
- Obtención y normalización de información **WHOIS e IP**
- Identificación de **sistemas autónomos (ASN)** y sus redes
- **Categorización automática** de subdominios según su propósito
- Almacenamiento estructurado en **MongoDB**
- Generación de **informes visuales PDF** con los resultados

## Estructura del proyecto
- `src/modules/` → módulos funcionales (IA, dominios, WHOIS, etc.)
- `src/main.py` → archivo desde el que se ejecuta la herramienta
- `reports/` → informes generados
- `requirements.txt` → dependencias del proyecto


## Requisitos
- **Python 3.11+**
- **MongoDB**
- Claves API para:
  - [WhoisXMLAPI](https://whoisxmlapi.com/)
  - [Google AI Studio](https://aistudio.google.com/)

Instalación:
```bash
pip install -r requirements.txt