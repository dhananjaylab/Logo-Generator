'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Sparkles, Type, Cpu, Layers, Palette,
  Image as ImageIcon, Download, RefreshCw, ChevronDown,
  Target, Quote, CheckCircle2, Ban, Briefcase, AlertCircle, X,
} from 'lucide-react';
import styles from './page.module.css';
import HistoryGallery from '@/components/HistoryGallery';
import IdentityPreview from '@/components/IdentityPreview';
import { resolveImageUrl } from '@/lib/imageUrl';
import { getApiUrl, getWsUrl, authenticatedFetch } from '@/lib/auth';
import { useAuth } from '@/contexts/AuthContext';        // P1.1 — replaces localStorage
import type { LogoGenerationResponse, JobStatusResponse, WsTicketResponse } from '@/lib/types';

// ── Inline error banner (P2.7 — replaces alert()) ───────────────────────────
function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
      background: 'rgba(255,71,87,0.12)', border: '1px solid rgba(255,71,87,0.35)',
      borderRadius: '0.75rem', padding: '0.9rem 1.1rem', marginTop: '0.75rem',
    }}>
      <AlertCircle size={16} style={{ color: '#ff4757', flexShrink: 0, marginTop: '2px' }} />
      <span style={{ flex: 1, fontSize: '0.87rem', color: '#ff4757', lineHeight: 1.5 }}>
        {message}
      </span>
      <button
        onClick={onDismiss}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ff4757', padding: 0 }}
        aria-label="Dismiss error"
      >
        <X size={14} />
      </button>
    </div>
  );
}

export default function LogoForge() {
  // ── Generator / style state ────────────────────────────────────────────
  const [generator, setGenerator] = useState('gpt-image-2-2026-04-21');
  const [style,     setStyle]     = useState('minimalist');
  const [palette,   setPalette]   = useState('monochrome');
  const [brandName, setBrandName] = useState('');
  const [description, setDescription] = useState('');

  const [generating,     setGenerating]     = useState(false);
  const [progressLabel,  setProgressLabel]  = useState('Initializing...');
  const [progressValue,  setProgressValue]  = useState(0);
  const [logoSrc,        setLogoSrc]        = useState<string | null>(null);
  const [variationIndex, setVariationIndex] = useState(0);

  // P1.1 — token comes from AuthContext (React memory), never localStorage.
  const { token, loading: authLoading, error: authError } = useAuth();

  // Error display state (replaces alert())
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Advanced options
  const [advOpen,    setAdvOpen]    = useState(false);
  const [tagline,    setTagline]    = useState('');
  const [typography, setTypography] = useState('');
  const [elemInclude, setElemInclude] = useState('');
  const [elemAvoid,   setElemAvoid]   = useState('');
  const [mission,     setMission]     = useState('');

  // Refs for cleanup — all timers and the WebSocket are tracked here so the
  // useEffect cleanup can cancel everything on unmount (P1.7 — pollRef fix).
  const wsRef           = useRef<WebSocket | null>(null);
  const progressSimRef  = useRef<NodeJS.Timeout | null>(null);
  const pollRef         = useRef<NodeJS.Timeout | null>(null); // P1.7 — was anonymous, leaked on unmount

  // Cancel all async work on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      if (progressSimRef.current) clearInterval(progressSimRef.current);
      if (pollRef.current)        clearInterval(pollRef.current);   // P1.7
    };
  }, []);

  // ── Progress simulator ─────────────────────────────────────────────────
  const simulateProgress = useCallback((startVal: number, duration: number) => {
    if (progressSimRef.current) clearInterval(progressSimRef.current);
    const steps     = 50;
    const increment = (95 - startVal) / steps;
    const delay     = duration / steps;
    let current = startVal;
    progressSimRef.current = setInterval(() => {
      current = Math.min(current + increment, 95);
      setProgressValue(current);
    }, delay);
  }, []);

  // ── Job result handler ────────────────────────────────────────────────
  const handleJobResult = useCallback(
    (result: LogoGenerationResponse | JobStatusResponse | null, isError = false) => {
      if (progressSimRef.current) clearInterval(progressSimRef.current);
      if (isError) {
        const msg = (result as { error?: string } | null)?.error ?? 'Generation failed';
        // P2.7 — show inline error instead of alert()
        setErrorMsg(msg);
        setGenerating(false);
        return;
      }

      setProgressValue(100);
      setProgressLabel('Complete');

      if (result && 'result' in result && result.result) {
        const imgUrl = Array.isArray(result.result)
          ? result.result[0]
          : (result.result as string);
        if (imgUrl) setLogoSrc(resolveImageUrl(imgUrl));
      }
      setTimeout(() => setGenerating(false), 500);
    },
    [],
  );

  // ── Main generate handler ─────────────────────────────────────────────
  const handleGenerate = useCallback(
    async (isRegen = false) => {
      if (!brandName && !description) {
        setErrorMsg('Please provide a brand name or description.');
        return;
      }
      if (!token) {
        setErrorMsg('Authentication is not ready yet — please wait a moment and try again.');
        return;
      }

      setErrorMsg(null);

      let newVariation = variationIndex;
      if (isRegen) {
        newVariation += 1;
        setVariationIndex(newVariation);
      } else {
        newVariation = 0;
        setVariationIndex(0);
      }

      setGenerating(true);
      setProgressValue(5);
      setProgressLabel(`Connecting to ${generator}...`);
      simulateProgress(5, generator === 'gpt-image-2-2026-04-21' ? 12000 : 8000);
      setLogoSrc(null);

      const API_URL = getApiUrl();
      const WS_URL  = getWsUrl();

      try {
        // ── 1. Enqueue the generation job ──────────────────────────────
        const res = await authenticatedFetch(
          `${API_URL}/generate`,
          {
            method: 'POST',
            body: JSON.stringify({
              generator, style, palette,
              text: brandName, description,
              variation_index: newVariation,
              tagline, typography,
              elements_to_include: elemInclude,
              elements_to_avoid:   elemAvoid,
              brand_mission:       mission,
            }),
          },
          token,
        );

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail ?? 'Generation failed');

        const jobId = data.job_id;

        // ── 2. Exchange JWT for a short-lived WS ticket (P1.2 / VULN-02) ──
        // The ticket — NOT the JWT — goes in the WebSocket URL query string,
        // so the long-lived bearer token never appears in server access logs.
        const ticketRes = await authenticatedFetch(
          `${API_URL}/ws/ticket`,
          { method: 'POST' },
          token,
        );
        if (!ticketRes.ok) throw new Error('Failed to obtain WebSocket ticket');
        const { ticket }: WsTicketResponse = await ticketRes.json();

        // ── 3. Open WebSocket with the ticket ──────────────────────────
        const ws = new WebSocket(
          `${WS_URL}/ws/progress/${jobId}?ticket=${encodeURIComponent(ticket)}`,
        );
        wsRef.current = ws;

        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          if (msg.status === 'in_progress') {
            setProgressLabel('Generating image...');
          } else if (msg.status === 'completed') {
            handleJobResult(msg.result);
            ws.close();
          } else if (msg.status === 'failed') {
            handleJobResult(msg, true);
            ws.close();
          }
        };

        ws.onerror = async () => {
          console.warn('[WS] WebSocket error — falling back to HTTP polling');

          let pollAttempts = 0;
          const maxAttempts = 150; // ~5 min at 2 s intervals

          // P1.7: store interval in pollRef so it is cleared on unmount.
          pollRef.current = setInterval(async () => {
            pollAttempts++;
            try {
              const pollRes = await authenticatedFetch(
                `${API_URL}/jobs/${jobId}`,
                {},
                token,
              );
              if (!pollRes.ok) throw new Error('Poll request failed');

              const jobData: JobStatusResponse = await pollRes.json();
              if (jobData.status === 'completed' && jobData.result) {
                clearInterval(pollRef.current!);
                pollRef.current = null;
                handleJobResult(jobData.result);
              } else if (jobData.status === 'failed') {
                clearInterval(pollRef.current!);
                pollRef.current = null;
                handleJobResult(jobData, true);
              }
            } catch (pollErr) {
              console.error('[Poll]', pollErr);
              if (pollAttempts >= maxAttempts) {
                clearInterval(pollRef.current!);
                pollRef.current = null;
                handleJobResult(null, true);
              }
            }
          }, 2000);
        };

      } catch (err: unknown) {
        if (progressSimRef.current) clearInterval(progressSimRef.current);
        const msg = err instanceof Error ? err.message : 'An unexpected error occurred';
        setErrorMsg(msg);
        setGenerating(false);
      }
    },
    [
      brandName, description, generator, style, palette,
      tagline, typography, elemInclude, elemAvoid, mission,
      token, variationIndex, simulateProgress, handleJobResult,
    ],
  );

  // ── Download helper ───────────────────────────────────────────────────
  const downloadLogo = useCallback(async () => {
    if (!logoSrc) return;
    try {
      const resp = await fetch(logoSrc);
      const blob = await resp.blob();
      const url  = window.URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.style.display = 'none';
      a.href     = url;
      a.download = `${brandName || 'logo'}_design.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      window.open(logoSrc, '_blank');
    }
  }, [logoSrc, brandName]);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <div className={styles.iconWrap}><Sparkles size={20} /></div>
          <h1>LogoForge AI</h1>
        </div>
        <span className={styles.pill}>v3.0 // React</span>
      </header>

      <main className={styles.main}>
        {/* ── Left Form Panel ── */}
        <section className={styles.panel}>

          {/* Auth error state */}
          {authError && (
            <ErrorBanner
              message={`Authentication error: ${authError}`}
              onDismiss={() => {}}
            />
          )}

          {/* Generation error state */}
          {errorMsg && (
            <ErrorBanner
              message={errorMsg}
              onDismiss={() => setErrorMsg(null)}
            />
          )}

          <div>
            <div className={styles.sectionTitle}><Type size={13} /> Brand Identity</div>
            <input
              className={styles.input}
              type="text"
              placeholder="Enter Brand Name"
              value={brandName}
              onChange={e => setBrandName(e.target.value)}
            />
            <textarea
              className={styles.input}
              placeholder="Describe your brand, industry, or vision..."
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
          </div>

          {/* Advanced Guidelines */}
          <div>
            <button className={styles.advToggle} onClick={() => setAdvOpen(!advOpen)}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Target size={13} />
                Advanced Guidelines
              </span>
              <ChevronDown
                size={14}
                className={`${styles.chevron} ${advOpen ? styles.chevronOpen : ''}`}
              />
            </button>
            <div className={`${styles.advBody} ${advOpen ? styles.advBodyOpen : ''}`}>
              <div className={styles.sectionTitle}><Quote size={10} /> Tagline</div>
              <input className={styles.input} type="text" placeholder="e.g. Innovation at Speed" value={tagline} onChange={e => setTagline(e.target.value)} />

              <div className={styles.sectionTitle} style={{ marginTop: '0.4rem' }}><Type size={10} /> Typography Preference</div>
              <input className={styles.input} type="text" placeholder="e.g. Modern Sans-Serif, Bold Serif" value={typography} onChange={e => setTypography(e.target.value)} />

              <div className={styles.grid2} style={{ marginTop: '0.4rem' }}>
                <div>
                  <div className={styles.sectionTitle}><CheckCircle2 size={10} /> Include</div>
                  <input className={styles.input} type="text" placeholder="e.g. Gear, Leaf" value={elemInclude} onChange={e => setElemInclude(e.target.value)} />
                </div>
                <div>
                  <div className={styles.sectionTitle}><Ban size={10} /> Avoid</div>
                  <input className={styles.input} type="text" placeholder="e.g. Animals, Circles" value={elemAvoid} onChange={e => setElemAvoid(e.target.value)} />
                </div>
              </div>

              <div className={styles.sectionTitle} style={{ marginTop: '0.4rem' }}><Briefcase size={10} /> Brand Mission</div>
              <textarea className={styles.input} rows={2} placeholder="What is the core purpose of your brand?" value={mission} onChange={e => setMission(e.target.value)} />
            </div>
          </div>

          {/* Generator */}
          <div>
            <div className={styles.sectionTitle}><Cpu size={13} /> AI Generator</div>
            <div className={styles.grid2}>
              <button className={`${styles.chip} ${generator === 'gpt-image-2-2026-04-21' ? styles.active : ''}`} onClick={() => setGenerator('gpt-image-2-2026-04-21')}>🎨 GPT Image 2</button>
              <button className={`${styles.chip} ${generator === 'gemini' ? styles.active : ''}`} onClick={() => setGenerator('gemini')}>✨ Gemini</button>
            </div>
          </div>

          {/* Style */}
          <div>
            <div className={styles.sectionTitle}><Layers size={13} /> Visual Style</div>
            <div className={styles.grid2}>
              {['minimalist', 'tech', 'vintage', 'abstract', 'mascot', 'luxury'].map(s => (
                <button key={s} className={`${styles.chip} ${style === s ? styles.active : ''}`} onClick={() => setStyle(s)}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Palette */}
          <div>
            <div className={styles.sectionTitle}><Palette size={13} /> Color Palette</div>
            <div className={styles.grid3}>
              {['monochrome', 'ocean', 'sunset', 'forest', 'royal', 'neon'].map(p => (
                <button key={p} className={`${styles.chip} ${palette === p ? styles.active : ''}`} onClick={() => setPalette(p)}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Generate button */}
          <div>
            <button
              className={styles.genBtn}
              onClick={() => handleGenerate(false)}
              disabled={generating || authLoading || !token}
              aria-busy={generating}
            >
              <Sparkles size={20} />
              {authLoading ? 'Authenticating...' : generating ? 'Generating...' : 'Generate Logo'}
            </button>

            {generating && (
              <div className={styles.progressWrap}>
                <div className={styles.progressTrack}>
                  <div className={styles.progressFill} style={{ width: `${progressValue}%` }} />
                </div>
                <div className={styles.progressLabel}>{progressLabel}</div>
              </div>
            )}
          </div>
        </section>

        {/* ── Right Preview Panel ── */}
        <section className={styles.previewPanel}>
          <div className={styles.canvas}>
            {logoSrc ? (
              <img src={logoSrc} alt="Generated Logo" className={styles.canvasImage} />
            ) : (
              <div className={styles.placeholder}>
                <ImageIcon size={64} style={{ opacity: 0.15 }} strokeWidth={1} />
                <p>Awaiting Parameters</p>
              </div>
            )}

            {logoSrc && !generating && (
              <div className={styles.canvasActions}>
                <button className={`${styles.actBtn} ${styles.actPrimary}`} onClick={downloadLogo}>
                  <Download size={15} /> Download PNG
                </button>
                <button className={`${styles.actBtn} ${styles.actSecondary}`} onClick={() => handleGenerate(true)}>
                  <RefreshCw size={15} /> Regenerate
                </button>
              </div>
            )}
          </div>
        </section>
      </main>

      <IdentityPreview brandName={brandName} logoSrc={logoSrc || ''} />

      {/* P1.1 — HistoryGallery now gets its own token via useAuth() */}
      <HistoryGallery
        onSelect={(b, url) => {
          setBrandName(b);
          setLogoSrc(url);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      />

      <footer className={styles.footer}>
        <div><Sparkles size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> LogoForge React Engine</div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <a href="/privacy" style={{ opacity: 0.7 }}>Privacy &amp; Data</a>
          <span>System: Online | API: Default</span>
        </div>
      </footer>
    </div>
  );
}
