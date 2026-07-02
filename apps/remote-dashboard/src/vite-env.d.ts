/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * API base path or absolute URL for the Miori core-api. Defaults to "/api".
   * The host origin comes from the connection state; this is appended to it
   * unless an absolute http(s) URL is supplied. Health is probed at the origin
   * root (`/health`), independent of this value.
   */
  readonly VITE_MIORI_API?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
