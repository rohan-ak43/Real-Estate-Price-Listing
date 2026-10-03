import { useState, useRef, useEffect } from 'react';

interface MultiSelectProps {
  id: string;
  label: string;
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

export default function MultiSelect({ id, label, options, selected, onChange }: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const toggle = (value: string) => {
    const next = selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value];
    onChange(next);
  };

  const summary =
    selected.length === options.length
      ? 'All selected'
      : selected.length === 0
        ? 'None'
        : selected.length <= 2
          ? selected.join(', ')
          : `${selected.length} selected`;

  return (
    <div className="filter-group multi-select" ref={ref}>
      <label htmlFor={id}>{label}</label>
      <div id={id} className="multi-select-trigger" onClick={() => setOpen(!open)}>
        <span>{summary}</span>
        <span className={`chevron ${open ? 'open' : ''}`}>▼</span>
      </div>
      {open && (
        <div className="multi-select-dropdown">
          {options.map((opt) => (
            <label key={opt} className="multi-select-item">
              <input type="checkbox" checked={selected.includes(opt)} onChange={() => toggle(opt)} />
              {opt}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
