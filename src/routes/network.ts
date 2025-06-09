class NetworkInfo {
  static readonly URL: string =
    import.meta.env.VITE_ENV === "DEV"
      ? import.meta.env.VITE_API_URL
      : import.meta.env.VITE_API_URL_PROD;
}

class HTTPMethod {
  static readonly GET: string = "get";
  static readonly POST: string = "post";
  static readonly PUT: string = "put";
  static readonly PATCH: string = "patch";
  static readonly DELETE: string = "delete";
}

class AuthURL {
  static readonly SIGNUP: string = "/register/";
  static readonly LOGIN: string = "/login/"; 
  static readonly REFRESH_TOKEN: string = "/refresh"; 
  static readonly LOGOUT: string = "/logout"; 
  static readonly FORGOT_PASS: string = "/forgetPassword";
}

class PostLoginURL {
  static readonly getUser: string = "/user-details";
  static readonly examListing: string = "/exam-listing";
  
}

export { NetworkInfo, AuthURL, PostLoginURL, HTTPMethod };
