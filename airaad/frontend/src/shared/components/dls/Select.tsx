import { forwardRef, useState, useRef, useEffect, useCallback } from 'react';
import { AlertCircle, ChevronDown, Search, Check } from 'lucide-react';
import styles from './Input.module.css';
import selectStyles from './Select.module.css';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'id' | 'required' | 'disabled'> {
  label: string;
  options: SelectOption[];
  error?: string | undefined;
  hint?: string | undefined;
  required?: boolean | undefined;
  disabled?: boolean | undefined;
  id: string;
  placeholder?: string | undefined;
}

const SEARCHABLE_THRESHOLD = 5;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, options, error, hint, required, disabled, id, placeholder, className, value, onChange, ...rest },
  ref,
) {
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy = [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(' ') || undefined;
  const isSearchable = options.length > SEARCHABLE_THRESHOLD;

  if (!isSearchable) {
    return (
      <div className={styles.field}>
        <label htmlFor={id} className={styles.label}>
          {label}
          {required && <span className={styles.required} aria-hidden="true"> *</span>}
        </label>
        <select
          ref={ref}
          id={id}
          required={required}
          disabled={disabled}
          aria-describedby={describedBy}
          aria-invalid={error ? 'true' : undefined}
          className={[selectStyles.select, error ? styles.hasError : '', className].filter(Boolean).join(' ')}
          value={value}
          onChange={onChange}
          {...rest}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {hint && !error && (
          <span id={hintId} className={styles.hint}>
            {hint}
          </span>
        )}
        {error && (
          <span id={errorId} className={styles.error} role="alert">
            <AlertCircle size={12} strokeWidth={1.5} aria-hidden="true" />
            {error}
          </span>
        )}
      </div>
    );
  }

  return (
    <SearchableSelect
      ref={ref}
      id={id}
      label={label}
      options={options}
      placeholder={placeholder}
      required={required}
      disabled={disabled}
      error={error}
      hint={hint}
      className={className}
      value={value}
      onChange={onChange}
      describedBy={describedBy}
      {...rest}
    />
  );
});

/* ── Searchable variant (options > 5) ── */

interface SearchableSelectInternalProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'id' | 'required' | 'disabled'> {
  id: string;
  label: string;
  options: SelectOption[];
  placeholder?: string | undefined;
  required?: boolean | undefined;
  disabled?: boolean | undefined;
  error?: string | undefined;
  hint?: string | undefined;
  describedBy?: string | undefined;
}

const SearchableSelect = forwardRef<HTMLSelectElement, SearchableSelectInternalProps>(function SearchableSelect(
  { id, label, options, placeholder, required, disabled, error, hint, className, value, onChange, describedBy, ...rest },
  ref,
) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;

  const selectedLabel = options.find((o) => o.value === value)?.label;
  const filtered = search
    ? options.filter((o) => o.label.toLowerCase().includes(search.toLowerCase()))
    : options;

  const handleSelect = useCallback(
    (optValue: string) => {
      if (onChange) {
        const syntheticEvent = {
          target: { value: optValue, name: rest.name ?? '' },
          currentTarget: { value: optValue, name: rest.name ?? '' },
        } as React.ChangeEvent<HTMLSelectElement>;
        onChange(syntheticEvent);
      }
      setOpen(false);
      setSearch('');
      setHighlightIndex(-1);
    },
    [onChange, rest.name],
  );

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch('');
        setHighlightIndex(-1);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [open]);

  useEffect(() => {
    if (open && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [open]);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setHighlightIndex(-1);
  }, []);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        setOpen(true);
      }
      return;
    }
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightIndex((prev) => (prev < filtered.length - 1 ? prev + 1 : 0));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightIndex((prev) => (prev > 0 ? prev - 1 : filtered.length - 1));
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightIndex >= 0 && filtered[highlightIndex]) {
          handleSelect(filtered[highlightIndex].value);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setOpen(false);
        setSearch('');
        setHighlightIndex(-1);
        break;
    }
  }

  useEffect(() => {
    if (highlightIndex >= 0 && listRef.current) {
      const el = listRef.current.children[highlightIndex] as HTMLElement | undefined;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [highlightIndex]);

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
        {required && <span className={styles.required} aria-hidden="true"> *</span>}
      </label>

      {/* Hidden native select for form/ref compatibility */}
      <select
        ref={ref}
        id={id}
        required={required}
        disabled={disabled}
        aria-hidden="true"
        tabIndex={-1}
        className={selectStyles.hiddenSelect}
        value={value}
        onChange={onChange}
        {...rest}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>

      {/* Custom searchable trigger */}
      <div ref={wrapperRef} className={selectStyles.searchableWrapper} onKeyDown={handleKeyDown}>
        <button
          type="button"
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-describedby={describedBy}
          aria-invalid={error ? 'true' : undefined}
          className={[
            selectStyles.trigger,
            error ? styles.hasError : '',
            disabled ? selectStyles.triggerDisabled : '',
            className,
          ].filter(Boolean).join(' ')}
          onClick={() => !disabled && setOpen((v) => !v)}
        >
          <span className={selectedLabel ? selectStyles.triggerText : selectStyles.triggerPlaceholder}>
            {selectedLabel ?? placeholder ?? 'Select…'}
          </span>
          <ChevronDown
            size={16}
            strokeWidth={1.5}
            className={[selectStyles.triggerIcon, open ? selectStyles.triggerIconOpen : ''].filter(Boolean).join(' ')}
            aria-hidden="true"
          />
        </button>

        {open && (
          <div className={selectStyles.dropdown} role="presentation">
            <div className={selectStyles.searchRow}>
              <Search size={14} strokeWidth={1.5} className={selectStyles.searchIcon} aria-hidden="true" />
              <input
                ref={searchInputRef}
                type="text"
                className={selectStyles.searchInput}
                placeholder="Search…"
                value={search}
                onChange={handleSearchChange}
                aria-label={`Search ${label}`}
                autoComplete="off"
              />
            </div>
            <ul ref={listRef} className={selectStyles.optionsList} role="listbox" aria-label={label}>
              {filtered.length === 0 ? (
                <li className={selectStyles.noResults} role="option" aria-selected={false}>No results</li>
              ) : (
                filtered.map((opt, i) => {
                  const isSelected = opt.value === value;
                  const isHighlighted = i === highlightIndex;
                  return (
                    <li
                      key={opt.value}
                      role="option"
                      aria-selected={isSelected}
                      className={[
                        selectStyles.option,
                        isSelected ? selectStyles.optionSelected : '',
                        isHighlighted ? selectStyles.optionHighlighted : '',
                      ].filter(Boolean).join(' ')}
                      onMouseEnter={() => setHighlightIndex(i)}
                      onClick={() => handleSelect(opt.value)}
                    >
                      <span>{opt.label}</span>
                      {isSelected && <Check size={14} strokeWidth={2} className={selectStyles.checkIcon} aria-hidden="true" />}
                    </li>
                  );
                })
              )}
            </ul>
          </div>
        )}
      </div>

      {hint && !error && (
        <span id={hintId} className={styles.hint}>
          {hint}
        </span>
      )}
      {error && (
        <span id={errorId} className={styles.error} role="alert">
          <AlertCircle size={12} strokeWidth={1.5} aria-hidden="true" />
          {error}
        </span>
      )}
    </div>
  );
});
