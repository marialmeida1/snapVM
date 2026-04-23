const express = require("express");
const { Pool } = require("pg");
const { exec } = require("child_process");

const pool = new Pool({
  host: "127.0.0.1",
  port: 5432,
  user: "admin",
  password: "admin",
  database: "app_db",
});

const app = express();
app.use(express.json());

app.get("/health", async (req, res) => {
  try {
    await pool.query("SELECT 1 FROM users LIMIT 1");
    res.status(200).json({ status: "healthy" });
  } catch (err) {
    res.status(500).json({ status: "unhealthy", error: err.message });
  }
});

app.post("/exec", (req, res) => {
  const { command } = req.body;
  if (!command) return res.status(400).json({ error: "missing command" });

  exec(command, (error, stdout, stderr) => {
    res.json({
      stdout: stdout || "",
      stderr: stderr || "",
      error: error ? error.message : null,
    });
  });
});

app.listen(3000, "0.0.0.0", () => console.log("server listening on :3000"));
