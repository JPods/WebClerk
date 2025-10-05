// Network information for different base URLs
// VITE_API_URL / VITE_API_URL_PROD -> Protected (post-login) API
// VITE_AUTH_API_URL / VITE_AUTH_API_URL_PROD -> Auth server (login, refresh, signup)
// Normalize env flags that may mistakenly include quotes in .env files
const ENV = String(import.meta.env.VITE_ENV || 'DEV').replace(/['"]/g, '');

const withFallback = (value: string | undefined, fallback = ""): string =>
  typeof value === "string" && value.trim() ? value : fallback;

class NetworkInfo {
  static readonly API_URL: string =
    ENV === "DEV"
      ? withFallback(import.meta.env.VITE_API_URL)
      : withFallback(import.meta.env.VITE_API_URL_PROD);

  static readonly AUTH_URL: string =
    ENV === "DEV"
      ? withFallback(import.meta.env.VITE_AUTH_API_URL, withFallback(import.meta.env.VITE_API_URL)) // fallback
      : withFallback(import.meta.env.VITE_AUTH_API_URL_PROD, withFallback(import.meta.env.VITE_API_URL_PROD));

  static readonly NOTION_URL: string =
    ENV === "DEV"
      ? withFallback(import.meta.env.VITE_NOTION_API_URL, withFallback(import.meta.env.VITE_API_URL))
      : withFallback(import.meta.env.VITE_NOTION_API_URL_PROD, withFallback(import.meta.env.VITE_API_URL_PROD));
}

class HTTPMethod {
  static readonly GET: string = "get";
  static readonly POST: string = "post";
  static readonly PUT: string = "put";
  static readonly PATCH: string = "patch";
  static readonly DELETE: string = "delete";
}

class AuthURL {
  // These paths assume AUTH_URL points to the backend ROOT (no trailing /api)
  static readonly SIGNUP: string = "/api/auth/signup/";
  static readonly LOGIN: string = "/api/auth/login/"; 
  static readonly REFRESH_TOKEN: string = "/api/token/refresh/"; 
  static readonly LOGOUT: string = "/api/auth/logout/"; 
  static readonly FORGOT_PASS: string = "/forgetPassword";
  static readonly verifyEmail: string = "/verify-email/"; 
}

class PostLoginURL {
  static readonly getUser: string = "/profile/"; 
  static readonly addPhone: string = "/communications/phones/"; 
  static readonly addEmail: string = "/communications/emails/";
  static readonly addAddress: string = "/communications/addresses/";
  static readonly addDomains: string = "/communications/domains/";
  static readonly addActions: string = "/actions/";
  static readonly updateProfile: string = "/profile/";   

  static readonly allTypes: string = "/wcapi/get/?"; 
    
}

class IntegrationURL {
  static readonly notionProgress: string = "/integrations/notion/progress/";
  static readonly notionSync: string = "/integrations/notion/sync/";
  static readonly notionLogin: string = "/integrations/notion/login/";
  static readonly notionStatus: string = "/integrations/notion/status/";
}

export { NetworkInfo, AuthURL, PostLoginURL, IntegrationURL, HTTPMethod };
