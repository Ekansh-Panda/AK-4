/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MIORI_API?: string;
  readonly VITE_MIORI_WS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
