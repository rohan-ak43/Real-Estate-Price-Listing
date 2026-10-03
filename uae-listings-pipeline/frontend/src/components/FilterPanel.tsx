import MultiSelect from './MultiSelect';

interface FilterPanelProps {
  purposes: string[];
  cities: string[];
  propertyTypes: string[];
  selectedPurpose: string;
  selectedCities: string[];
  selectedPropertyTypes: string[];
  onPurposeChange: (purpose: string) => void;
  onCitiesChange: (cities: string[]) => void;
  onPropertyTypesChange: (types: string[]) => void;
}

export default function FilterPanel({
  purposes,
  cities,
  propertyTypes,
  selectedPurpose,
  selectedCities,
  selectedPropertyTypes,
  onPurposeChange,
  onCitiesChange,
  onPropertyTypesChange,
}: FilterPanelProps) {
  return (
    <div className="filter-panel">
      {/* Purpose radio */}
      <div className="filter-group">
        <label>Purpose</label>
        <div className="radio-group">
          {purposes.map((p) => (
            <label key={p} className="radio-option">
              <input
                type="radio"
                name="purpose"
                value={p}
                checked={selectedPurpose === p}
                onChange={() => onPurposeChange(p)}
              />
              {p}
            </label>
          ))}
        </div>
      </div>

      {/* City multi-select */}
      <MultiSelect
        id="filter-city"
        label="City"
        options={cities}
        selected={selectedCities}
        onChange={onCitiesChange}
      />

      {/* Property type multi-select */}
      <MultiSelect
        id="filter-property-type"
        label="Property Type"
        options={propertyTypes}
        selected={selectedPropertyTypes}
        onChange={onPropertyTypesChange}
      />

      <p className="filter-note">Price per sqft is AED per sqft (annual rent for Rent).</p>
    </div>
  );
}
