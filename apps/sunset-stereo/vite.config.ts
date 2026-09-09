import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  base: "./",
  plugins: [svelte()],
  server: { host: true, port: 4173 },
  preview: { host: true, port: 4173 },
});
