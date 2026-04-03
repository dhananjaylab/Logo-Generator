'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, ChevronDown } from 'lucide-react';
import styles from '../app/page.module.css';
import { resolveImageUrl } from '../lib/imageUrl';
import { getApiUrl, authenticatedFetch } from '../lib/auth';
import type { HistoryEntry } from '../lib/types';

interface HistoryItem extends HistoryEntry {}

export default function HistoryGallery({ 
  onSelect, token 
}: { 
  onSelect: (brand: string, logoSrc: string) => void,
  token: string | null
}) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(true);

  const fetchHistory = useCallback(async () => {
    if (!token) {
      console.log("[HistoryGallery] Waiting for authentication token");
      return;
    }

    try {
      setLoading(true);
      const API_URL = getApiUrl();
      const url = `${API_URL}/api/history?limit=12`;
      console.log("[HistoryGallery] Fetching from:", url);
      
      const res = await authenticatedFetch(url, {}, token);
      
      console.log("[HistoryGallery] Response status:", res.status);
      
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errorText}`);
      }
      
      const data = await res.json();
      setHistory(data);
      console.log("[HistoryGallery] Loaded", data.length, "items");
    } catch (err) {
      console.error("[HistoryGallery] Fetch failed:", err);
    } finally {
      setLoading(false);
    }
  }, [token]); // Token must be stable in parent to avoid re-fetch loops

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleSelect = (item: HistoryItem) => {
    onSelect(item.brand_name, resolveImageUrl(item.image_url));
  };

  return (
    <section className={styles.gallerySection}>
      <div className={styles.galleryHeader} style={{ cursor: 'pointer' }} onClick={() => setOpen(!open)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <h2>Recent Generations</h2>
          <ChevronDown size={14} className={`${styles.chevron} ${open ? styles.chevronOpen : ''}`} />
        </div>
        <button className={styles.refreshBtn} onClick={(e) => { e.stopPropagation(); fetchHistory(); }} title="Refresh History">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className={`${styles.advBody} ${open ? styles.advBodyOpen : ''}`} style={{ marginTop: 0 }}>
        <div className={styles.galleryGrid}>
          {loading && <div className={styles.galleryLoading}>Loading History...</div>}
          {!loading && history.length === 0 && (
            <div className={styles.galleryLoading}>No history found yet.</div>
          )}
          {!loading && history.map(item => {
            const src = resolveImageUrl(item.image_url);
            
            return (
               <div key={item.id} className={styles.galleryItem} onClick={() => handleSelect(item)}>
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
