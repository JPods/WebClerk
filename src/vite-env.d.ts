/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_ENV?: string;
	readonly VITE_API_URL?: string;
	readonly VITE_API_URL_PROD?: string;
	readonly VITE_AUTH_API_URL?: string;
	readonly VITE_AUTH_API_URL_PROD?: string;
	readonly VITE_NOTION_API_URL?: string;
	readonly VITE_NOTION_API_URL_PROD?: string;
	readonly VITE_NOTION_CLIENT_ID?: string;
	readonly VITE_NOTION_REDIRECT_URI?: string;
	readonly VITE_NOTION_SCOPE?: string;
	readonly VITE_NOTION_OAUTH_OWNER?: string;
	readonly VITE_PRINT_TEMPLATE_MARKER?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
