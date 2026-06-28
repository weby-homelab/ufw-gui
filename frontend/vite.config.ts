import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import { readFileSync } from "fs"

const packageJson = JSON.parse(readFileSync("./package.json", "utf-8"))

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(packageJson.version),
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000"
    }
  }
})
