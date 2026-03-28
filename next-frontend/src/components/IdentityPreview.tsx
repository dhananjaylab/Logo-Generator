'use client';

import React from 'react';
import { Mail, Globe, MapPin, CreditCard, Smartphone, Monitor } from 'lucide-react';
import styles from '../app/page.module.css';

interface IdentityPreviewProps {
  readonly brandName: string;
  readonly logoSrc: string;
}

export default function IdentityPreview({ brandName, logoSrc }: IdentityPreviewProps) {
  if (!logoSrc) return null;

  return (
    <section className={styles.identitySection}>
      <div className={styles.identityInner}>
        <div className={styles.identityHeader}>
          <h2>Visual Identity Preview</h2>
          <p>Conceptual previews of how your logo would appear on physical and digital assets.</p>
        </div>
        
        <div className={styles.identityGrid}>
          {/* Card Mockup */}
          <div>
            <div className={styles.bizCard}>
              <div className={styles.bizLogoWrap}>
                <img src={logoSrc} alt="Logo" />
              </div>
              <div className={styles.bizInfo}>
                <div className={styles.bizName}>{brandName || "Brand Name"}</div>
                <div className={styles.bizTagline}>Global Solutions</div>
                <div className={styles.bizContacts}>
                  <div className={styles.bizContact}><Mail size={11} /> contact@example.com</div>
                  <div className={styles.bizContact}><Globe size={11} /> www.example.com</div>
                  <div className={styles.bizContact}><MapPin size={11} /> 123 Innovation Drive</div>
                </div>
              </div>
            </div>
            <div className={styles.identityLabel}><CreditCard size={12} /> Physical Asset // Business Card Mockup</div>
          </div>
          
          {/* Digital Mockups */}
          <div className={styles.digCol}>
            {/* App Icon + Favicon */}
            <div className={styles.appIconWrap}>
              <div>
                <div className={styles.appIcon}>
                  <img src={logoSrc} alt="App icon" />
                </div>
                <div className={styles.identityLabel} style={{ justifyContent: 'center', marginTop: '0.6rem' }}>
                  <Smartphone size={12} /> iOS Icon
                </div>
              </div>
              <div className={styles.webFav}>
                <div className={styles.favRow}>
                  <div className={styles.favIcon}>
                    <img src={logoSrc} alt="Favicon" />
                  </div>
                  <div className={styles.favBar}></div>
                </div>
                <div className={styles.favLines}>
                  <div className={`${styles.favLine}`} style={{ width: '100%' }}></div>
                  <div className={`${styles.favLine}`} style={{ width: '66%' }}></div>
                </div>
                <div className={styles.identityLabel} style={{ marginTop: '0.6rem' }}><Globe size={11} /> Web Favicon</div>
              </div>
            </div>
            
            {/* Dark UI Mockup */}
            <div className={styles.darkMock}>
              <div className={styles.darkLogoBox}>
                <img src={logoSrc} alt="Dark logo" />
              </div>
              <div className={styles.darkLines}>
                <div className={styles.darkLine} style={{ width: '100%' }}></div>
                <div className={styles.darkLine} style={{ width: '75%' }}></div>
                <div className={styles.darkLine} style={{ width: '50%' }}></div>
              </div>
            </div>
            <div className={styles.identityLabel} style={{ justifyContent: 'center' }}>
              <Monitor size={11} /> Dark UI Adaptability
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
