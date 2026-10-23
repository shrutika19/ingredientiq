import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const { VITE_API_BASE_URL = "http://localhost:8000" } = loadEnv(
    mode,
    process.cwd(),
    "VITE_",
  );
  const apiUrl = new URL(VITE_API_BASE_URL);
  if (apiUrl.protocol !== "http:" && apiUrl.protocol !== "https:") {
    throw new Error("VITE_API_BASE_URL must use HTTP or HTTPS");
  }

  return {
    plugins: [
      react(),
      tailwindcss(),
      {
        name: "frontend-content-security-policy",
        transformIndexHtml(html: string) {
          return html.replace("__API_ORIGIN__", apiUrl.origin);
        },
      },
    ],
  };
});