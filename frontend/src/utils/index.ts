/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// Utility functions salvaged from Vue2020 utils.js

export const formatPhoneNum = (phoneNumberString: string): string | null => {
  const cleaned = ('' + phoneNumberString).replace(/\D/g, '');
  const match = cleaned.match(/^(\d{3})(\d{3})(\d{4})$/);
  if (match) {
    return '(' + match[1] + ') ' + match[2] + '-' + match[3];
  }
  return null;
};

type PhoneLike = {
  phone?: string | null;
  phoneCell?: string | null;
  [key: string]: unknown;
};

export const formatPhoneNums = <T extends PhoneLike>(rows: T[]): T[] => {
  rows.forEach((element) => {
    if (typeof element.phone === 'string' && element.phone) {
      element.phone = formatPhoneNum(element.phone);
    }
    if (typeof element.phoneCell === 'string' && element.phoneCell) {
      element.phoneCell = formatPhoneNum(element.phoneCell);
    }
  });
  return rows;
};

export const formatDate = (d: Date): string => {
  let month = '' + (d.getMonth() + 1);
  let day = '' + d.getDate();
  const year = d.getFullYear();

  if (month.length < 2) month = '0' + month;
  if (day.length < 2) day = '0' + day;

  return [year, month, day].join('-');
};

export const getDateAsStr = (d: Date): string => {
  let month = '' + (d.getMonth() + 1);
  let day = '' + d.getDate();
  const year = d.getFullYear();

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

// Auth state (setLoggedIn/isLoggedIn/setLoggedOut) REMOVED 2026-08-14.
// Auth is owned by Redux authSlice + userProfile localStorage (managed by
// api/auth.ts and AuthInitializer.tsx). The old "loggedIn" key was never consumed.
//
type LabeledValue = {
  value: string;
  label: string;
};

export const convertToArray = (src?: LabeledValue[] | null): [string, string][] => {
  const target: [string, string][] = [];
  if (typeof src === 'undefined') {
    console.log('Variable is undefined');
    return target;
  }
  if (src == null) {
    return target;
  }
  src.forEach(({ value, label }) => {
    target.push([value, label]);
  });
  return target;
};

// Data Set Identification exports
export {
  getFrontendDataSet,
  fetchBackendSystemInfo,
  validateDataSetMatch,
  logDataSetInfo,
} from './dataSetInfo';
export type { DataSetInfo, SystemInfo } from './dataSetInfo';