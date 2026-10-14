import AnalysisPreview from '../components/home/AnalysisPreview'
import CTASection from '../components/home/CTASection'
import FeaturesSection from '../components/home/FeaturesSection'
import HeroSection from '../components/home/HeroSection'
import HowItWorks from '../components/home/HowItWorks'
import IngredientAnalyzer from '../components/home/IngredientAnalyzer'
import Footer from '../components/layout/Footer'
import Navbar from '../components/layout/Navbar'

function HomePage() {
  return (
    <>
      <Navbar />
      <main>
        <HeroSection />
        <IngredientAnalyzer />
        <HowItWorks />
        <FeaturesSection />
        <AnalysisPreview />
        <CTASection />
      </main>
      <Footer />
    </>
  )
}

export default HomePage
