'use client'

import { getCopyrightOwner } from './product'

const currentYear = new Date().getFullYear()

type IoneCopyrightProps = {
  className?: string
  year?: number
}

export function ProductCopyright({ className, year = currentYear }: IoneCopyrightProps) {
  const copyrightOwner = getCopyrightOwner()

  return (
    <div className={className}>
      © {year} {copyrightOwner.endsWith('.') ? copyrightOwner : `${copyrightOwner}.`} All rights
      reserved.
    </div>
  )
}
