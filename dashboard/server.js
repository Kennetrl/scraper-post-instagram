const express = require("express");
const path = require("path");
const fs = require("fs");

const app = express();
const PORT = 3000;
const DATA_DIR = path.join(__dirname, "..");

app.use(express.static(path.join(__dirname, "public")));

app.get("/api/analyses", (_req, res) => {
  const files = fs
    .readdirSync(DATA_DIR)
    .filter((f) => f.startsWith("analisis_") && f.endsWith(".json"));

  const list = files.map((file) => {
    const data = JSON.parse(
      fs.readFileSync(path.join(DATA_DIR, file), "utf-8")
    );
    return {
      username: data.username,
      nombre_completo: data.nombre_completo,
      posts_analizados: data.posts_analizados,
      file,
    };
  });

  res.json(list);
});

app.get("/api/analyses/:username", (req, res) => {
  const file = path.join(DATA_DIR, `analisis_${req.params.username}.json`);
  if (!fs.existsSync(file)) {
    return res.status(404).json({ error: "Análisis no encontrado" });
  }
  res.json(JSON.parse(fs.readFileSync(file, "utf-8")));
});

app.listen(PORT, () => {
  console.log(`Dashboard corriendo en http://localhost:${PORT}`);
});
