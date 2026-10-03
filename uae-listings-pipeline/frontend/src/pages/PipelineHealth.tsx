import { useState, useEffect } from 'react';
import PipelineRunsTable from '../components/PipelineRunsTable';
import DataQualityTable from '../components/DataQualityTable';
import RejectedRowsTable from '../components/RejectedRowsTable';
import { fetchPipelineRuns, fetchDataQuality, fetchRejectedRows } from '../services/api';
import type { PipelineRun, DataQualityResult, RejectedRow } from '../types/dashboard';

export default function PipelineHealth() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [dq, setDq] = useState<DataQualityResult[]>([]);
  const [rejected, setRejected] = useState<RejectedRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchPipelineRuns(), fetchDataQuality(), fetchRejectedRows()])
      .then(([r, d, j]) => {
        setRuns(r);
        setDq(d);
        setRejected(j);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (error) {
    return (
      <div className="error-banner">
        <h2>Warehouse unavailable</h2>
        <p>The analytics warehouse could not be found. Run the data pipeline / demo setup and try again.</p>
      </div>
    );
  }

  return (
    <>
      <PipelineRunsTable data={runs} loading={loading} />
      <DataQualityTable data={dq} loading={loading} />
      <RejectedRowsTable data={rejected} loading={loading} />
    </>
  );
}
