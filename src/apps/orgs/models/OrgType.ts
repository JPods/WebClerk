// TypeScript enum for OrgType, matching Django model
export enum OrgType {
  CUSTOMER = "customer",
  VENDOR = "vendor",
  REP = "rep",
  EMPLOYEE = "employee",
  MANUFACTURER = "manufacturer",
  OTHER = "other"
}

// TypeScript type for OrgType values (string union)
export type OrgTypeValue =
  | OrgType.CUSTOMER
  | OrgType.VENDOR
  | OrgType.REP
  | OrgType.EMPLOYEE
  | OrgType.MANUFACTURER
  | OrgType.OTHER;
