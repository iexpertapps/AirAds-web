import { HeroSection } from '@/components/landing/HeroSection';
import { HowItWorksSection } from '@/components/landing/HowItWorksSection';
import { TierPreviewSection } from '@/components/landing/TierPreviewSection';
import { SocialProofSection } from '@/components/landing/SocialProofSection';
import { CTASection } from '@/components/landing/CTASection';

export default function LandingPage() {
  return (
    <>
      <HeroSection />
      <HowItWorksSection />
      <TierPreviewSection />
      <SocialProofSection />
      <CTASection />
    </>
  );
}
