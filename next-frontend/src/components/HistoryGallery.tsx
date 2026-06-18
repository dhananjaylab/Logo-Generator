'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, ChevronDown } from 'lucide-react';
import styles from '@/app/page.module.css';
import { resolveImageUrl } from '@/lib/imageUrl';
import { getApiUrl, authenticatedFetch } from '@/lib/auth';
import { useAuth } from '@/contexts/AuthContext'; // P1.1 — token from memory, not prop
import type { HistoryEntry } from '@/lib/types';

interface HistoryGalleryProps {
  onSelect: (brand: string, logoSrc: string) => void;
  // `token` prop removed — component reads from AuthContext instead (P1.1).
}

export default function HistoryGallery({ onSelect }: HistoryGalleryProps) {
  const { token } = useAuth();  // memory-only, never localStorage

  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [open,    setOpen]    = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    if (!token) {
      // Token not yet available — wait for AuthContext to provide it.
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const API_URL = getApiUrl();
      const res = await authenticatedFetch(`${API_URL}/history?limit=12`, {}, token);

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }

      const data: HistoryEntry[] = await res.json();
      setHistory(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load history';
      console.error('[HistoryGallery]', msg);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Re-fetch whenever the token becomes available (or changes after a refresh).
  useEffect(() => {
    if (token) fetchHistory();
  }, [token, fetchHistory]);

  const handleSelect = (item: HistoryEntry) => {
    onSelect(item.brand_name, resolveImageUrl(item.image_url) ?? '');
  };

  return (
    <section className={styles.gallerySection}>
      <div
        className={styles.galleryHeader}
        style={{ cursor: 'pointer' }}
        onClick={() => setOpen(o => !o)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <h2>Recent Generations</h2>
          <ChevronDown
            size={14}
            className={`${styles.chevron} ${open ? styles.chevronOpen : ''}`}
          />
        </div>
        <button
          className={styles.refreshBtn}
          onClick={e => { e.stopPropagation(); fetchHistory(); }}
          title="Refresh history"
          disabled={!token}
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className={`${styles.advBody} ${open ? styles.advBodyOpen : ''}`} style={{ marginTop: 0 }}>
        <div className={styles.galleryGrid}>
          {loading && (
            <div className={styles.galleryLoading}>Loading history…</div>
          )}

          {!loading && error && (
            <div className={styles.galleryLoading} style={{ color: '#ff4757' }}>
              {error}
            </div>
          )}

          {!loading && !error && history.length === 0 && (
            <div className={styles.galleryLoading}>No generations yet.</div>
          )}

          {!loading && !error && history.map(item => {
            const src = resolveImageUrl(item.image_url) ?? '';
            return (
              <div
                key={item.id}
                className={styles.galleryItem}
                onClick={() => handleSelect(item)}
                role="button"
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && handleSelect(item)}
                aria-label={`Load logo for ${item.brand_name}`}
              >
                <div className={styles.galleryImgWrap}>
                  <img src={src} alt={item.brand_name} />
                </div>
                <div className={styles.galleryInfo}>
                  <div className={styles.galleryName}>{item.brand_name}</div>
                  <div className={styles.galleryMeta}>
                    <span>{item.generator}</span>
                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
