'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, ChevronDown } from 'lucide-react';
import styles from '../app/page.module.css';

const API_URL = 'http://localhost:8000';

interface HistoryItem {
  id: number;
  brand_name: string;
  image_url: string;
  generator: string;
  created_at: string;
}

export default function HistoryGallery({ 
  onSelect, token 
}: { 
  onSelect: (brand: string, logoSrc: string) => void,
  token: string 
}) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(true);

  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/api/history?limit=12`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to fetch history");
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleSelect = (item: HistoryItem) => {
    let src = item.image_url;
    src = src.replace(/\\/g, '/');
    if (!src.startsWith('http')) {
      src = `${API_URL}/static/${src}`;
    }
    onSelect(item.brand_name, src);
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
            let src = item.image_url.replace(/\\/g, '/');
            if (!src.startsWith('http')) src = `${API_URL}/static/${src}`;
            
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
