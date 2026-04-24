#!/usr/bin/env python3

import json
import os
import sys
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class AnalizadorPersonalidad:
    """Analiza la personalidad de un perfil de Instagram usando los captions
    de sus posts y la bio, enviándolos a un LLM gratuito (Groq)."""

    MODELO = "llama-3.3-70b-versatile"

    _SYSTEM = (
        "Eres un psicólogo experto en análisis de personalidad digital. "
        "Analiza el comportamiento en redes sociales y entrega diagnósticos "
        "concisos y precisos. Responde siempre en español. Sé directo y evita generalidades."
    )

    def __init__(self, api_key: str, modelo: str = MODELO):
        self._client = Groq(api_key=api_key)
        self._modelo = modelo

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    @classmethod
    def desde_archivo(cls, ruta_json: str, api_key: str | None = None) -> "AnalizadorPersonalidad":
        """Carga los datos del JSON del scraper y retorna la instancia lista para analizar."""
        instancia = cls(api_key or os.getenv("GROQ_API_KEY", ""))
        instancia._datos = cls._cargar_json(ruta_json)
        return instancia

    def analizar(self, datos: dict | None = None) -> dict:
        """Ejecuta el análisis y retorna un dict con username + texto del análisis."""
        datos = datos or getattr(self, "_datos", None)
        if not datos:
            raise ValueError("No hay datos cargados. Usa desde_archivo() o pasa un dict.")

        perfil = datos["perfil"]
        posts = datos.get("posts", [])
        captions = [
            p["caption"].strip() if p.get("caption", "").strip() else "(sin descripción)"
            for p in posts
        ]

        prompt = self._construir_prompt(
            username=perfil["username"],
            bio=perfil.get("biografia", ""),
            captions=captions,
        )

        texto = self._llamar_llm(prompt)

        return {
            "username": perfil["username"],
            "nombre_completo": perfil.get("nombre_completo", ""),
            "posts_analizados": len(posts),
            "analisis": texto,
        }

    def guardar_resultado(self, resultado: dict, ruta: str | None = None) -> str:
        """Guarda el análisis en un archivo JSON y retorna la ruta."""
        ruta = ruta or f"analisis_{resultado['username']}.json"
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        return ruta

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _construir_prompt(self, username: str, bio: str, captions: list[str]) -> str:
        captions_texto = "\n".join(
            f"[Post {i+1}] {c}" for i, c in enumerate(captions)
        )

        return f"""Analiza la personalidad de @{username} basándote exclusivamente en su actividad pública de Instagram.

BIO: {bio.strip() or '(sin bio)'}

DESCRIPCIONES DE SUS {len(captions)} POSTS MÁS RECIENTES:
{captions_texto}

Entrega el análisis en este formato exacto:

**TIPO DE PERSONALIDAD:** [nombre o arquetipo en 1-3 palabras]

**RASGOS PRINCIPALES:**
• [rasgo 1]: [descripción breve]
• [rasgo 2]: [descripción breve]
• [rasgo 3]: [descripción breve]

**ESTILO DE COMUNICACIÓN:** [1 oración]

**MOTIVACIÓN CENTRAL:** [1 oración]

**RESUMEN:** [2-3 oraciones máximo, sin repetir lo anterior]"""

    def _llamar_llm(self, prompt: str) -> str:
        completion = self._client.chat.completions.create(
            model=self._modelo,
            messages=[
                {"role": "system", "content": self._SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=600,
        )
        return completion.choices[0].message.content.strip()

    @staticmethod
    def _cargar_json(ruta: str) -> dict:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)


# ------------------------------------------------------------------
# Uso directo: python analizador_personalidad.py resultado_xxx.json
# ------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Uso: python analizador_personalidad.py <resultado.json>")
        sys.exit(1)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] Falta GROQ_API_KEY en .env")
        sys.exit(1)

    ruta_json = sys.argv[1]
    print(f"Analizando {ruta_json}...")

    analizador = AnalizadorPersonalidad.desde_archivo(ruta_json, api_key)
    resultado = analizador.analizar()

    print(f"\n{'='*60}")
    print(f"  ANÁLISIS DE PERSONALIDAD — @{resultado['username']}")
    print(f"  ({resultado['posts_analizados']} posts analizados)")
    print(f"{'='*60}\n")
    print(resultado["analisis"])

    ruta_guardado = analizador.guardar_resultado(resultado)
    print(f"\n[OK] Guardado en '{ruta_guardado}'")


if __name__ == "__main__":
    main()
