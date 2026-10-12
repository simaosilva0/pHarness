import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "@xyflow/react/dist/style.css";
import "./style.css";

// The data is written in the page by pharness (output/page.py, render_car).
const holder = document.getElementById("car-data");
const root = document.getElementById("car-root");
if (holder && root) createRoot(root).render(<App data={JSON.parse(holder.textContent)} />);
