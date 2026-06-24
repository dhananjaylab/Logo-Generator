'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ShieldCheck, Trash2, AlertTriangle, CheckCircle2, ArrowLeft } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { getApiUrl, authenticatedFetch } from '@/lib/auth';

export default function PrivacyPage() {
  const { token } = useAuth();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!token) {
      setError('You must be signed in to delete your data.');
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      const res = await authenticatedFetch(
        `${getApiUrl()}/me/data`,
        { method: 'DELETE' },
        token,
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail ?? 'Deletion failed');
      setResult(data.message ?? 'Your data has been deleted.');
      setConfirming(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Deletion failed');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <main style={{ maxWidth: 760, margin: '0 auto', padding: '3rem 1.5rem', lineHeight: 1.7 }}>
      <Link
        href="/"
        style={{ fontSize: '0.85rem', opacity: 0.6, display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
      >
        <ArrowLeft size={14} /> Back to LogoForge
      </Link>

      <h1 style={{
        fontSize: '1.8rem', fontWeight: 800, marginTop: '1rem',
        display: 'flex', alignItems: 'center', gap: '0.6rem',
      }}>
        <ShieldCheck size={26} /> Privacy &amp; Your Data
      </h1>

      <section style={{ marginTop: '2rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>What we collect</h2>
        <p>
          When you generate a logo, we store the brand name and description you provide,
          the final AI prompt, the generator used, and the resulting image. We also store
          a one-way cryptographic hash of your IP address — never the raw address itself —
          which cannot be reversed back to your actual IP. We do not sell or share your
          data with third parties beyond the AI providers (OpenAI, Google) strictly needed
          to generate the image you requested.
        </p>
      </section>

      <section style={{ marginTop: '1.5rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>How long we keep it</h2>
        <p>
          Generation history is retained for a limited period and then automatically and
          permanently deleted by a scheduled maintenance job. You don&apos;t need to do
          anything for this to happen — but if you&apos;d like your data removed sooner,
          you can request immediate deletion at any time using the control below.
        </p>
      </section>

      <section style={{ marginTop: '1.5rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Content safety</h2>
        <p>
          Every generation request is checked by an automated content-moderation system
          before it ever reaches an image generator. Requests that are flagged are blocked
          immediately and are not processed or charged against your quota beyond the check
          itself.
        </p>
      </section>

      <section style={{ marginTop: '1.5rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Your rights</h2>
        <p>
          Under data protection laws such as the GDPR and CCPA, you have the right to
          access, export, and delete the personal data we hold about you. The control
          below exercises your right to erasure — it permanently deletes your generation
          history and the associated images.
        </p>
      </section>

      <section style={{
        marginTop: '2.5rem', padding: '1.5rem',
        border: '1px solid rgba(255,71,87,0.3)', borderRadius: '0.9rem',
        background: 'rgba(255,71,87,0.06)',
      }}>
        <h2 style={{
          fontSize: '1.05rem', fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: '0.5rem',
        }}>
          <Trash2 size={18} /> Delete my data
        </h2>
        <p style={{ marginTop: '0.5rem' }}>
          This permanently deletes all of your generation history and associated images.
          This action cannot be undone.
        </p>

        {result && (
          <div style={{
            marginTop: '1rem', display: 'flex', gap: '0.5rem',
            alignItems: 'flex-start', color: '#2ed573',
          }}>
            <CheckCircle2 size={16} style={{ flexShrink: 0, marginTop: '2px' }} /> {result}
          </div>
        )}

        {error && (
          <div style={{
            marginTop: '1rem', display: 'flex', gap: '0.5rem',
            alignItems: 'flex-start', color: '#ff4757',
          }}>
            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px' }} /> {error}
          </div>
        )}

        {!result && !confirming && (
          <button
            onClick={() => setConfirming(true)}
            disabled={!token}
            style={{
              marginTop: '1rem', background: '#ff4757', color: '#fff',
              padding: '0.7rem 1.2rem', borderRadius: '0.6rem', fontWeight: 700,
              opacity: token ? 1 : 0.5, cursor: token ? 'pointer' : 'not-allowed',
            }}
          >
            Delete My Data
          </button>
        )}

        {!result && confirming && (
          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              onClick={handleDelete}
              disabled={deleting}
              style={{
                background: '#ff4757', color: '#fff', padding: '0.7rem 1.2rem',
                borderRadius: '0.6rem', fontWeight: 700,
                opacity: deleting ? 0.6 : 1,
              }}
            >
              {deleting ? 'Deleting…' : 'Yes, permanently delete everything'}
            </button>
            <button
              onClick={() => setConfirming(false)}
              disabled={deleting}
              style={{
                background: 'transparent', color: 'inherit',
                border: '1px solid rgba(255,255,255,0.2)',
                padding: '0.7rem 1.2rem', borderRadius: '0.6rem',
              }}
            >
              Cancel
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
