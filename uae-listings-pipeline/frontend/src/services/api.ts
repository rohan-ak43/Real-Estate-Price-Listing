/* ------------------------------------------------------------------ */
/*  API service — all calls to the FastAPI backend                    */
/* ------------------------------------------------------------------ */

import type {
  MarketOptions,
  MarketSummary,
  CommunityPrice,
  PropertyTypeCount,
  PriceTrend,
  PriceChange,
  PipelineRun,
  DataQualityResult,
  RejectedRow,
} from '../types/dashboard';

const BASE = '/api';

/** Build a query-string from the common market filter params. */
function marketParams(purpose: string, cities: string[], propertyTypes: string[]): string {
  const p = new URLSearchParams();
  p.set('purpose', purpose);
  cities.forEach((c) => p.append('cities', c));
  propertyTypes.forEach((t) => p.append('propertyTypes', t));
  return p.toString();
}

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `API error ${res.status}`);
  }
  return res.json();
}

/* ---------- Market ---------- */

export async function fetchMarketOptions(): Promise<MarketOptions> {
  return get<MarketOptions>(`${BASE}/market/options`);
}

export async function fetchMarketSummary(
  purpose: string,
  cities: string[],
  propertyTypes: string[],
): Promise<MarketSummary> {
  return get<MarketSummary>(`${BASE}/market/summary?${marketParams(purpose, cities, propertyTypes)}`);
}

export async function fetchCommunityPrices(
  purpose: string,
  cities: string[],
  propertyTypes: string[],
): Promise<CommunityPrice[]> {
  return get<CommunityPrice[]>(`${BASE}/market/community-prices?${marketParams(purpose, cities, propertyTypes)}`);
}

export async function fetchPropertyTypes(
  purpose: string,
  cities: string[],
  propertyTypes: string[],
): Promise<PropertyTypeCount[]> {
  return get<PropertyTypeCount[]>(`${BASE}/market/property-types?${marketParams(purpose, cities, propertyTypes)}`);
}

export async function fetchPriceTrend(
  purpose: string,
  cities: string[],
  propertyTypes: string[],
): Promise<PriceTrend[]> {
  return get<PriceTrend[]>(`${BASE}/market/price-trend?${marketParams(purpose, cities, propertyTypes)}`);
}

export async function fetchPriceChanges(): Promise<PriceChange[]> {
  return get<PriceChange[]>(`${BASE}/market/price-changes`);
}

/* ---------- Pipeline Health ---------- */

export async function fetchPipelineRuns(): Promise<PipelineRun[]> {
  return get<PipelineRun[]>(`${BASE}/health/pipeline-runs`);
}

export async function fetchDataQuality(): Promise<DataQualityResult[]> {
  return get<DataQualityResult[]>(`${BASE}/health/data-quality`);
}

export async function fetchRejectedRows(): Promise<RejectedRow[]> {
  return get<RejectedRow[]>(`${BASE}/health/rejected-rows`);
}
