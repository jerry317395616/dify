import type { VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn } from '@langgenius/dify-ui/cn'
import { cva } from 'class-variance-authority'
import { isIoneBrandedUi } from '@/features/ione-branding/feature-flag'
import { IONE_PRODUCT_NAME } from '@/features/ione-branding/product'
import { basePath } from '@/utils/var'

const difyLogoVariants = cva(
  'block object-contain [html[data-theme=dark]_&]:brightness-0 [html[data-theme=dark]_&]:invert',
  {
    variants: {
      size: {
        small: 'h-4 w-9',
        medium: 'h-5.5 w-12',
        large: 'h-7 w-16',
      },
    },
    defaultVariants: {
      size: 'medium',
    },
  },
)

export type DifyLogoProps = Omit<
  ComponentProps<'img'>,
  'alt' | 'height' | 'size' | 'src' | 'width'
> &
  VariantProps<typeof difyLogoVariants> & {
    alt: string
  }

export function DifyLogo({ alt, className, size, ...props }: DifyLogoProps) {
  const classes = cn(difyLogoVariants({ size, className }))
  const ioneBrandedUi = isIoneBrandedUi()

  return (
    <img
      {...props}
      src={`${basePath}/logo/${ioneBrandedUi ? 'ione-logo.svg' : 'logo.svg'}`}
      width={48}
      height={22}
      className={classes}
      alt={ioneBrandedUi && alt ? IONE_PRODUCT_NAME : alt}
    />
  )
}
