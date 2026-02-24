/**
 * Central utility functions for formatting text displayed to users.
 * Converts technical/programmatic values to human-readable format.
 */

// Role name mappings
const ROLE_MAPPINGS: Record<string, string> = {
  SUPER_ADMIN: 'Super Admin',
  CITY_MANAGER: 'City Manager',
  DATA_ENTRY: 'Data Entry',
  QA_REVIEWER: 'QA Reviewer',
  FIELD_AGENT: 'Field Agent',
  ANALYST: 'Analyst',
  SUPPORT: 'Support',
  OPERATIONS_MANAGER: 'Operations Manager',
  CONTENT_MODERATOR: 'Content Moderator',
  DATA_QUALITY_ANALYST: 'Data Quality Analyst',
  ANALYTICS_OBSERVER: 'Analytics Observer',
};

// Status value mappings
const STATUS_MAPPINGS: Record<string, string> = {
  NEEDS_REVIEW: 'Needs Review',
  IN_PROGRESS: 'In Progress',
  QC_PENDING: 'QC Pending',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  DONE: 'Done',
  FAILED: 'Failed',
  PENDING: 'Pending',
  ACTIVE: 'Active',
  INACTIVE: 'Inactive',
  SOFT_DELETED: 'Deleted',
};

/**
 * Formats role names to human-readable format.
 * @param role - The role string to format
 * @returns Human-readable role name
 */
export function formatRole(role: string): string {
  if (!role || typeof role !== 'string') return '';
  return ROLE_MAPPINGS[role] || formatLabel(role);
}

/**
 * Formats status values to human-readable format.
 * @param status - The status string to format
 * @returns Human-readable status value
 */
export function formatStatus(status: string): string {
  if (!status || typeof status !== 'string') return '';
  return STATUS_MAPPINGS[status] || formatLabel(status);
}

/**
 * Converts snake_case, SCREAMING_CASE, or camelCase to Title Case.
 * @param key - The string to convert
 * @returns Title Case string with spaces
 */
export function formatLabel(key: string): string {
  if (!key || typeof key !== 'string') return '';
  
  // Handle SCREAMING_CASE
  if (key === key.toUpperCase()) {
    return key
      .toLowerCase()
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  }
  
  // Handle snake_case
  if (key.includes('_')) {
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  }
  
  // Handle camelCase
  return key
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, str => str.toUpperCase())
    .trim();
}

/**
 * Formats boolean values to human-readable format.
 * @param value - The boolean value
 * @returns "Yes" or "No"
 */
export function formatBoolean(value: boolean): string {
  return value ? 'Yes' : 'No';
}

/**
 * Formats active/inactive boolean values to human-readable format.
 * @param value - The boolean value
 * @returns "Active" or "Inactive"
 */
export function formatActiveStatus(value: boolean): string {
  return value ? 'Active' : 'Inactive';
}

/**
 * Formats nullable values to human-readable format.
 * @param value - The value to format
 * @returns Formatted string or em dash for null/undefined
 */
export function formatNullable(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  
  if (typeof value === 'boolean') {
    return formatBoolean(value);
  }
  
  if (typeof value === 'string') {
    return value;
  }
  
  if (typeof value === 'number') {
    return value.toLocaleString();
  }
  
  if (value instanceof Date) {
    return value.toLocaleString();
  }
  
  return String(value);
}

/**
 * Formats a date to human-readable format.
 * @param date - The date to format
 * @returns Formatted date string
 */
export function formatDate(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return dateObj.toLocaleDateString();
}

/**
 * Formats a date with time to human-readable format.
 * @param date - The date to format
 * @returns Formatted date-time string
 */
export function formatDateTime(date: string | Date): string {
  if (!date) return '—';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  // Check if the date is valid
  if (isNaN(dateObj.getTime())) {
    return '—';
  }
  
  return dateObj.toLocaleString();
}
