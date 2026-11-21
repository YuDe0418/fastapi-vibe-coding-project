import { useEffect, useState, useCallback } from 'react';
import { api } from '@/services/api';
export function useResource<T>(path: string) {
 const [data, setData] = useState<T | null>(null); const [error, setError] = useState<Error | null>(null); const [loading, setLoading] = useState(true); const [version, setVersion] = useState(0);
 const reload = useCallback(() => setVersion(v => v + 1), []);
 useEffect(() => { let live = true; setLoading(true); setError(null); api<T>(path).then(value => { if (live) setData(value); }).catch(e => { if (live) setError(e); }).finally(() => { if (live) setLoading(false); }); return () => { live = false; }; }, [path, version]);
 return { data, error, loading, reload };
}
