import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonProps = {
  children: ReactNode
  className?: string
  href?: string
  variant?: 'primary' | 'secondary' | 'light'
} & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'children' | 'href'> &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'>

const variantClasses = {
  primary:
    'bg-[#294B3A] text-white shadow-sm hover:bg-[#203d2f] focus-visible:outline-[#294B3A]',
  secondary:
    'border border-[#d9dfd8] bg-white/70 text-[#294B3A] hover:border-[#8FAF9B] hover:bg-white focus-visible:outline-[#294B3A]',
  light:
    'bg-[#FAF9F6] text-[#294B3A] shadow-sm hover:bg-white focus-visible:outline-white',
}

function Button({
  children,
  className = '',
  href,
  variant = 'primary',
  ...props
}: ButtonProps) {
  const classes = `inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${variantClasses[variant]} ${className}`

  if (href) {
    return (
      <a className={classes} href={href} {...props}>
        {children}
      </a>
    )
  }

  return (
    <button className={classes} type="button" {...props}>
      {children}
    </button>
  )
}

export default Button
