export interface AddressParts {
  address1?: string | null;
  address2?: string | null;
  city?: string | null;
  state?: string | null;
  zip?: string | null;
  country?: string | null;
}

const US_COUNTRY_ALIASES = new Set([
  "",
  "US",
  "USA",
  "UNITED STATES",
  "UNITED STATES OF AMERICA",
]);

const clean = (value: unknown): string => String(value ?? "").trim();

const isUsCountry = (country: unknown): boolean =>
  US_COUNTRY_ALIASES.has(clean(country).toUpperCase());

/**
 * TODO(address-i18n): Replace this stub with country-aware international formatting.
 */
function formatInternationalAddressStub(parts: AddressParts): string {
  return [
    clean(parts.address1),
    clean(parts.address2),
    [clean(parts.city), clean(parts.state), clean(parts.zip)]
      .filter(Boolean)
      .join(", "),
    clean(parts.country),
  ]
    .filter(Boolean)
    .join(", ");
}

/**
 * Standard formatter used to denormalize address fields into address_full.
 */
export function formatAddressFull(parts: AddressParts): string {
  const country = clean(parts.country);

  if (!isUsCountry(country)) {
    return formatInternationalAddressStub(parts);
  }

  const line1 = [clean(parts.address1), clean(parts.address2)]
    .filter(Boolean)
    .join(", ");
  const cityStateZip = [
    clean(parts.city),
    [clean(parts.state), clean(parts.zip)].filter(Boolean).join(" "),
  ]
    .filter(Boolean)
    .join(", ");

  return [line1, cityStateZip].filter(Boolean).join(", ");
}
