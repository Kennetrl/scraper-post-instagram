#!/usr/bin/env python3

import os
import json
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

COOKIE_STRING   = os.getenv("INSTA_COOKIE", "")
TARGET_USERNAME = os.getenv("TARGET_USERNAME", "")
NUMBER_POSTS    = int(os.getenv("NUMBER_POSTS", 10))
IG_APP_ID       = "936619743392459"


# Convierte la cadena de cookies del navegador en un diccionario
def parsear_cookies(cookie_str: str) -> dict:
    cookies = {}
    for parte in cookie_str.split("; "):
        parte = parte.strip()
        if "=" in parte:
            clave, valor = parte.split("=", 1)
            cookies[clave.strip()] = valor.strip()
    return cookies


# Construye los headers HTTP necesarios para autenticarse en la API interna
def construir_headers(cookies_dict: dict) -> dict:
    csrf = cookies_dict.get("csrftoken", "")
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "x-ig-app-id": IG_APP_ID,
        "x-csrftoken": csrf,
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.instagram.com/",
        "Origin": "https://www.instagram.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }


# Imprime el código de error HTTP y detiene la ejecución
def manejar_error_http(response: requests.Response) -> None:
    codigos = {
        401: "Sesión expirada.",
        429: "Limite de tiempo",
        404: f"Perfil @{TARGET_USERNAME} no encontrado o es privado.",
    }
    msg = codigos.get(response.status_code, f"Respuesta inesperada: {response.text[:200]}")
    print(f"\n[ERROR {response.status_code}] {msg}")
    raise SystemExit(1)


# Pausa entre requests para no saturar la API
def esperar(segundos: float) -> None:
    print(f"    (pausa de {segundos}s...)")
    time.sleep(segundos)


# Retorna el JSON de la respuesta o None si el body está vacío o no es JSON válido
def _get_json_seguro(respuesta: requests.Response) -> dict | None:
    if not respuesta.text.strip():
        return None
    try:
        return respuesta.json()
    except Exception:
        return None


# Obtiene los datos del perfil: nombre, bio, seguidores, siguiendo, posts y user_id
def obtener_info_perfil(username: str, session: requests.Session) -> dict:
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    print(f"[1/3] Obteniendo perfil de @{username}...")

    respuesta = session.get(url)
    if respuesta.status_code != 200:
        manejar_error_http(respuesta)

    usuario = respuesta.json()["data"]["user"]
    perfil = {
        "username":        usuario.get("username"),
        "nombre_completo": usuario.get("full_name"),
        "biografia":       usuario.get("biography"),
        "seguidores":      usuario["edge_followed_by"]["count"],
        "siguiendo":       usuario["edge_follow"]["count"],
        "total_posts":     usuario["edge_owner_to_timeline_media"]["count"],
        "user_id":         usuario.get("id"),
        "es_privado":      usuario.get("is_private"),
        "verificado":      usuario.get("is_verified"),
        "foto_perfil_url": usuario.get("profile_pic_url_hd") or usuario.get("profile_pic_url"),
    }

    print(f"    @{perfil['username']} | {perfil['seguidores']:,} seguidores | {perfil['total_posts']:,} posts")
    return perfil


# Obtiene los posts recientes: fecha, caption, likes, URL y tipo de media
def obtener_posts(user_id: str, session: requests.Session, cantidad: int = NUMBER_POSTS) -> list:
    url = f"https://www.instagram.com/api/v1/feed/user/{user_id}/?count={cantidad}"
    print(f"\n[2/3] Obteniendo últimos {cantidad} posts...")

    respuesta = session.get(url)
    if respuesta.status_code != 200:
        manejar_error_http(respuesta)

    datos = respuesta.json()
    items = datos.get("items", [])

    # Paginación: Instagram devuelve next_max_id cuando hay más páginas.
    # Para más de 12 posts.
    # next_max_id = datos.get("next_max_id")
    # while next_max_id and len(items) < cantidad:
    #     url_pagina = f"{url}&max_id={next_max_id}"
    #     resp2 = session.get(url_pagina)
    #     datos2 = resp2.json()
    #     items += datos2.get("items", [])
    #     next_max_id = datos2.get("next_max_id")
    #     esperar(2)

    posts = []
    for item in items[:cantidad]:
        caption_obj = item.get("caption")
        caption_texto = caption_obj.get("text", "") if isinstance(caption_obj, dict) else ""
        timestamp = item.get("taken_at", 0)
        shortcode = item.get("code", "")

        posts.append({
            "post_id":           item.get("id"),
            "shortcode":         shortcode,
            "url":               f"https://www.instagram.com/p/{shortcode}/",
            "fecha":             datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "likes":             item.get("like_count", 0),
            "caption":           caption_texto,
            "comentarios_count": item.get("comment_count", 0),
            "tipo_media":        item.get("media_type", 1),
        })

    print(f"    {len(posts)} posts obtenidos")
    return posts


# Busca si el autor del post respondió a un comentario.
# Primero revisa preview_child_comments; si no encuentra, consulta el endpoint de replies.
def buscar_respuesta_autor(
    preview_replies: list,
    comment_pk: str,
    media_pk: str,
    autor_user_id: str,
    session: requests.Session,
) -> dict | None:
    def es_del_autor(reply: dict) -> bool:
        uid = str(reply.get("user", {}).get("pk") or reply.get("user", {}).get("id", ""))
        return uid == str(autor_user_id)

    def formatear(reply: dict) -> dict:
        ts = reply.get("created_at", 0)
        return {
            "texto": reply.get("text", ""),
            "fecha": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
        }

    for reply in preview_replies:
        if es_del_autor(reply):
            return formatear(reply)

    if not comment_pk:
        return None

    url_child = (
        f"https://www.instagram.com/api/v1/media/{media_pk}/comments/{comment_pk}/child_comments/"
        "?max_id=&min_id="
    )
    datos = _get_json_seguro(session.get(url_child))
    if not datos:
        return None

    for reply in datos.get("child_comments", []):
        if es_del_autor(reply):
            return formatear(reply)

    return None


# Obtiene los primeros comentarios de un post e incluye la respuesta del autor si existe.
# El campo respuesta_autor es null cuando el autor no respondió ese comentario.
def obtener_comentarios(
    media_id: str,
    autor_user_id: str,
    session: requests.Session,
    cantidad: int = 3,
) -> list:
    pk = media_id.split("_")[0]
    url = (
        f"https://www.instagram.com/api/v1/media/{pk}/comments/"
        "?can_support_threading=true&permalink_enabled=false"
    )

    respuesta = session.get(url)

    if respuesta.status_code == 429:
        print("    [Rate limit — esperando 30s...]")
        time.sleep(30)
        respuesta = session.get(url)

    if respuesta.status_code != 200:
        print(f"    [Sin comentarios — HTTP {respuesta.status_code}]")
        return []

    datos = _get_json_seguro(respuesta)
    if not datos:
        print("    [Comentarios no disponibles]")
        return []

    comentarios_raw = datos.get("comments", [])
    if not comentarios_raw:
        print("    [0 comentarios]")
        return []

    comentarios = []
    for c in comentarios_raw[:cantidad]:
        ts = c.get("created_at", 0)
        comment_pk = str(c.get("pk") or c.get("id", ""))
        preview_replies = c.get("preview_child_comments", [])

        tiene_replies = c.get("child_comment_count", 0) > 0 or bool(preview_replies)
        respuesta_autor = buscar_respuesta_autor(
            preview_replies, comment_pk, pk, str(autor_user_id), session
        ) if tiene_replies else None

        comentarios.append({
            "autor":           c.get("user", {}).get("username", "desconocido"),
            "texto":           c.get("text", ""),
            "fecha":           datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            "respuesta_autor": respuesta_autor,
        })

    return comentarios


def main():
    print("=" * 50)
    print("  Instagram Scraper")
    print("=" * 50)

    if not TARGET_USERNAME:
        print("[ERROR] Falta TARGET_USERNAME en .env")
        raise SystemExit(1)

    if not COOKIE_STRING:
        print("[ERROR] Falta INSTA_COOKIE en .env")
        raise SystemExit(1)

    cookies_dict = parsear_cookies(COOKIE_STRING)
    session = requests.Session()
    session.cookies.update(cookies_dict)
    session.headers.update(construir_headers(cookies_dict))

    perfil = obtener_info_perfil(TARGET_USERNAME, session)
    user_id = perfil["user_id"]
    esperar(2)

    posts = obtener_posts(user_id, session, cantidad=NUMBER_POSTS)
    esperar(2)

    print(f"\n[3/3] Obteniendo comentarios...")
    for i, post in enumerate(posts, start=1):
        print(f"    Post {i}/{len(posts)}: {post['url']}")
        post["primeros_comentarios"] = obtener_comentarios(post["post_id"], user_id, session, cantidad=3)
        esperar(1.5)

    resultado = {
        "perfil":      perfil,
        "posts":       posts,
        "generado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    nombre_archivo = f"resultado_{TARGET_USERNAME}.json"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Datos guardados en '{nombre_archivo}'")

    print("\n" + "=" * 60)
    print(f"PERFIL: @{perfil['username']}")
    print("=" * 60)
    print(f"  Nombre:      {perfil['nombre_completo']}")
    print(f"  Seguidores:  {perfil['seguidores']:,}")
    print(f"  Siguiendo:   {perfil['siguiendo']:,}")
    print(f"  Total posts: {perfil['total_posts']:,}")
    bio = perfil["biografia"] or ""
    print(f"  Biografía:   {bio[:80]}{'...' if len(bio) > 80 else ''}")
    print(f"\n  Últimos {len(posts)} posts:")

    for p in posts:
        print(f"\n    [{p['fecha']}] {p['likes']:,} likes — {p['url']}")
        caption_preview = p["caption"][:80].replace("\n", " ")
        if caption_preview:
            print(f"    Caption: {caption_preview}{'...' if len(p['caption']) > 80 else ''}")
        for c in p.get("primeros_comentarios", []):
            print(f"      @{c['autor']}: {c['texto'][:70]}")
            ra = c.get("respuesta_autor")
            if ra:
                print(f"@{perfil['username']} (autor): {ra['texto'][:70]}")

    print(f"\n  Datos completos en: {nombre_archivo}")


if __name__ == "__main__":
    main()
