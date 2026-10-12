import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// One script and one stylesheet, which pharness puts in the page: nothing is
// loaded from outside. `npm run build` writes them where the Python side reads them.
export default defineConfig({
  plugins: [react()],
  define: { "process.env.NODE_ENV": '"production"' },
  build: {
    outDir: "../src/pharness/output/ui",
    emptyOutDir: true,
    cssCodeSplit: false,
    lib: { entry: "src/main.jsx", formats: ["iife"], name: "PharnessCar", fileName: () => "car.js" },
    rollupOptions: { output: { assetFileNames: "car[extname]" } },
  },
});
