type SectionHeadingProps = {
  eyebrow?: string
  title: string
  description?: string
  centered?: boolean
}

function SectionHeading({
  eyebrow,
  title,
  description,
  centered = true,
}: SectionHeadingProps) {
  return (
    <div className={`max-w-2xl ${centered ? 'mx-auto text-center' : ''}`}>
      {eyebrow && (
        <p className="mb-4 text-xs font-bold uppercase tracking-[0.2em] text-[#65846f]">
          {eyebrow}
        </p>
      )}
      <h2 className="font-display text-3xl leading-tight text-[#252525] sm:text-4xl lg:text-[2.75rem]">
        {title}
      </h2>
      {description && (
        <p className="mt-4 text-base leading-7 text-[#6b6d68] sm:text-lg">
          {description}
        </p>
      )}
    </div>
  )
}

export default SectionHeading
