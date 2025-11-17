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
    limite = hoy + timedelta(days=365)

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


    resumen_data = [
        ["Elementos encontrados", ""],
        ["Dominios Identificados", num_domains],
        ["Subdominios Descubiertos", num_subdomains],
        ["ASN", num_asn],
        ["Rutas", num_routes],
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
    alt_names = record.get("alternativeNames", {})
    story.append(Paragraph("Nombres Alternativos", styles["Heading2"]))
    for category, names in alt_names.items():
        if names:
            story.append(Paragraph(f"<b>{category.capitalize()}</b>: {', '.join(names)}", styles["Normal"]))
            story.append(Spacer(1, 5))

    # ======= Dominios =======
    story.append(Paragraph("Dominios Identificados", styles["Heading2"]))
    domains = record.get("domains", [])
    if domains:
        data = [["Dominio", "Dirección IP", "Fuente"]]
        for d in domains:
            data.append([
                d.get("name", ""),
                d.get("ip", ""),
                d.get("source", "")
            ])
        table = Table(data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))
        story.append(table)
    story.append(Spacer(1, 15))

    # ======= Subdominios =======
    story.append(Paragraph("Subdominios Descubiertos", styles["Heading2"]))
    subs = record.get("subdomains", [])
    if subs:
        data = [["Subdominio", "Categoría", "Dominio Padre"]]
        for s in subs:
            data.append([s.get("name", ""), s.get("category", ""), s.get("domain", "")])
        table = Table(data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))
        story.append(table)
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
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F3F6FB")),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))

            story.append(table)
            story.append(Spacer(1, 15))
        else:
            story.append(Paragraph("No hay información WHOIS válida que mostrar.", styles["Italic"]))
            story.append(Spacer(1, 10))


    # ======= ASN =======
    story.append(Paragraph("ASN Asociados", styles["Heading2"]))
    asns = record.get("asn", [])  # ahora es lista de strings
    if asns:
        asn_data = [["ASN"]]
        for a in asns:
            asn_data.append([a])  # cada ASN en una fila
        table = Table(asn_data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))
        story.append(table)
        story.append(Spacer(1, 15))

    # ======= Rutas =======
    story.append(Paragraph("Rutas de Red", styles["Heading2"]))
    routes = record.get("routes", [])  # lista de strings
    if routes:
        routes_data = [["Red"]]
        for r in routes:
            routes_data.append([r])  # cada ruta en una fila
        table = Table(routes_data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))
        story.append(table)
        story.append(Spacer(1, 15))

    # ======= Sedes Físicas =======
    story.append(Paragraph("Sedes Físicas", styles["Heading2"]))
    story.append(Spacer(1, 6))

    # Introducción
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
        loc_data = [["Dirección", "Tipo", "Rating", "Teléfono"]]

        for loc in locations:
            loc_data.append([
                Paragraph(loc.get("address", "") or "-", styles["Normal"]),
                Paragraph(loc.get("type", "") or "-", styles["Normal"]),
                Paragraph(str(loc.get("rating", "")) or "-", styles["Normal"]),
                Paragraph(loc.get("phone", "") or "-", styles["Normal"])
            ])

        # Ajuste automático: colWidths=None para que se adapten, pero con máximo razonable si quieres
        table = Table(
            loc_data,
            hAlign='LEFT',
            colWidths=[200, 120, 60, 120]  # columnas proporcionadas y con salto de línea
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
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    story.append(table)
    story.append(Spacer(1, 24))


    # Comprobar dominios que expiran en menos de un año
    dominios_criticos = dominios_por_expirar(domains)
    if dominios_criticos:
        story.append(Paragraph("Dominios que expiran en menos de un año", styles["Heading2"]))
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
