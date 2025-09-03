// Network information for different base URLs
// VITE_API_URL / VITE_API_URL_PROD -> Protected (post-login) API
// VITE_AUTH_API_URL / VITE_AUTH_API_URL_PROD -> Auth server (login, refresh, signup)
class NetworkInfo {
  static readonly API_URL: string =
    import.meta.env.VITE_ENV === "DEV"
      ? import.meta.env.VITE_API_URL
      : import.meta.env.VITE_API_URL_PROD;

  static readonly AUTH_URL: string =
    import.meta.env.VITE_ENV === "DEV"
      ? (import.meta.env.VITE_AUTH_API_URL || import.meta.env.VITE_API_URL) // fallback
      : (import.meta.env.VITE_AUTH_API_URL_PROD || import.meta.env.VITE_API_URL_PROD);
}

class HTTPMethod {
  static readonly GET: string = "get";
  static readonly POST: string = "post";
  static readonly PUT: string = "put";
  static readonly PATCH: string = "patch";
  static readonly DELETE: string = "delete";
}

class AuthURL {
  static readonly SIGNUP: string = "/signup/";
  static readonly LOGIN: string = "/auth/login/"; 
  static readonly REFRESH_TOKEN: string = "/api/token/"; 
  static readonly LOGOUT: string = "/logout"; 
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

  static readonly allTypes: string = "get/?"; 
    
}

export { NetworkInfo, AuthURL, PostLoginURL, HTTPMethod };
