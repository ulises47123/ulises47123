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


def main():
    SALIDA.mkdir(exist_ok=True)
    repos = repos_propios()
    (SALIDA / "lenguajes.svg").write_text(tarjeta_lenguajes(repos), encoding="utf-8")
    (SALIDA / "resumen.svg").write_text(
        tarjeta_resumen(repos, contribuciones_anio()), encoding="utf-8")
    print(f"Listo: {len(repos)} repos procesados")


if __name__ == "__main__":
    main()
