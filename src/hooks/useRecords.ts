import { useState, useEffect, useCallback } from 'react'
import { getRecords, getRecord, saveRecord, deleteRecord } from '@/api/wcapi'
import type { GetListPayload } from '@/api/wcapi'

interface UseRecordsOptions {
  model_name: string
  autoFetch?: boolean
  params?: Record<string, any>
}

export function useRecords({ model_name, autoFetch = true, params }: UseRecordsOptions) {
  const [data, setData] = useState<GetListPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async (extraParams?: Record<string, any>) => {
    setLoading(true)
    setError(null)
    try {
      const result = await getRecords(model_name, { ...params, ...extraParams })
      setData(result)
      return result
    } catch (err: any) {
      setError(err.message || 'Failed to fetch records')
      return null
    } finally {
      setLoading(false)
    }
  }, [model_name, JSON.stringify(params)])

  useEffect(() => {
    if (autoFetch) { fetch() }
  }, [fetch, autoFetch])

  const refetch = useCallback(() => fetch(), [fetch])

  return { data, loading, error, fetch, refetch, records: data?.results || [], total: data?.total || 0 }
}

export function useRecord(model_name: string, id: number | null) {
  const [record, setRecord] = useState<any>(null)
  const [related, setRelated] = useState<Record<string, any[]>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getRecord(model_name, id)
      .then(result => {
        setRecord(result.record)
        setRelated(result.related || {})
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [model_name, id])

  const save = useCallback(async (payload: any) => {
    const result = await saveRecord(model_name, payload)
    setRecord(result.record || result)
    return result
  }, [model_name])

  const remove = useCallback(async () => {
    if (!id) return
    await deleteRecord(model_name, id)
    setRecord(null)
  }, [model_name, id])

  return { record, related, loading, error, save, remove }
}
