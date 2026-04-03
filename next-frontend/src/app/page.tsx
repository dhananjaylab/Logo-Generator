'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Type, Cpu, Layers, Palette, Image as ImageIcon, Download, RefreshCw, ChevronDown, Target, Quote, CheckCircle2, Ban, Briefcase } from 'lucide-react';
import styles from './page.module.css';
import HistoryGallery from '../components/HistoryGallery';
import IdentityPreview from '../components/IdentityPreview';
import { resolveImageUrl } from '../lib/imageUrl';
import { getAuthToken, getApiUrl, getWsUrl, authenticatedFetch } from '../lib/auth';
import type { LogoGenerationResponse, JobStatusResponse } from '../lib/types';

export default function LogoForge() {
  const [generator, setGenerator] = useState('dalle-3');
  const [style, setStyle] = useState('minimalist');
  const [palette, setPalette] = useState('monochrome');
  const [brandName, setBrandName] = useState('');
  const [description, setDescription] = useState('');
  
  const [generating, setGenerating] = useState(false);
  const [progressLabel, setProgressLabel] = useState('Initializing...');
  const [progressValue, setProgressValue] = useState(0);
  const [logoSrc, setLogoSrc] = useState<string | null>(null);
  const [variationIndex, setVariationIndex] = useState(0);
  
  // Authentication token - fetched from Clerk or env
  const [token, setToken] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [advOpen, setAdvOpen] = useState(false);
  const [tagline, setTagline] = useState('');
  const [typography, setTypography] = useState('');
  const [elemInclude, setElemInclude] = useState('');
  const [elemAvoid, setElemAvoid] = useState('');
  const [mission, setMission] = useState('');

  const wsRef = useRef<WebSocket | null>(null);
  const progressSimRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize auth token on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const authToken = await getAuthToken();
        setToken(authToken);
      } catch (err) {
        console.error("[Auth] Failed to initialize token:", err);
      } finally {
        setAuthLoading(false);
      }
    };
    initAuth();
  }, []);

  // Cleanup WebSocket and intervals on component unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      if (progressSimRef.current) clearInterval(progressSimRef.current);
    };
  }, []);

  // Fallback Progress Simulator (since WebSockets only send "in_progress", we interpolate)
  const simulateProgress = (startVal: number, duration: number) => {
    if (progressSimRef.current) clearInterval(progressSimRef.current);
    const steps = 50;
    const increment = (95 - startVal) / steps;
    const delay = duration / steps;
    let current = startVal;
    progressSimRef.current = setInterval(() => {
      current += increment;
      if (current >= 95) current = 95;
      setProgressValue(current);
    }, delay);
  };

  // Helper: process job result (from WebSocket or polling)
  const handleJobResult = (result: LogoGenerationResponse | null, isError: boolean = false) => {
    if (progressSimRef.current) clearInterval(progressSimRef.current);
    if (isError) {
      alert(`Error: ${(result as any)?.error || result}`);
      setGenerating(false);
      return;
    }
    
    setProgressValue(100);
    setProgressLabel('Complete');
    
    if (result && result.result) {
      // Handle both string and array result shapes
      let imgUrl: string | undefined;
      if (typeof result.result === 'string') {
        imgUrl = result.result;
      } else if (Array.isArray(result.result) && result.result.length > 0) {
        imgUrl = result.result[0];
      }
      
      if (imgUrl) {
        setLogoSrc(resolveImageUrl(imgUrl));
      }
    }
    setTimeout(() => setGenerating(false), 500);
  };

  const handleGenerate = async (isRegen = false) => {
    if (!brandName && !description) return alert("Provide brand name or description");
    if (!token) return alert("Authentication required. Please reload the page.");
    
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
    simulateProgress(5, generator === 'dalle-3' ? 12000 : 8000);
    setLogoSrc(null);

    const API_URL = getApiUrl();
    const WS_URL = getWsUrl();

    try {
      // 1. HTTP Post to Enqueue Job
      const res = await authenticatedFetch(
        `${API_URL}/api/generate`,
        {
          method: 'POST',
          body: JSON.stringify({
            generator, style, palette, text: brandName, description, variation_index: newVariation,
            tagline, typography, elements_to_include: elemInclude, elements_to_avoid: elemAvoid, brand_mission: mission
          })
        },
        token
      );
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Generation Failed");

      const jobId = data.job_id;
      
      // 2. Connect WebSocket to listen for progress
      const ws = new WebSocket(`${WS_URL}/api/ws/progress/${jobId}?token=${encodeURIComponent(token)}`);
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
        console.error("WebSocket error, falling back to polling");
        // Fall back to REST polling via /api/jobs/{jobId}
        let pollAttempts = 0;
        const maxAttempts = 150; // ~5 minutes with 2s interval
        const poll = setInterval(async () => {
          pollAttempts++;
          try {
            const pollRes = await authenticatedFetch(
              `${API_URL}/api/jobs/${jobId}`,
              {},
              token
            );
            if (!pollRes.ok) throw new Error("Poll failed");
            
            const jobData: JobStatusResponse = await pollRes.json();
            if (jobData.status === 'completed' && jobData.result) {
              clearInterval(poll);
              handleJobResult(jobData.result);
            } else if (jobData.status === 'failed') {
              clearInterval(poll);
              handleJobResult(jobData, true);
            }
          } catch (pollErr) {
            console.error("Polling error:", pollErr);
            if (pollAttempts >= maxAttempts) {
              clearInterval(poll);
              handleJobResult(null, true);
            }
          }
        }, 2000);
      };

    } catch (err: any) {
      if (progressSimRef.current) clearInterval(progressSimRef.current);
      alert(err.message);
      setGenerating(false);
    }
  };

  const downloadLogo = async () => {
    if (!logoSrc) return;
    try {
      const resp = await fetch(logoSrc);
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `${brandName || 'logo'}_design.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      console.error(e);
      window.open(logoSrc, '_blank');
    }
  };

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
        {/* Left Form Panel */}
        <section className={styles.panel}>
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
            ></textarea>
          </div>

          <div>
            <button className={styles.advToggle} onClick={() => setAdvOpen(!advOpen)}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Target size={13} />
                Advanced Guidelines
              </span>
              <ChevronDown size={14} className={`${styles.chevron} ${advOpen ? styles.chevronOpen : ''}`} />
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
              <textarea className={styles.input} rows={2} placeholder="What is the core purpose of your brand?" value={mission} onChange={e => setMission(e.target.value)}></textarea>
            </div>
          </div>

          <div>
            <div className={styles.sectionTitle}><Cpu size={13} /> AI Generator</div>
            <div className={styles.grid2}>
              <button className={`${styles.chip} ${generator === 'dalle-3' ? styles.active : ''}`} onClick={() => setGenerator('dalle-3')}>🎨 DALL-E 3</button>
              <button className={`${styles.chip} ${generator === 'gemini' ? styles.active : ''}`} onClick={() => setGenerator('gemini')}>✨ Gemini</button>
            </div>
          </div>

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

          <div>
            <button className={styles.genBtn} onClick={() => handleGenerate(false)} disabled={generating}>
              <Sparkles size={20} /> {generating ? 'Generating...' : 'Generate Logo'}
            </button>
            
            {generating && (
              <div className={styles.progressWrap}>
                <div className={styles.progressTrack}>
                  <div className={styles.progressFill} style={{ width: `${progressValue}%` }}></div>
                </div>
                <div className={styles.progressLabel}>{progressLabel}</div>
              </div>
            )}
          </div>
        </section>

        {/* Right Preview Panel */}
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

            {/* Canvas Actions Overlay */}
            {logoSrc && !generating && (
               <div className={styles.canvasActions}>
                 <button className={`${styles.actBtn} ${styles.actPrimary}`} onClick={downloadLogo}>
                   <Download size={15}/> Download PNG
                 </button>
                 <button className={`${styles.actBtn} ${styles.actSecondary}`} onClick={() => handleGenerate(true)}>
                   <RefreshCw size={15}/> Regenerate
                 </button>
               </div>
            )}
          </div>
        </section>
      </main>

      <IdentityPreview brandName={brandName} logoSrc={logoSrc || ''} />

      <HistoryGallery token={token} onSelect={(b, url) => {
          setBrandName(b);
          setLogoSrc(url);
          window.scrollTo({ top: 0, behavior: 'smooth' });
      }} />

      <footer className={styles.footer}>
        <div><Sparkles size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }}/> LogoForge React Engine</div>
        <div>System: Online | API: Default</div>
      </footer>
    </div>
  );
}
