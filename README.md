# Scraper Instagram — API interna

Script en Python que extrae datos de un perfil público de Instagram usando la API interna del sitio web, sin Selenium ni librerías de scraping.

## ¿Qué extrae?

- Datos del perfil: nombre, biografía, seguidores, seguidos y total de posts
- Últimos 12 posts: fecha, caption, likes y URL
- Primeros 3 comentarios por post, con la respuesta del autor si existe

## Requisitos

- Python 3.10+
- Una cuenta de Instagram activa para obtener las cookies de sesión

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd scraper-post-instagram

# 2. Crear y activar el entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / Mac

# 3. Instalar dependencias
pip install -r requirements.txt
```

## Configuración

Crea un archivo `.env` en la raíz del proyecto con este contenido:

```
INSTA_COOKIE=<tu cadena de cookies>
TARGET_USERNAME=<usuario a consultar>
```

### Cómo obtener las cookies desde DevTools

1. Abre Chrome o Edge y ve a `https://www.instagram.com`
2. Inicia sesión con tu cuenta
3. Presiona `F12` para abrir DevTools
4. Ve a la pestaña **Network** (Red)
5. Activa **Preserve log** (checkbox arriba a la izquierda)
6. En el filtro escribe: `web_profile_info`
7. Recarga la página con `F5`
8. Haz clic en la request que aparezca
9. En el panel derecho ve a **Headers → Request Headers**
10. Busca la línea `cookie:` y copia **todo** el valor
11. Pégalo en el `.env` como `INSTA_COOKIE=<valor copiado>`

> Las cookies expiran cada pocos días. Si ves el error 401, repite el proceso.

## Uso

```bash
python scraper-instagram.py
```

El resultado se guarda en `resultado_<usuario>.json` y se muestra un resumen en consola.

## Estructura del JSON de salida

```json
{
  "perfil": {
    "username": "...",
    "nombre_completo": "...",
    "biografia": "...",
    "seguidores": 0,
    "siguiendo": 0,
    "total_posts": 0
  },
  "posts": [
    {
      "url": "https://www.instagram.com/p/...",
      "fecha": "2026-01-01 12:00 UTC",
      "likes": 0,
      "caption": "...",
      "primeros_comentarios": [
        {
          "autor": "usuario",
          "texto": "...",
          "fecha": "2026-01-01",
          "respuesta_autor": null
        }
      ]
    }
  ]
}
```
