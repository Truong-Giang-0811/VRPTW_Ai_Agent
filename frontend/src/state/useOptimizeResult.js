import { useState } from "react";
import { optimizeRoutes, optimizeComparison } from "../api/optimizeApi";

export function useOptimizeResult() {
  const [result, setResult] = useState(null);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function runOptimize(payload) {
    setLoading(true);
    setError(null);
    setComparisonResult(null);
    try {
      const data = await optimizeRoutes(payload);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function runComparison(payload) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await optimizeComparison(payload);
      setComparisonResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function clearResult() {
    setResult(null);
    setComparisonResult(null);
    setError(null);
  }

  return { result, comparisonResult, loading, error, runOptimize, runComparison, clearResult };
}
