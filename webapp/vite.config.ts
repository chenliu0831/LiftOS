import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

function liftosApiPlugin(): Plugin {
  const logsDir = path.resolve(__dirname, "../logs");

  return {
    name: "liftos-api",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url?.startsWith("/api/runs")) return next();

        const urlPath = req.url.replace("/api/runs", "");

        // GET /api/runs → list run directories
        if (urlPath === "" || urlPath === "/") {
          const entries = fs
            .readdirSync(logsDir, { withFileTypes: true })
            .filter((d) => d.isDirectory() && d.name.startsWith("run_"))
            .map((d) => d.name)
            .sort()
            .reverse();
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(entries));
          return;
        }

        // Serve file from logs directory
        const filePath = path.join(logsDir, urlPath);
        const resolved = path.resolve(filePath);
        if (!resolved.startsWith(logsDir)) {
          res.statusCode = 403;
          res.end("Forbidden");
          return;
        }

        if (!fs.existsSync(resolved)) {
          res.statusCode = 404;
          res.end("Not found");
          return;
        }

        const stat = fs.statSync(resolved);
        if (stat.isDirectory()) {
          // List directory contents
          const contents = fs.readdirSync(resolved);
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(contents));
          return;
        }

        const ext = path.extname(resolved);
        const contentType =
          ext === ".json" ? "application/json" : "text/plain";
        res.setHeader("Content-Type", contentType);
        fs.createReadStream(resolved).pipe(res);
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), liftosApiPlugin()],
});
