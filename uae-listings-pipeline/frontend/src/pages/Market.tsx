import { useState, useEffect, useCallback } from 'react';
import FilterPanel from '../components/FilterPanel';
import KPICard from '../components/KPICard';
import CommunityPriceChart from '../components/CommunityPriceChart';
import PropertyTypeChart from '../components/PropertyTypeChart';
import PriceTrendChart from '../components/PriceTrendChart';
import PriceChangesTable from '../components/PriceChangesTable';
import {
  fetchMarketOptions,
  fetchMarketSummary,
  fetchCommunityPrices,
  fetchPropertyTypes,
  fetchPriceTrend,
  fetchPriceChanges,
} from '../services/api';
import type {
  MarketOptions,
  MarketSummary,
  CommunityPrice,
  PropertyTypeCount,
  PriceTrend,
  PriceChange,
} from '../types/dashboard';

function fmtKpi(val: number | null, prefix = ''): string {
  if (val == null || isNaN(val)) return '-';
  return `${prefix}${Math.round(val).toLocaleString()}`;
}

export default function Market() {
  // Filter options from DB
  const [options, setOptions] = useState<MarketOptions | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);

  // Selected filters
  const [purpose, setPurpose] = useState('');
  const [cities, setCities] = useState<string[]>([]);
  const [propertyTypes, setPropertyTypes] = useState<string[]>([]);

  // Dashboard data
  const [summary, setSummary] = useState<MarketSummary | null>(null);
  const [communityData, setCommunityData] = useState<CommunityPrice[]>([]);
  const [propTypeData, setPropTypeData] = useState<PropertyTypeCount[]>([]);
  const [trendData, setTrendData] = useState<PriceTrend[]>([]);
  const [priceChanges, setPriceChanges] = useState<PriceChange[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [priceChangesLoading, setPriceChangesLoading] = useState(true);

  // 1. Load filter options on mount
  useEffect(() => {
    fetchMarketOptions()
      .then((opts) => {
        setOptions(opts);
        if (!opts.empty) {
          setPurpose(opts.purposes[0]); // Sale first (sorted reverse)
          setCities(opts.cities);
          setPropertyTypes(opts.propertyTypes);
        }
      })
      .catch((err) => setOptionsError(err.message));
  }, []);

  // 2. Load filtered data whenever filters change
  const loadData = useCallback(async () => {
    if (!purpose || cities.length === 0 || propertyTypes.length === 0) return;
    setDataLoading(true);
    try {
      const [s, cp, pt, tr] = await Promise.all([
        fetchMarketSummary(purpose, cities, propertyTypes),
        fetchCommunityPrices(purpose, cities, propertyTypes),
        fetchPropertyTypes(purpose, cities, propertyTypes),
        fetchPriceTrend(purpose, cities, propertyTypes),
      ]);
      setSummary(s);
      setCommunityData(cp);
      setPropTypeData(pt);
      setTrendData(tr);
    } catch {
      // individual fetch errors are acceptable — show empty charts
    } finally {
      setDataLoading(false);
    }
  }, [purpose, cities, propertyTypes]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 3. Price changes (unfiltered, only loaded once)
  useEffect(() => {
    setPriceChangesLoading(true);
    fetchPriceChanges()
      .then(setPriceChanges)
      .catch(() => setPriceChanges([]))
      .finally(() => setPriceChangesLoading(false));
  }, []);

  // --- Render states ---
  if (optionsError) {
    return (
      <div className="error-banner">
        <h2>Warehouse unavailable</h2>
        <p>The analytics warehouse could not be found. Run the data pipeline / demo setup and try again.</p>
      </div>
    );
  }

  if (!options) {
    return <div className="loading"><div className="spinner" /> Loading market data…</div>;
  }

  if (options.empty) {
    return (
      <div className="error-banner">
        <h2>Warehouse is empty</h2>
        <p>Run the pipeline to populate the warehouse.</p>
      </div>
    );
  }

  return (
    <>
      <FilterPanel
        purposes={options.purposes}
        cities={options.cities}
        propertyTypes={options.propertyTypes}
        selectedPurpose={purpose}
        selectedCities={cities}
        selectedPropertyTypes={propertyTypes}
        onPurposeChange={setPurpose}
        onCitiesChange={setCities}
        onPropertyTypesChange={setPropertyTypes}
      />

      {/* KPI cards */}
      {dataLoading ? (
        <div className="kpi-row">
          {[1, 2, 3, 4].map((i) => <div key={i} className="skeleton skeleton-kpi" />)}
        </div>
      ) : (
        <div className="kpi-row">
          <KPICard label="Listings" value={summary ? summary.listings.toLocaleString() : '-'} />
          <KPICard label="Median price (AED)" value={fmtKpi(summary?.medianPrice ?? null, 'AED ')} />
          <KPICard label="Avg AED / sqft" value={fmtKpi(summary?.averagePricePerSqft ?? null)} />
          <KPICard label="Communities" value={summary ? summary.communities.toLocaleString() : '-'} />
        </div>
      )}

      {/* Charts */}
      {dataLoading ? (
        <div className="chart-grid">
          <div className="skeleton skeleton-chart" />
          <div className="skeleton skeleton-chart" />
          <div className="skeleton skeleton-chart chart-full" />
        </div>
      ) : (
        <div className="chart-grid">
          <CommunityPriceChart data={communityData} />
          <PropertyTypeChart data={propTypeData} />
          <PriceTrendChart data={trendData} />
        </div>
      )}

      {/* Price changes table */}
      <PriceChangesTable data={priceChanges} loading={priceChangesLoading} />
    </>
  );
}
