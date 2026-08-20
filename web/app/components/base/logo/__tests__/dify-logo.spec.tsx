import { render, screen } from '@testing-library/react'
import { DifyLogo } from '../dify-logo'

const mockIsIoneBrandedUi = vi.hoisted(() => vi.fn(() => false))

vi.mock('@/features/ione-branding/feature-flag', () => ({
  isIoneBrandedUi: () => mockIsIoneBrandedUi(),
}))

describe('DifyLogo', () => {
  beforeEach(() => {
    mockIsIoneBrandedUi.mockReturnValue(false)
  })

  it('uses the provided alternative text as its accessible name', () => {
    const { container, rerender } = render(<DifyLogo alt="Dify" />)

    expect(screen.getByRole('img', { name: 'Dify' })).toHaveAttribute('src', '/logo/logo.svg')

    rerender(<DifyLogo alt="" />)

    const decorativeLogo = container.querySelector('img')
    expect(decorativeLogo).toHaveAttribute('alt', '')
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('uses the I-ONE wordmark and accessible name in branded mode', () => {
    mockIsIoneBrandedUi.mockReturnValue(true)

    render(<DifyLogo alt="Dify" size="large" />)

    expect(screen.getByRole('img', { name: 'I-ONE' })).toHaveAttribute('src', '/logo/ione-logo.svg')
  })
})
