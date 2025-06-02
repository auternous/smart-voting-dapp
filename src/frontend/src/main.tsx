import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

declare global {
  interface ImportMetaEnv {
    readonly VITE_BACKEND_API_URL: string;
    readonly VITE_POLL_SYSTEM_ADDRESS: string;
    readonly VITE_POLL_TOKEN_ADDRESS: string;
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}