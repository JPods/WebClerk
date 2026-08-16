/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// Utility functions extracted and translated from vue2020

/**
 * Formats a phone number string into (XXX) XXX-XXXX format
 * @param phoneNumberString - The phone number to format
 * @returns Formatted phone number or null if invalid
 */
export function formatPhoneNum(phoneNumberString: string): string | null {
  const cleaned = ('' + phoneNumberString).replace(/\D/g, '');
  const match = cleaned.match(/^(\d{3})(\d{3})(\d{4})$/);
  if (match) {
    return '(' + match[1] + ') ' + match[2] + '-' + match[3];
  }
  return null;
}

/**
 * Formats phone numbers in an array of objects
 * @param rows - Array of objects that may contain phone or phoneCell properties
 * @returns The modified array with formatted phone numbers
 */
interface PhoneRecord {
  phone?: string | null;
  phoneCell?: string | null;
  [key: string]: unknown;
}

export function formatPhoneNums<T extends PhoneRecord>(rows: T[]): T[] {
  rows.forEach((element) => {
    if (typeof element.phone === 'string' && element.phone) {
      element.phone = formatPhoneNum(element.phone);
    }
    if (typeof element.phoneCell === 'string' && element.phoneCell) {
      element.phoneCell = formatPhoneNum(element.phoneCell);
    }
  });
  return rows;
}

/**
 * Formats a date object into YYYY-MM-DD format
 * @param d - Date object
 * @returns Formatted date string
 */
export function formatDate(d: Date): string {
  let month = '' + (d.getMonth() + 1);
  let day = '' + d.getDate();
  const year = d.getFullYear();

  if (month.length < 2) month = '0' + month;
  if (day.length < 2) day = '0' + day;

  return [year, month, day].join('-');
}

/**
 * Formats a date object into MM/DD/YYYY format
 * @param d - Date object
 * @returns Formatted date string
 */
export function getDateAsStr(d: Date): string {
  let month = '' + (d.getMonth() + 1);
  let day = '' + d.getDate();
  const year = d.getFullYear();

  if (month.length < 2) month = '0' + month;
  if (day.length < 2) day = '0' + day;

  return [month, day, year].join('/');
}

/**
 * Validates an email address
 * @param v - Email string to validate
 * @returns True if valid or empty, false otherwise
 */
export function emailValidator(v: string | null): boolean {
  if (v == null || v === "") {
    return true;
  }
  const re = /^(?!['`])\s*[-+.'\w]+@[-.\w]+\.[-.\w]+\s*$/;
  return re.test(String(v).toLowerCase());
}

/**
 * Converts an array of objects with value/label to array of [value, label] pairs
 * @param src - Source array
 * @returns Converted array
 */
type LabeledValue = {
  value: string;
  label: string;
};

export function convertToArray(src?: LabeledValue[] | null): [string, string][] {
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
}

// Local storage utilities
//
// Auth state (setLoggedIn/isLoggedIn/setLoggedOut) REMOVED 2026-08-14.
