import networkx as nx
import ipaddress
from datetime import datetime
from pyvis.network import Network
import json

def object_to_html(obj, indent=0):
    html = ""

    if isinstance(obj, dict):
        for k, v in obj.items():
            html += "&nbsp;" * indent + f"<b>{k}</b>:<br>"
            html += object_to_html(v, indent + 4)

    elif isinstance(obj, list):
        for item in obj:
            html += "&nbsp;" * indent + "- "
            html += object_to_html(item, indent + 4)

    else:
        html += "&nbsp;" * indent + f"{obj}<br>"

    return html

def create_graph(company_name, db, date_str=None):
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")

    data = db[date_str].find_one({"company": company_name})
    if not data:
        print(f"[!] No se encontraron datos para {company_name} en {date_str}")
        return
    node_info = {}

    G = nx.Graph()
    
    for asn in data.get("asn", []):
        node_info[asn] = {"type": "ASN", "value": asn}
        G.add_node(asn, type="asn")

    for r in data.get("ranges", []):
        node_info[r] = {"type": "Range", "value": r}
        G.add_node(r, type="range")

        for asn in data.get("asn", []):
            G.add_edge(asn, r, relation="announces")
    for domain in data.get("domains", []):

        dname = domain.get("name")
        ip = domain.get("ip")

        if not dname:
            continue
        node_info[dname] = domain
        G.add_node(dname, type="domain")

        if ip:
            G.add_node(ip, type="ip")
            G.add_edge(dname, ip, relation="resolves_to")

            for r in data.get("ranges", []):
                if ipaddress.ip_address(ip) in ipaddress.ip_network(r, strict=False):
                    G.add_edge(ip, r, relation="in_range")
    for asset in data.get("shodan_assets", []):

        ip = asset.get("ip")
        asn = asset.get("asn")

        if ip:
            node_info[ip] = asset
            G.add_node(ip, type="ip")

        if asn:
            G.add_node(asn, type="asn")
            G.add_edge(ip, asn, relation="belongs_to")
    for leak in data.get("domain_leaks", []):

        domain = leak.get("domain")

        if domain:
            node_info[f"leak_{domain}"] = leak
            leak_node = f"leak_{domain}"
            G.add_node(leak_node, type="leak")
            G.add_edge(domain, leak_node, relation="breach")

    net = Network(height="800px", width="100%")

    color_map = {
        "asn": "pink",
        "range": "orange",
        "ip": "green",
        "domain": "purple",
        "asset": "blue",
        "leak": "red"
    }

    for node, data in G.nodes(data=True):

        node_type = data.get("type", "unknown")
        info = node_info.get(node, {"value": node})

        html_info = f"<h3>{node}</h3>"
        html_info += object_to_html(info)

        net.add_node(
            node,
            label=node,
            color=color_map.get(node_type, "gray"),
            title=html_info
        )

    for src, dst, data in G.edges(data=True):

        net.add_edge(
            src,
            dst,
            title=data.get("relation")
        )

    net.write_html(f"src/reports/{company_name}_infraestructura.html")
    with open(f"src/reports/{company_name}_infraestructura.html", "r", encoding="utf8") as f:
        html = f.read()

    panel = """
    <div id="mainContainer" style="
    display:flex;
    width:100vw;
    height:100vh;
    overflow:hidden;
    ">

    <div id="graphContainer" style="
    flex:3;
    height:100%;
    border-right:2px solid #ddd;
    ">
    </div>

    <div id="infoPanel" style="
    flex:1;
    height:100%;
    overflow:auto;
    padding:15px;
    background:#fafafa;
    font-family: Arial;
    ">
    <h2>Node information</h2>
    Click en un nodo para ver los detalles
    </div>

    </div>
    """

    html = html.replace("<body>", "<body>" + panel)

    script = """
    <script>

    document.addEventListener("DOMContentLoaded", function(){

        var networkDiv = document.getElementById("mynetwork");
        var graphContainer = document.getElementById("graphContainer");

        graphContainer.appendChild(networkDiv);

    });

    network.on("click", function(params){

        if(params.nodes.length > 0){

            var nodeId = params.nodes[0];
            var node = nodes.get(nodeId);

            document.getElementById("infoPanel").innerHTML =
            "<h2>"+node.label+"</h2>" + node.title;

        }

    });

    </script>
    """

    html = html.replace("</body>", script + "</body>")

    with open(f"src/reports/{company_name}_infraestructura.html", "w", encoding="utf8") as f:
        f.write(html)
    print(f"[+] Grafo generado: src/reports/{company_name}_infraestructura.html")