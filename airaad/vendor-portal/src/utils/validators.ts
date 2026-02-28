const PK_PHONE_REGEX = /^(\+92|0)?3[0-9]{9}$/;

export function isValidPakistaniPhone(phone: string): boolean {
  return PK_PHONE_REGEX.test(phone.replace(/\s|-/g, ''));
}

export function isValidOTP(otp: string): boolean {
  return /^\d{6}$/.test(otp);
}

export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

export function isNotEmpty(value: string): boolean {
  return value.trim().length > 0;
}

export function isValidPercentage(value: number): boolean {
  return value >= 1 && value <= 100;
}

export function isValidDiscountValue(type: string, value: number): boolean {
  if (type === 'BOGO') return true;
  if (type === 'PERCENTAGE') return value >= 1 && value <= 100;
  return value >= 1;
}

export function isValidDateRange(start: string, end: string): boolean {
  if (!start || !end) return false;
  return new Date(end) > new Date(start);
}
