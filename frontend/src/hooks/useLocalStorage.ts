'use client'

import { useState, useEffect, useCallback } from 'react'

/**
 * SSR-safe localStorage hook.
 * Reads from localStorage on mount, writes back on every update.
 */
export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T) => void] {
  const [storedValue, setStoredValue] = useState<T>(initialValue)

  // Read from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const item = window.localStorage.getItem(key)
      if (item !== null) {
        setStoredValue(JSON.parse(item))
      }
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error)
    }
  }, [key])

  // Write to localStorage on update
  const setValue = useCallback(
    (value: T) => {
      setStoredValue(value)
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(key, JSON.stringify(value))
        } catch (error) {
          console.error(`Error writing localStorage key "${key}":`, error)
        }
      }
    },
    [key],
  )

  return [storedValue, setValue]
}
