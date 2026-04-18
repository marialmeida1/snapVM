const express = require("express");
const { Pool } = require("pg");

const pool = new Pool({
  host: "localhost",
  port: 5432,
  user: "admin",
  password: "admin",
  database: "app_db",
});

const app = express();

app.get("/health", async (req, res) => {
  try {
    await pool.query("SELECT 1 FROM users LIMIT 1");
    res.status(200).json({ status: "healthy" });
  } catch (err) {
    res.status(500).json({ status: "unhealthy", error: err.message });
  }
});

app.listen(3000, "0.0.0.0", () => console.log("server listening on :3000"));
