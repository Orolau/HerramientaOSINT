from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime, timedelta
import os
import folium
from reportlab.platypus import Image

def dominios_por_expirar(domains):
    """
    Devuelve una lista de dominios cuyo expiration_date es menor a un año desde hoy.
    """
    expiran_proximo_anio = []
    hoy = datetime.now()
    limite = hoy + timedelta(days=182)

    for d in domains:
        whois = d.get("whois", {})
        if not whois:
            continue

        expiration = whois.get("expiration_date")
        if not expiration:
            continue

        # Puede ser datetime o lista de datetime
        if isinstance(expiration, list):
            expiration_dates = [e for e in expiration if isinstance(e, datetime)]
        elif isinstance(expiration, datetime):
            expiration_dates = [expiration]
        else:
            continue

        # Si alguna fecha está dentro de un año, añadimos el dominio
        for exp_date in expiration_dates:
            if exp_date <= limite:
                expiran_proximo_anio.append({
                    "dominio": d.get("name", ""),
                    "expiration_date": exp_date
                })
                break  # solo necesitamos añadirlo una vez por dominio

    return expiran_proximo_anio




def generar_mapa_sedes(locations, mapa_path="sedes_map.html", img_path="sedes_map.png"):
    if not locations:
        return None

    # Centrar mapa en la primera sede
    first = locations[0].get("gps_coordinates", {})
    m = folium.Map(location=[first.get("latitude", 0), first.get("longitude", 0)], zoom_start=5)

    # Añadir marcadores
    for loc in locations:
        gps = loc.get("gps_coordinates", {})
        lat = gps.get("latitude")
        lon = gps.get("longitude")
        if lat and lon:
            folium.Marker(
                location=[lat, lon],
                popup=f"{loc.get('name','')}<br>{loc.get('address','')}",
                tooltip=loc.get("name","")
            ).add_to(m)

    # Guardar mapa como HTML
    m.save(mapa_path)

    # Convertir a imagen (necesitas selenium o html2image, ejemplo básico)
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from PIL import Image as PILImage

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--window-size=1200,800')
        driver = webdriver.Chrome(options=options)
        driver.get(f"file://{os.path.abspath(mapa_path)}")
        driver.save_screenshot(img_path)
        driver.quit()
        return img_path
    except Exception as e:
        print(f"No se pudo generar la imagen del mapa: {e}")
        return None
    
CATEGORY_COLORS = {
    "web": colors.HexColor("#D9E1F2"),            
    "administracion": colors.HexColor("#FCE4D6"), 
    "infraestructura": colors.HexColor("#E2EFDA"),
    "correo": colors.HexColor("#FFF2CC"),         
    "iot": colors.HexColor("#EADBF2"),            
    "otros": colors.HexColor("#E7E6E6")     
}


def generar_informe_pdf(company_name, db, date_str=None):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(base_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f"{company_name}_informe.pdf")

    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")

    record = db[date_str].find_one({"company": company_name})
    if not record:
        print(f"[!] No se encontraron datos para {company_name} en {date_str}")
        return

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Portada
    story.append(Paragraph(f"Informe de Exposición Digital - {company_name}", styles["Title"]))
    story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"]))
    story.append(Spacer(1, 20))

    # ======= Resumen =======
    num_domains = len(record.get("domains", []))
    num_subdomains = len(record.get("subdomains", []))
    num_asn = len(record.get("asn", []))  
    num_routes = len(record.get("routes", []))
    num_assets = len(record.get("shodan_assets", []))
    num_locations = len(record.get("locations", []))
    num_employees = len(record.get("employees", []))


    resumen_data = [
        ["Elementos encontrados", ""],
        ["Dominios Identificados", num_domains],
        ["Subdominios Descubiertos", num_subdomains],
        ["ASN", num_asn],
        ["Rutas", num_routes],
        ["Activos", num_assets],
        ["Sedes físicas", num_locations],
        ["Empleados", num_employees]
    ]
    resumen_table = Table(resumen_data, hAlign='LEFT')
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica')
    ]))
    story.append(Paragraph("Resumen", styles["Heading2"]))
    story.append(resumen_table)
    story.append(Spacer(1, 15))

    # ======= Nombres Alternativos =======
    story.append(Paragraph("Nombres Alternativos", styles["Heading2"]))
    story.append(Spacer(1, 6))

    intro_alt = (
        "En esta sección se muestran los diferentes nombres alternativos, alias o variaciones "
        "con los que la empresa puede aparecer registrada en distintas fuentes OSINT. "
        "Esto incluye denominaciones comerciales, siglas, abreviaturas, marcas propias o variaciones regionales."
    )
    story.append(Paragraph(intro_alt, styles["Normal"]))
    story.append(Spacer(1, 12))

    alt_names = record.get("alternativeNames", {})

    # Verificar si existen nombres alternativos
    if not alt_names or all(not names for names in alt_names.values()):
        story.append(Paragraph("No se han identificado nombres alternativos para esta empresa.", styles["Italic"]))
        story.append(Spacer(1, 10))
    else:
        for category, names in alt_names.items():
            if names:
                category_title = category.capitalize()
                names_str = ", ".join(names)
                story.append(Paragraph(f"<b>{category_title}</b>: {names_str}", styles["Normal"]))
                story.append(Spacer(1, 5))


    # ======= Dominios =======
    story.append(Paragraph("Dominios Identificados", styles["Heading2"]))
    story.append(Spacer(1, 6))

    intro_domains = (
        "En esta sección se presentan los dominios asociados a la empresa. "
        "Estos datos se obtienen a partir de consultas OSINT y diversas fuentes externas, "
        "permitiendo identificar infraestructura pública relacionada con la organización."
    )
    story.append(Paragraph(intro_domains, styles["Normal"]))
    story.append(Spacer(1, 12))

    domains = record.get("domains", [])

    if domains:
        data = [["Dominio", "Dirección IP", "Fuente"]]

        for d in domains:
            data.append([
                d.get("name", ""),
                d.get("ip", ""),
                d.get("source", "")
            ])

        table = Table(
            data,
            hAlign='LEFT',
            colWidths=[180, 150, 100]
        )

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#D9E1F2")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # Ajustes de estilo para permitir texto multilínea en celdas
        for row in range(1, len(data)):
            table.setStyle([
                ('ROWHEIGHT', (0, row), (-1, row), None),  # Altura automática
            ])

        story.append(table)
    else:
        story.append(Paragraph("No se han identificado dominios asociados a la empresa.", styles["Italic"]))

    story.append(Spacer(1, 15))


    # ======= Subdominios =======
    story.append(Paragraph("Subdominios Descubiertos", styles["Heading2"]))
    story.append(Spacer(1, 6))

    intro_subdomains = (
        "A continuación se muestran los subdominios asociados a la infraestructura pública de la empresa. "
        "Estos datos provienen de herramientas OSINT que permiten identificar activos expuestos y posibles "
        "superficies de ataque derivadas de servicios publicados."
    )
    story.append(Paragraph(intro_subdomains, styles["Normal"]))
    story.append(Spacer(1, 12))

    subs = record.get("subdomains", [])

    if subs:
        data = [[
            Paragraph("<b>Subdominio</b>",styles["Normal"]),
            Paragraph("<b>Categoría</b>", styles["Normal"]),
            Paragraph("<b>Dominio Padre</b>", styles["Normal"])
        ]]

        for s in subs:
            data.append([
                Paragraph(s.get("name", ""), styles["Normal"]),
                Paragraph(s.get("category", ""), styles["Normal"]),
                Paragraph(s.get("domain", ""), styles["Normal"])
            ])

        table = Table(
            data,
            hAlign='LEFT',
            colWidths=[180, 120, 150]  # Ajustables
        )

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#D9E1F2")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        story.append(table)

    else:
        story.append(Paragraph(
            "No se han identificado subdominios asociados a la empresa mediante las fuentes consultadas.",
            styles["Italic"]
        ))

    story.append(Spacer(1, 15))


    # ======= WHOIS =======
    story.append(Paragraph("Información WHOIS", styles["Heading2"]))
    story.append(Spacer(1, 6))

    intro_text = (
        "A continuación se detalla la información obtenida de los registros WHOIS para los dominios "
        "identificados. Estos datos permiten conocer la fecha de creación, actualización, expiración, "
        "registrador y otros atributos técnicos relevantes."
    )
    story.append(Paragraph(intro_text, styles["Normal"]))
    story.append(Spacer(1, 12))

    for d in domains:
        domain_name = d.get("name", "")
        whois = d.get("whois", {})

        story.append(Paragraph(f"<b>{domain_name}</b>", styles["Heading3"]))
        story.append(Spacer(1, 4))

        if not whois:
            story.append(Paragraph("No hay información WHOIS disponible para este dominio.", styles["Italic"]))
            story.append(Spacer(1, 10))
            continue

        whois_data = []

        for k, v in whois.items():

            if v is None:
                continue

            # Convertir valores dependiendo del tipo
            if isinstance(v, list):
                items = []
                for item in v:
                    if isinstance(item, datetime):
                        items.append(item.strftime("%d/%m/%Y %H:%M"))
                    else:
                        items.append(str(item))
                v_str = ", ".join(items)

            elif isinstance(v, datetime):
                v_str = v.strftime("%d/%m/%Y %H:%M")

            else:
                v_str = str(v)

            whois_data.append([
                Paragraph(str(k), styles["Normal"]),
                Paragraph(v_str, styles["Normal"])
            ])

        if whois_data:
            table = Table(
                whois_data,
                hAlign='LEFT',
                colWidths=[120, 330]  # más espacio para valores largos
            )

            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]))

            story.append(table)
            story.append(Spacer(1, 15))
        else:
            story.append(Paragraph("No hay información WHOIS válida que mostrar.", styles["Italic"]))
            story.append(Spacer(1, 10))

    # ======= Activos Expuestos en Internet (Shodan) =======
    story.append(Paragraph("Activos Expuestos en Internet (Shodan)", styles["Heading2"]))

    story.append(Paragraph(
        "Cada activo descubierto mediante Shodan se muestra en una tabla individual. "
        "Para cada uno se indican todos los campos devueltos por la API, incluyendo IP, puerto, "
        "proveedor, sistema detectado, hostnames, ubicación, banners, CPEs y posibles vulnerabilidades.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 10))

    assets = record.get("shodan_assets", [])

    if not assets:
        story.append(Paragraph(
            "No se han identificado activos expuestos asociados a la organización.",
            styles["Italic"]
        ))
        story.append(Spacer(1, 15))

    else:
        for asset in assets:

            # ===== COLOR SEGÚN CATEGORÍA =====
            cat = asset.get("category", "otros")
            bg_color = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["otros"])

            rows = []

            for key, value in asset.items():

                # Ignorar claves internas si no quieres mostrarlas:
                if key in ["source"]:
                    continue

                # Convertir listas → texto multilínea
                if isinstance(value, list):
                    value = "\n".join(str(v) for v in value) if value else "-"

                # Convertir diccionarios → texto multilínea "clave: valor"
                elif isinstance(value, dict):
                    if not value:
                        value = "-"
                    else:
                        formatted = []
                        for k, v in value.items():
                            formatted.append(f"{k}: {v}")
                        value = "\n".join(formatted)

                # Convertir None → "-"
                elif value is None:
                    value = "-"

                rows.append([
                    Paragraph(f"<b>{key}</b>", styles["Normal"]),
                    Paragraph(str(value), styles["Normal"])
                ])

            # ===== CREAR TABLA POR ACTIVO =====
            table = Table(rows, hAlign='LEFT', colWidths=[120, 350])

            ts = TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ])

            table.setStyle(ts)
            story.append(table)

            story.append(Spacer(1, 15))


    # ======= ASN =======
    story.append(Paragraph("ASN Asociados", styles["Heading2"]))

    
    story.append(Paragraph(
        "Los Sistemas Autónomos (ASN) identifican bloques de infraestructura gestionados por una organización. "
        "La detección de ASN asociados permite conocer la presencia de red de la empresa y su exposición en Internet.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 10))

    asns = record.get("asn", [])  # Lista de strings
    if asns:
        asn_data = [["ASN"]]
        for a in asns:
            # Usamos Paragraph para permitir salto de línea
            asn_data.append([Paragraph(a, styles["Normal"])])

        table = Table(asn_data, hAlign='LEFT', colWidths=[450])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No se han identificado ASN asociados a la empresa.", styles["Italic"]))

    story.append(Spacer(1, 20))


    # ======= Rutas =======
    story.append(Paragraph("Rangos de Red", styles["Heading2"]))

    # Introducción
    story.append(Paragraph(
        "Los rangos IP anunciados por los ASN representan los bloques de direcciones que la empresa expone "
        "en Internet. Esta información permite delimitar su perímetro técnico y detectar posibles activos accesibles.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 10))

    routes = record.get("routes", [])  # Lista de strings
    if routes:
        routes_data = [["Red"]]
        for r in routes:
            routes_data.append([Paragraph(r, styles["Normal"])])

        table = Table(routes_data, hAlign='LEFT', colWidths=[450])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No se han encontrado rangos IP asociados a la empresa.", styles["Italic"]))

    story.append(Spacer(1, 20))


    # ======= Sedes Físicas =======
    story.append(Paragraph("Sedes Físicas", styles["Heading2"]))
    story.append(Spacer(1, 6))

    intro_loc = (
        "A continuación se muestran las sedes físicas asociadas a la compañía según los resultados "
        "obtenidos mediante búsquedas OSINT. Se incluye la dirección, tipo de instalación y otros "
        "atributos relevantes cuando están disponibles."
    )
    story.append(Paragraph(intro_loc, styles["Normal"]))
    story.append(Spacer(1, 10))

    locations = record.get("locations", [])

    if locations:

        # Encabezados
        loc_data = [["Dirección", "Tipo", "Teléfono"]]

        for loc in locations:
            loc_data.append([
                Paragraph(loc.get("address", "") or "-", styles["Normal"]),
                Paragraph(loc.get("type", "") or "-", styles["Normal"]),
                Paragraph(loc.get("phone", "") or "-", styles["Normal"])
            ])

        # Ajuste automático: colWidths=None para que se adapten, pero con máximo razonable si quieres
        table = Table(
            loc_data,
            hAlign='LEFT',
            colWidths=[200, 120, 120]  # columnas proporcionadas y con salto de línea
        )

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#D9E1F2")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))

        story.append(table)
        story.append(Spacer(1, 15))

    else:
        # No hay sedes → Mensaje claro
        story.append(Paragraph(
            "No se han identificado sedes físicas asociadas a la empresa mediante las fuentes consultadas.",
            styles["Italic"]
        ))
        story.append(Spacer(1, 15))

    # ======= Mapa =======
    if locations:
        img_path = generar_mapa_sedes(locations)
        if img_path:
            story.append(Paragraph("Mapa de Sedes", styles["Heading2"]))
            story.append(Image(img_path, width=500, height=300))
            story.append(Spacer(1, 15))


    #=================Empleados===================
    employees = record.get("employees", [])

    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Empleados Identificados</b>", styles["Heading2"]))
    story.append(Spacer(1, 6))

    if not employees:
        story.append(Paragraph("No se han encontrado empleados asociados.", styles["Normal"]))
        story.append(Spacer(1, 12))
        return

    # Explicación introductoria
    intro = (
        "Esta sección recoge los empleados encontrados mediante búsquedas OSINT en fuentes públicas. "
        "Los resultados incluyen el nombre del perfil, el enlace público encontrado y un extracto del contenido asociado."
    )
    story.append(Paragraph(intro, styles["Normal"]))
    story.append(Spacer(1, 12))

    # Tabla
    data = [["Nombre", "Perfil", "Extracto"]]

    for emp in employees:
        name = emp.get("name", "")
        link = emp.get("profile_link", "")
        additional_data = emp.get("additional_data", "")

        data.append([
            Paragraph(name, styles["Normal"]),
            Paragraph(f'<a href="{link}">{link}</a>', styles["Normal"]),
            Paragraph(additional_data or "-", styles["Normal"])
        ])

    table = Table(data, colWidths=[150, 200, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))

    story.append(table)
    story.append(Spacer(1, 24))


    # Comprobar dominios que expiran en menos de un año
    dominios_criticos = dominios_por_expirar(domains)
    if dominios_criticos:
        story.append(Paragraph("Dominios que expiran en menos de medio año", styles["Heading2"]))
        data = [["Dominio", "Fecha de Expiración"]]
        for item in dominios_criticos:
            data.append([item["dominio"], item["expiration_date"].strftime("%d/%m/%Y")])

        table = Table(data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#FF4F4F")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#FFDCDC")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))
        story.append(table)
        story.append(Spacer(1, 15))
    # Guardar PDF
    doc.build(story)
    print(f"[+] Informe generado: reports/{company_name}_informe.pdf")
