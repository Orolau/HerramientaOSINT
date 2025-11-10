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

    for d in domains:
        whois = d.get("whois", {})
        if whois:
            story.append(Paragraph(f"<b>{d.get('name', '')}</b>", styles["Heading3"]))
            whois_data = []
            for k, v in whois.items():
                if v is None:
                    continue
                # Convertir listas a cadena
                if isinstance(v, list):
                    v_str_list = []
                    for item in v:
                        if isinstance(item, datetime):
                            v_str_list.append(item.strftime("%d/%m/%Y %H:%M"))
                        else:
                            v_str_list.append(str(item))
                    v_str = ', '.join(v_str_list)
                # Convertir datetime a string
                elif isinstance(v, datetime):
                    v_str = v.strftime("%d/%m/%Y %H:%M")
                else:
                    v_str = str(v)
                whois_data.append([k, v_str])
            
            if whois_data:  # Solo crear tabla si hay datos
                table = Table(whois_data, hAlign='LEFT', colWidths=[120, 300])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#D9E1F2")),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP')
                ]))
                story.append(table)
                story.append(Spacer(1, 10))
            else:
                story.append(Paragraph("No hay información WHOIS disponible.", styles["Normal"]))
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
    locations = record.get("locations", [])
    if locations:
        loc_data = [["Dirección", "Tipo", "Rating", "Teléfono"]]
        for loc in locations:
            loc_data.append([
                loc.get("address", ""),
                loc.get("type", ""),
                str(loc.get("rating", "")),
                loc.get("phone", "")
            ])
        table = Table(loc_data, hAlign='LEFT', colWidths=[80, 200, 80, 50, 80])
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
    img_path = generar_mapa_sedes(locations)
    if img_path:
        story.append(Paragraph("Mapa de Sedes", styles["Heading2"]))
        story.append(Image(img_path, width=500, height=300))
        story.append(Spacer(1, 15))


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
