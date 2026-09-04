import React from 'react';
import { Navbar } from '@/components/landing/navbar';
import { Hero } from '@/components/landing/hero';
import { ProductPreview } from '@/components/landing/product-preview';
import { Features } from '@/components/landing/features';
import { HowItWorks } from '@/components/landing/how-it-works';
import { Personas } from '@/components/landing/personas';
import { CTASection } from '@/components/landing/cta-section';
import { Footer } from '@/components/landing/footer';

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col selection:bg-primary/30 selection:text-white">
      <Navbar />
      <main className="flex-1">
        <Hero />
        <ProductPreview />
        <Features />
        <HowItWorks />
        <Personas />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
