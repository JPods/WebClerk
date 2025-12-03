// Utility functions salvaged from Vue2020 utils.js

export const formatPhoneNum = (phoneNumberString: string): string | null => {
  const cleaned = ('' + phoneNumberString).replace(/\D/g, '');
  const match = cleaned.match(/^(\d{3})(\d{3})(\d{4})$/);
  if (match) {
    return '(' + match[1] + ') ' + match[2] + '-' + match[3];
  }
  return null;
};

export const formatPhoneNums = (rows: any[]): any[] => {
  rows.forEach(element => {
    if (Object.prototype.hasOwnProperty.call(element, "phone") && element.phone) {
      element.phone = formatPhoneNum(element.phone);
    }
    if (Object.prototype.hasOwnProperty.call(element, "phoneCell") && element.phoneCell) {
      element.phoneCell = formatPhoneNum(element.phoneCell);
    }
  });
  return rows;
};

export const formatDate = (d: Date): string => {
  let month = '' + (d.getMonth() + 1);
  let day = '' + d.getDate();
  let year = d.getFullYear();

  if (month.length < 2) month = '0' + month;
  if (day.length < 2) day = '0' + day;

  return [year, month, day].join('-');
};

export const getDateAsStr = (d: Date): string => {
  let month = '' + (d.getMonth() + 1);
  let day = '' + d.getDate();
  let year = d.getFullYear();

  if (month.length < 2) month = '0' + month;
  if (day.length < 2) day = '0' + day;

  return [month, day, year].join('/');
};

export const emailValidator = (v: string | null | undefined): boolean => {
  if (v == null || v === "") {
    return true;
  }
  const re = /^(?!['`])\s*[-+.'\w]+@[-.\w]+\.[-.\w]+\s*$/;
  return re.test(String(v).toLowerCase());
};

// Local storage helpers for current entity IDs
export const getCurrentCustomerId = (): string | null => {
  return window.localStorage.getItem("currentCustomerId");
};

export const setCurrentCustomerId = (currentCustomerId: string): void => {
  window.localStorage.setItem("currentCustomerId", currentCustomerId);
};

export const getCurrentProposalId = (): string | null => {
  return window.localStorage.getItem("currenProposalId");
};

export const setCurrentProposalId = (currenProposalId: string): void => {
  window.localStorage.setItem("currenProposalId", currenProposalId);
};

export const getCurrentOrderId = (): string | null => {
  return window.localStorage.getItem("currenOrderId");
};

export const setCurrentOrderId = (currenOrderId: string): void => {
  window.localStorage.setItem("currenOrderId", currenOrderId);
};

export const getCurrentInvoiceId = (): string | null => {
  return window.localStorage.getItem("currentInvoiceId");
};

export const setCurrentInvoiceId = (currentInvoiceId: string): void => {
  window.localStorage.setItem("currentInvoiceId", currentInvoiceId);
};

// Login status
export const setLoggedIn = (): void => {
  window.localStorage.setItem("loggedIn", "true");
};

export const setLoggedOut = (): void => {
  window.localStorage.setItem("loggedIn", "false");
};

export const isLoggedIn = (): boolean => {
  return window.localStorage.getItem("loggedIn") === "true";
};

// Search persistence
export const setLastSearch = (lastSearch: any): void => {
  window.localStorage.setItem("lastSearch", JSON.stringify(lastSearch));
};

export const getLastSearch = (): any => {
  const item = window.localStorage.getItem("lastSearch");
  return item ? JSON.parse(item) : null;
};

export const convertToArray = (src: any[]): [string, string][] => {
  const target: [string, string][] = [];
  if (typeof src === 'undefined') {
    console.log('Variable is undefined');
    return target;
  }
  if (src == null) {
    return target;
  }

  src.forEach(element => {
    target.push([element.value, element.label]);
  });
  return target;
};