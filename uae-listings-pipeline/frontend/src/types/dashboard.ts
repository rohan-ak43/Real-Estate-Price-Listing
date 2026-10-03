/* ------------------------------------------------------------------ */
/*  TypeScript types for all API responses                            */
/* ------------------------------------------------------------------ */

export interface MarketOptions {
  empty: boolean;
  cities: string[];
  propertyTypes: string[];
  purposes: string[];
}

export interface MarketSummary {
  listings: number;
  medianPrice: number | null;
  averagePricePerSqft: number | null;
  communities: number;
}

export interface CommunityPrice {
  community: string;
  avg_price_per_sqft: number;
}

export interface PropertyTypeCount {
  property_type: string;
  listings: number;
}

export interface PriceTrend {
  year_month: string;
  avg_price_per_sqft: number;
}

export interface PriceChange {
  listing_id: string;
  community: string;
  property_type: string;
  old_price: number;
  new_price: number;
  change_pct: number;
  changed_at: string;
}

export interface PipelineRun {
  run_id: number;
  batch_id: number;
  started_at: string;
  finished_at: string;
  rows_raw: number;
  rows_staged: number;
  rows_rejected: number;
  rows_dup_removed: number;
  fact_inserted: number;
  fact_updated: number;
  status: string;
}

export interface DataQualityResult {
  check_name: string;
  severity: string;
  passed: boolean;
  detail: string;
  run_id: number;
}

export interface RejectedRow {
  reject_reason: string;
  rows: number;
}
