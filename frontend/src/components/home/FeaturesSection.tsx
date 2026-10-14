import {
  AlertCircle,
  FlaskConical,
  Leaf,
  ScanLine,
} from 'lucide-react'
import SectionHeading from '../ui/SectionHeading'

const features = [
  {
    title: 'Ingredient Breakdown',
    description: 'Understand the purpose of individual ingredients in your skincare.',
    Icon: FlaskConical,
  },
  {
    title: 'Potential Concerns',
    description: 'Discover ingredients that may be worth a closer look.',
    Icon: AlertCircle,
  },
  {
    title: 'Beneficial Ingredients',
    description: 'Explore ingredients commonly associated with skincare benefits.',
    Icon: Leaf,
  },
  {
    title: 'Product Assessment',
    description: 'Get an easy-to-understand overview of a product’s formulation.',
    Icon: ScanLine,
  },
]

function FeaturesSection() {
  return (
    <section className="bg-[#f1f2ec] px-5 py-20 sm:px-8 sm:py-24 lg:px-10" id="features">
      <div className="mx-auto max-w-7xl">
        <SectionHeading
          description="Helpful context to make ingredient lists feel a little less like a foreign language."
          eyebrow="A thoughtful toolkit"
          title="Know more about what you put on your skin"
        />
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ title, description, Icon }) => (
            <article
              className="group rounded-3xl border border-[#e5e7df] bg-white p-6 transition duration-300 hover:-translate-y-1 hover:border-[#cbd7ca] hover:shadow-[0_18px_35px_-25px_rgba(41,75,58,0.4)] sm:p-7"
              key={title}
            >
              <span className="grid size-12 place-items-center rounded-2xl bg-[#edf2eb] text-[#55765d] transition group-hover:bg-[#294B3A] group-hover:text-white">
                <Icon aria-hidden="true" size={21} strokeWidth={1.7} />
              </span>
              <h3 className="mt-6 font-display text-xl text-[#294B3A]">{title}</h3>
              <p className="mt-2.5 text-sm leading-6 text-[#777a73]">{description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

export default FeaturesSection
