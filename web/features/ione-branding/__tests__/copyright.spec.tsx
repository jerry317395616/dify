import { render, screen } from '@testing-library/react'
import { ProductCopyright } from '../copyright'

const mockIsIoneBrandedUi = vi.hoisted(() => vi.fn(() => false))

vi.mock('@/features/ione-branding/feature-flag', () => ({
  isIoneBrandedUi: () => mockIsIoneBrandedUi(),
}))

describe('ProductCopyright', () => {
  beforeEach(() => {
    mockIsIoneBrandedUi.mockReturnValue(false)
  })

  it('preserves the upstream copyright when branding is disabled', () => {
    render(<ProductCopyright year={2026} />)

    expect(screen.getByText('© 2026 LangGenius, Inc. All rights reserved.')).toBeInTheDocument()
  })

  it('uses I-ONE ownership in branded mode', () => {
    mockIsIoneBrandedUi.mockReturnValue(true)

    render(<ProductCopyright year={2026} />)

    expect(screen.getByText('© 2026 I-ONE. All rights reserved.')).toBeInTheDocument()
  })
})
