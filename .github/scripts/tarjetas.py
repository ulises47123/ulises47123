"""Genera las tarjetas SVG del perfil (estadísticas y lenguajes).

Se ejecuta desde GitHub Actions una vez al día. Solo usa la biblioteca
estándar de Python y la API pública de GitHub, así no depende de servicios
externos que a veces se caen (github-readme-stats, etc.).
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USUARIO = os.environ.get("GH_USER", "ulises47123")
TOKEN = os.environ.get("GH_TOKEN", "")
SALIDA = Path("assets")

# Colores de lenguajes (los mismos que usa GitHub)
COLORES = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "HTML": "#e34c26",
    "CSS": "#563d7c", "Kotlin": "#A97BFF", "Shell": "#89e051",
    "TypeScript": "#3178c6", "Astro": "#ff5a03", "Tcl": "#e4cc98",
    "Java": "#b07219", "C#": "#178600", "PowerShell": "#012456",
    "Batchfile": "#C1F12E", "GDScript": "#355570", "Vue": "#41b883",
}

# Lenguajes que inflan el conteo sin ser código propio
IGNORAR = {"Tcl", "XSLT", "Batchfile", "Inno Setup", "NSIS", "Jupyter Notebook"}


def api(url, data=None):
    req = urllib.request.Request(url, data=data)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "perfil-tarjetas")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def repos_propios():
    repos, pagina = [], 1
    while True:
        lote = api(f"https://api.github.com/users/{USUARIO}/repos"
                   f"?per_page=100&page={pagina}&type=owner")
        if not lote:
            return [r for r in repos if not r["fork"]]
        repos += lote
        pagina += 1


def contribuciones_anio():
    if not TOKEN:
        return None
    consulta = {"query": "query($u:String!){user(login:$u){contributionsCollection"
                         "{contributionCalendar{totalContributions}}}}",
                "variables": {"u": USUARIO}}
    try:
        r = api("https://api.github.com/graphql", json.dumps(consulta).encode())
        return r["data"]["user"]["contributionsCollection"][
            "contributionCalendar"]["totalContributions"]
    except Exception:
        return None


ESTILO = """<style>
  .fondo { fill: #ffffff; stroke: #d0d7de; }
  .titulo { font: 600 19px 'Segoe UI', Ubuntu, sans-serif; fill: #0969da; }
  .texto { font: 400 15px 'Segoe UI', Ubuntu, sans-serif; fill: #1f2328; }
  .tenue { font: 400 14px 'Segoe UI', Ubuntu, sans-serif; fill: #59636e; }
  .numero { font: 700 32px 'Segoe UI', Ubuntu, sans-serif; fill: #1f2328; }
  .pista { fill: #eaeef2; }
  @media (prefers-color-scheme: dark) {
    .fondo { fill: #0d1117; stroke: #30363d; }
    .titulo { fill: #58a6ff; }
    .texto, .numero { fill: #e6edf3; }
    .tenue { fill: #9198a1; }
    .pista { fill: #21262d; }
  }
</style>"""


def tarjeta_lenguajes(repos):
    total = {}
    for r in repos:
        for lang, b in api(r["languages_url"]).items():
            if lang not in IGNORAR:
                total[lang] = total.get(lang, 0) + b
    suma = sum(total.values()) or 1
    top = sorted(total.items(), key=lambda x: -x[1])[:8]

    ancho, alto = 420, 270
    filas, y = [], 66
    for lang, b in top:
        pct = b / suma * 100
        color = COLORES.get(lang, "#8b949e")
        barra = max(3, 190 * pct / 100)
        filas.append(
            f'<circle cx="30" cy="{y - 5}" r="6" fill="{color}"/>'
            f'<text x="44" y="{y}" class="texto">{lang}</text>'
            f'<rect x="150" y="{y - 11}" width="190" height="10" rx="5" class="pista"/>'
            f'<rect x="150" y="{y - 11}" width="{barra:.1f}" height="10" rx="5" fill="{color}"/>'
            f'<text x="352" y="{y}" class="tenue">{pct:.1f}%</text>')
        y += 25
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
            f'viewBox="0 0 {ancho} {alto}">{ESTILO}'
            f'<rect x="0.5" y="0.5" width="{ancho - 1}" height="{alto - 1}" rx="10" class="fondo"/>'
            f'<text x="22" y="34" class="titulo">Lenguajes más usados</text>'
            + "".join(filas) + "</svg>")


def tarjeta_resumen(repos, contribs):
    creado = datetime.fromisoformat(
        api(f"https://api.github.com/users/{USUARIO}")["created_at"].replace("Z", "+00:00"))
    anios = (datetime.now(timezone.utc) - creado).days / 365.25
    datos = [
        (str(len(repos)), "repositorios"),
        (str(sum(1 for r in repos if r.get("has_pages"))), "páginas publicadas"),
        (str(contribs) if contribs is not None else "—", "contribuciones (último año)"),
        (f"{anios:.1f}", "años en GitHub"),
    ]
    ancho, alto = 420, 270
    celdas = []
    for i, (num, etiqueta) in enumerate(datos):
        x = 30 + (i % 2) * 200
        y = 100 + (i // 2) * 88
        celdas.append(f'<text x="{x}" y="{y}" class="numero">{num}</text>'
                      f'<text x="{x}" y="{y + 26}" class="tenue">{etiqueta}</text>')
    fecha = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
            f'viewBox="0 0 {ancho} {alto}">{ESTILO}'
            f'<rect x="0.5" y="0.5" width="{ancho - 1}" height="{alto - 1}" rx="10" class="fondo"/>'
            f'<text x="22" y="34" class="titulo">Resumen en GitHub</text>'
            + "".join(celdas) +
            f'<text x="22" y="{alto - 18}" class="tenue">Actualizado el {fecha}</text></svg>')


# Proyectos destacados: (repo, título, descripción, tecnologías)
DESTACADOS = [
    ("jujuy-ciudad-pass", "Jujuy Ciudad Pass",
     "Plataforma turística con app Android, web y panel de administración, en un servidor propio.",
     "Python · FastAPI · Kotlin · JS"),
    ("proyecto-ies-5-launcher", "Campus Virtual IES N°5",
     "App de escritorio para ver clases, notas y mensajes del campus del instituto.",
     "Python · Pyloid · Tailwind"),
    ("Recurso-Hidricos", "Recursos Hídricos",
     "Sistema de gestión de personal, licencias y contratos que funciona 100 % offline.",
     "Electron · FastAPI · SQLite"),
    ("Milagro-Costurera-y-Arreglo", "Milagro Costurera",
     "Página web para un emprendimiento de costura y arreglos.",
     "Astro"),
    ("VTuber", "VTuber 2D",
     "Avatar que se anima con el micrófono, con cámara virtual y grabación.",
     "Python · OpenCV"),
    ("agiltp", "agiltp",
     "Programas para dar formato APA y crear carátulas de trabajos prácticos.",
     "Python"),
]


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def partir(texto, max_chars):
    lineas, actual = [], ""
    for palabra in texto.split():
        if len(actual) + len(palabra) + 1 > max_chars and actual:
            lineas.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    return lineas + ([actual] if actual else [])


def tarjeta_proyecto(repo, titulo, desc, tecnologias, info):
    ancho, alto = 420, 140
    color = COLORES.get(info.get("language") or "", "#8b949e")
    lineas = "".join(f'<text x="22" y="{66 + i * 20}" class="texto">{esc(l)}</text>'
                     for i, l in enumerate(partir(desc, 52)[:2]))
    estrellas = info.get("stargazers_count", 0)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
            f'viewBox="0 0 {ancho} {alto}">{ESTILO}'
            f'<rect x="0.5" y="0.5" width="{ancho - 1}" height="{alto - 1}" rx="10" class="fondo"/>'
            # icono de repositorio (octicon repo)
            f'<g transform="translate(22,18)" class="tenue"><path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"/></g>'
            f'<text x="46" y="31" class="titulo">{esc(titulo)}</text>'
            + lineas +
            f'<circle cx="28" cy="{alto - 25}" r="6" fill="{color}"/>'
            f'<text x="40" y="{alto - 20}" class="tenue">{esc(tecnologias)}</text>'
            f'<text x="{ancho - 22}" y="{alto - 20}" text-anchor="end" class="tenue">★ {estrellas}</text>'
            "</svg>")


def banner():
    ancho, alto = 900, 220
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#0d1117"/><stop offset=".55" stop-color="#132a4a"/><stop offset="1" stop-color="#1f6feb"/>
  </linearGradient>
  <pattern id="p" width="28" height="28" patternUnits="userSpaceOnUse">
    <path d="M28 0H0V28" fill="none" stroke="#ffffff" stroke-opacity=".05"/>
  </pattern>
</defs>
<style>
  .n {{ font: 700 46px 'Segoe UI', Ubuntu, sans-serif; fill: #ffffff; }}
  .s {{ font: 400 20px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; }}
  .c {{ font: 600 15px Consolas, 'Fira Code', monospace; fill: #79c0ff; }}
  .k {{ font: 700 120px Consolas, monospace; fill: #ffffff; fill-opacity: .07; }}
  .cur {{ animation: b 1s step-end infinite; }}
  @keyframes b {{ 50% {{ opacity: 0; }} }}
</style>
<rect width="{ancho}" height="{alto}" rx="14" fill="url(#g)"/>
<rect width="{ancho}" height="{alto}" rx="14" fill="url(#p)"/>
<text x="{ancho - 40}" y="160" text-anchor="end" class="k">&lt;/&gt;</text>
<text x="50" y="62" class="c">~/jujuy/argentina $ whoami</text>
<text x="48" y="122" class="n">Ulises Julián Cabezas</text>
<text x="50" y="160" class="s">Técnico en soporte informático · Python · Web · Android</text>
<rect x="50" y="178" width="12" height="3" fill="#79c0ff" class="cur"/>
</svg>'''


def main():
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "banner.svg").write_text(banner(), encoding="utf-8")
    (SALIDA / "proyectos").mkdir(exist_ok=True)
    for repo, titulo, desc, tec in DESTACADOS:
        try:
            info = api(f"https://api.github.com/repos/{USUARIO}/{repo}")
        except Exception:
            info = {}
        (SALIDA / "proyectos" / f"{repo}.svg").write_text(
            tarjeta_proyecto(repo, titulo, desc, tec, info), encoding="utf-8")
    repos = repos_propios()
    (SALIDA / "lenguajes.svg").write_text(tarjeta_lenguajes(repos), encoding="utf-8")
    (SALIDA / "resumen.svg").write_text(
        tarjeta_resumen(repos, contribuciones_anio()), encoding="utf-8")
    print(f"Listo: {len(repos)} repos procesados")


if __name__ == "__main__":
    main()
